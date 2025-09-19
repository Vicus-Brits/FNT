import random
import base64
import requests
from urllib.parse import urlencode
from django.db import models
from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import Session, Song
from .serializers import (
    SessionSerializer,
    SongSerializer,
    ArtistSearchResponseSerializer,
    ArtistSongsResponseSerializer,
    SongSearchResponseSerializer,
    AddPlaylistVibeResponseSerializer,
    GetSongsResponseSerializer,
    OrderPlaylistItemSerializer,
    OrderPlaylistResponseSerializer,
    OrderVibeItemSerializer,
    OrderVibeResponseSerializer,
    RemoveListResponseSerializer,
    ClearVibeResponseSerializer,
    RecommendResponseSerializer,
)
from .helperfunctions import (
    find_artist,
    # get_top_tracks_for_artist,
    find_song,
    get_top_tracks_for_artist_by_name,
)
from .recommendation_helpers import recommend_tracks



# helper function to check if session is valid
def validate_session(session_id):
    if not session_id:
        return False, Response({"error": "session_id required"}, status=400)
    
    try:
        session = Session.objects.get(session_id=session_id)
        if not session.is_active:
            return False, Response({"error": "Session not active"}, status=400)
        return True, None
    except Session.DoesNotExist:
        return False, Response({"error": "Session not found"}, status=404)


class SessionViewSet(viewsets.ViewSet):
    serializer_class = SessionSerializer
    
    @extend_schema(
        description='Creates session with random 6-digit ID',
        request=None,
        responses={201: SessionSerializer}
    )
    @action(detail=False, methods=['post'])
    def start_session(self, request):
        # Generate random session ID - TODO: maybe use UUIDs instead?
        session_id = str(random.randint(100000, 999999))
        while Session.objects.filter(session_id=session_id).exists():
            session_id = str(random.randint(100000, 999999))
        
        session = Session.objects.create(session_id=session_id)
        serializer = SessionSerializer(session)
        
        return Response({'session': serializer.data}, status=201)
    
    @extend_schema(
        description='Delete session and songs',
        parameters=[
            OpenApiParameter(
                name="id",
                required=True,
                type=str,
                location=OpenApiParameter.PATH,
                description="Session ID"
            )
        ],
        responses={200: {'type': 'object', 'properties': {'session_id': {'type': 'string'}}}}
    )
    @action(detail=True, methods=['delete'])
    def stop_session(self, request, pk=None):
        try:
            session = Session.objects.get(session_id=pk)
            session.is_active = False
            session.save()
            return Response({
                'session_id': session.session_id,
                'message': 'Session deactivated successfully'
            })
        except Session.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)

    @extend_schema(
        description='Check session status',
        parameters=[
            OpenApiParameter(
                name="id",
                required=True,
                type=str,
                location=OpenApiParameter.PATH,
                description="Session ID"
            )
        ],
        responses={200: SessionSerializer}
    )
    @action(detail=True, methods=['get'])
    def check_session(self, request, pk=None):
        try:
            session = Session.objects.get(session_id=pk)
            serializer = SessionSerializer(session)
            return Response({'session': serializer.data})
        except Session.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)


class SongViewSet(viewsets.ViewSet):
    serializer_class = SongSerializer
    # TODO: add CRUD operations here


class ArtistSearchLFMView(APIView):
    serializer_class = ArtistSearchResponseSerializer
    
    def get(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        artist_name = request.query_params.get("artist_name")
        
        if not artist_name:
            return Response({"error": "artist_name required"}, status=400)
        
       
        # Call helper function to search
        response_data = find_artist(artist_name)
        
        # top 5 artists
        artists = response_data.get("results", {}).get("artists", [])
        limited_artists = artists[:5]
        
        return Response({
            "results": {
                "artists": limited_artists
            }
        })
        


class ArtistSearchSongLFMView(APIView):
    serializer_class = ArtistSongsResponseSerializer
    
    @extend_schema(
        description='Get top tracks for specific artist from Last.fm using artist name or MBID',
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Session ID"
            ),
            OpenApiParameter(
                name="artist_name",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Artist name"
            ),
            OpenApiParameter(
                name="artist_mbid",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Optional: Artist MBID (if provided, takes priority over artist_name)"
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        artist_name = request.query_params.get("artist_name")
        artist_mbid = request.query_params.get("artist_mbid")
        
        # Validate session
        is_valid, error_response = validate_session(session_id)
        if not is_valid:
            return error_response
        
        if not artist_name:
            return Response({"error": "artist_name required"}, status=400)
        
        # Get top tracks for artist
        data = get_top_tracks_for_artist_by_name(artist_name, artist_mbid)
        return Response(data)


class SongSearchLFMView(APIView):
    serializer_class = SongSearchResponseSerializer
    
    @extend_schema(
        description='Search Last.fm for songs by track name and optional artist name',
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Session ID"
            ),
            OpenApiParameter(
                name="song_name",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Song/track name"
            ),
            OpenApiParameter(
                name="artist_name",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Optional: Artist Name"
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        song_name = request.query_params.get("song_name")
        artist_name = request.query_params.get("artist_name")  # Optional parameter
        
        # Validate session
        is_valid, error_response = validate_session(session_id)
        if not is_valid:
            return error_response
        
        if not song_name:
            return Response({"error": "song_name required"}, status=400)
        
        # Search for songs
        data = find_song(song_name, artist_name)
        return Response(data)


class AddPlaylistVibeView(APIView):
    serializer_class = AddPlaylistVibeResponseSerializer
    
    @extend_schema(
        description='Add song to playlist and vibe with sequence management',
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Session ID"
            ),
            OpenApiParameter(
                name="artist_name",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Artist name"
            ),
            OpenApiParameter(
                name="artist_mbid",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Optional: Artist MBID"
            ),
            OpenApiParameter(
                name="song_name",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Song/track name"
            ),
            OpenApiParameter(
                name="song_mbid",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Optional: Song MBID"
            ),
            OpenApiParameter(
                name="popularity",
                required=False,
                type=int,
                location=OpenApiParameter.QUERY,
                description="Optional: Song popularity score"
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        artist_name = request.query_params.get("artist_name")
        artist_mbid = request.query_params.get("artist_mbid", "")
        song_name = request.query_params.get("song_name")
        song_mbid = request.query_params.get("song_mbid", "")
        popularity = request.query_params.get("popularity", 0)
        
        # Validate session
        is_valid, error_response = validate_session(session_id)
        if not is_valid:
            return error_response
        
        # Check required params
        if not artist_name:
            return Response({"error": "artist_name required"}, status=400)
        if not song_name:
            return Response({"error": "song_name required"}, status=400)
        
        try:
            session = Session.objects.get(session_id=session_id)
            
            # Convert popularity to int
            try:
                popularity = int(popularity)
            except:
                popularity = 0
            
            # Update existing vibe_sequence values - increment by 1
            Song.objects.filter(session=session, vibe_sequence__gt=0).update(
                vibe_sequence=models.F('vibe_sequence') + 1
            )
            
            # Get max playlist_sequence and add 1
            max_playlist_seq = Song.objects.filter(session=session).aggregate(
                max_seq=models.Max('playlist_sequence')
            )['max_seq']
            new_playlist_sequence = (max_playlist_seq or 0) + 1
            
            # Create new song
            new_song = Song.objects.create(
                session=session,
                artist_id=artist_mbid,
                artist_name=artist_name,
                song_id=song_mbid,
                song_title=song_name,
                song_popularity=popularity,
                vibe_sequence=1,  # Set to 1 (highest priority)
                playlist_sequence=new_playlist_sequence,
                playlist_hist_sequence=0,
                is_playing=False,
                is_played=False
            )
            
            return Response({
                "success": True,
                "message": "Song added to playlist and vibe successfully",
                "song_id": new_song.id,
                "vibe_sequence": new_song.vibe_sequence,
                "playlist_sequence": new_song.playlist_sequence
            })
            
        except Session.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)
        except Exception as e:
            return Response({"error": f"Failed to add song: {str(e)}"}, status=500)


class GetSongsView(APIView):
    serializer_class = GetSongsResponseSerializer
    
    @extend_schema(
        description='Get songs from playlist or vibe list ordered by sequence',
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Session ID"
            ),
            OpenApiParameter(
                name="list_type",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Type of list to retrieve: 'playlist' or 'vibe'",
                enum=['playlist', 'vibe']
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        list_type = request.query_params.get("list_type")
        
        # Validate session
        is_valid, error_response = validate_session(session_id)
        if not is_valid:
            return error_response
        
        if not list_type:
            return Response({"error": "list_type required"}, status=400)
            
        if list_type not in ['playlist', 'vibe']:
            return Response({"error": "list_type must be 'playlist' or 'vibe'"}, status=400)
        
        try:
            session = Session.objects.get(session_id=session_id)
            
            if list_type == 'playlist':
                # Get playlist songs ordered by sequence
                songs = Song.objects.filter(
                    session=session,
                    playlist_sequence__isnull=False,
                    playlist_sequence__gt=0
                ).order_by('playlist_sequence')
            else:  # vibe
                # Get vibe songs ordered by sequence
                songs = Song.objects.filter(
                    session=session,
                    vibe_sequence__isnull=False,
                    vibe_sequence__gt=0
                ).order_by('vibe_sequence')
            
            return Response({
                "success": True,
                "list_type": list_type,
                "songs": SongSerializer(songs, many=True).data
            })
            
        except Session.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)
        except Exception as e:
            return Response({"error": f"Failed to retrieve songs: {str(e)}"}, status=500)


class OrderPlaylistView(APIView):
    serializer_class = OrderPlaylistResponseSerializer
    
    @extend_schema(
        description='Update playlist sequence order for multiple songs',
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Session ID"
            )
        ],
        request={
            'application/json': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer', 'description': 'Song ID'},
                        'playlist_sequence': {'type': 'integer', 'description': 'New playlist sequence number'}
                    },
                    'required': ['id', 'playlist_sequence']
                },
                'example': [
                    {"id": 2, "playlist_sequence": 1},
                    {"id": 1, "playlist_sequence": 2}
                ]
            }
        }
    )
    def post(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        
        # Validate session
        is_valid, error_response = validate_session(session_id)
        if not is_valid:
            return error_response
        
        # Validate request data
        if not isinstance(request.data, list):
            return Response({"error": "Request body must be an array of objects"}, status=400)
        
        # Serialize and validate each item
        serializer = OrderPlaylistItemSerializer(data=request.data, many=True)
        if not serializer.is_valid():
            return Response({"error": "Invalid data format", "details": serializer.errors}, status=400)
        
        try:
            session = Session.objects.get(session_id=session_id)
            updated_count = 0
            
            # Update each song's playlist_sequence
            for item in serializer.validated_data:
                song_id = item['id']
                new_sequence = item['playlist_sequence']
                
                # Update the song if it exists and belongs to the session
                updated = Song.objects.filter(
                    id=song_id,
                    session=session
                ).update(playlist_sequence=new_sequence)
                
                if updated:
                    updated_count += 1
            
            return Response({
                "success": True,
                "message": f"Successfully updated playlist sequence for {updated_count} songs",
                "updated_songs": updated_count
            })
            
        except Session.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)
        except Exception as e:
            return Response({"error": f"Failed to update playlist order: {str(e)}"}, status=500)


class OrderVibeView(APIView):
    serializer_class = OrderVibeResponseSerializer
    
    @extend_schema(
        description='Update vibe sequence order for multiple songs',
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Session ID"
            )
        ],
        request={
            'application/json': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer', 'description': 'Song ID'},
                        'vibe_sequence': {'type': 'integer', 'description': 'New vibe sequence number'}
                    },
                    'required': ['id', 'vibe_sequence']
                },
                'example': [
                    {"id": 2, "vibe_sequence": 2},
                    {"id": 1, "vibe_sequence": 1}
                ]
            }
        }
    )
    def post(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        
        # Validate session
        is_valid, error_response = validate_session(session_id)
        if not is_valid:
            return error_response
        
        # Validate request data
        if not isinstance(request.data, list):
            return Response({"error": "Request body must be an array of objects"}, status=400)
        
        # Serialize and validate each item
        serializer = OrderVibeItemSerializer(data=request.data, many=True)
        if not serializer.is_valid():
            return Response({"error": "Invalid data format", "details": serializer.errors}, status=400)
        
        try:
            session = Session.objects.get(session_id=session_id)
            updated_count = 0
            
            # Update each song's vibe_sequence
            for item in serializer.validated_data:
                song_id = item['id']
                new_sequence = item['vibe_sequence']
                
                # Update the song if it exists and belongs to the session
                updated = Song.objects.filter(
                    id=song_id,
                    session=session
                ).update(vibe_sequence=new_sequence)
                
                if updated:
                    updated_count += 1
            
            return Response({
                "success": True,
                "message": f"Successfully updated vibe sequence for {updated_count} songs",
                "updated_songs": updated_count
            })
            
        except Session.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)
        except Exception as e:
            return Response({"error": f"Failed to update vibe order: {str(e)}"}, status=500)


class RemoveListView(APIView):
    serializer_class = RemoveListResponseSerializer
    
    @extend_schema(
        description='Remove a song from playlist or vibe list and reorder sequences',
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Session ID"
            ),
            OpenApiParameter(
                name="list_type",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Type of list to remove from: 'playlist' or 'vibe'",
                enum=['playlist', 'vibe']
            ),
            OpenApiParameter(
                name="id",
                required=True,
                type=int,
                location=OpenApiParameter.QUERY,
                description="Song ID to remove from the list"
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        list_type = request.query_params.get("list_type")
        song_id = request.query_params.get("id")
        
        # Validate session
        is_valid, error_response = validate_session(session_id)
        if not is_valid:
            return error_response
        
        # Validate parameters
        if not list_type:
            return Response({"error": "list_type required"}, status=400)
        if list_type not in ['playlist', 'vibe']:
            return Response({"error": "list_type must be 'playlist' or 'vibe'"}, status=400)
        if not song_id:
            return Response({"error": "id required"}, status=400)
        
        try:
            song_id = int(song_id)
        except ValueError:
            return Response({"error": "id must be a valid integer"}, status=400)
        
        try:
            session = Session.objects.get(session_id=session_id)
            
            # Check if song exists and belongs to the session
            try:
                song_to_remove = Song.objects.get(id=song_id, session=session)
            except Song.DoesNotExist:
                return Response({"error": "Song not found in this session"}, status=404)
            
            if list_type == 'playlist':
                # Get the current playlist_sequence to remove
                removed_sequence = song_to_remove.playlist_sequence
                
                # Set playlist_sequence to 0 for the removed song
                song_to_remove.playlist_sequence = 0
                song_to_remove.save()
                
                # Reorder remaining songs (move all higher sequences down by 1)
                if removed_sequence and removed_sequence > 0:
                    reordered_count = Song.objects.filter(
                        session=session,
                        playlist_sequence__gt=removed_sequence
                    ).update(playlist_sequence=models.F('playlist_sequence') - 1)
                else:
                    reordered_count = 0
                    
                list_name = "playlist"
                
            else:  # list_type == 'vibe'
                # Get the current vibe_sequence to remove
                removed_sequence = song_to_remove.vibe_sequence
                
                # Set vibe_sequence to 0 for the removed song
                song_to_remove.vibe_sequence = 0
                song_to_remove.save()
                
                # Reorder remaining songs (move all higher sequences down by 1)
                if removed_sequence and removed_sequence > 0:
                    reordered_count = Song.objects.filter(
                        session=session,
                        vibe_sequence__gt=removed_sequence
                    ).update(vibe_sequence=models.F('vibe_sequence') - 1)
                else:
                    reordered_count = 0
                    
                list_name = "vibe"
            
            return Response({
                "success": True,
                "message": f"Successfully removed song from {list_name} and reordered {reordered_count} songs",
                "removed_song_id": song_id,
                "reordered_songs": reordered_count
            })
            
        except Session.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)
        except Exception as e:
            return Response({"error": f"Failed to remove song from list: {str(e)}"}, status=500)


class ClearVibeView(APIView):
    serializer_class = ClearVibeResponseSerializer
    
    @extend_schema(
        description='Clear all songs from vibe list by setting vibe_sequence to 0',
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Session ID"
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        
        # Validate session
        is_valid, error_response = validate_session(session_id)
        if not is_valid:
            return error_response
        
        try:
            session = Session.objects.get(session_id=session_id)
            
            # Set vibe_sequence = 0 for all songs in the session that have a vibe_sequence
            cleared_count = Song.objects.filter(
                session=session,
                vibe_sequence__isnull=False,
                vibe_sequence__gt=0
            ).update(vibe_sequence=0)
            
            return Response({
                "success": True,
                "message": f"Successfully cleared vibe sequence for {cleared_count} songs",
                "cleared_songs": cleared_count
            })
            
        except Session.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)
        except Exception as e:
            return Response({"error": f"Failed to clear vibe list: {str(e)}"}, status=500)


class RecommendView(APIView):
    serializer_class = RecommendResponseSerializer
    
    @extend_schema(
        description='Get track recommendations based on artist using Last.fm similarity algorithm',
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Session ID"
            ),
            OpenApiParameter(
                name="artist_name",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Artist name to base recommendations on"
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        artist_name = request.query_params.get("artist_name")
        
        # Validate session
        is_valid, error_response = validate_session(session_id)
        if not is_valid:
            return error_response
        
        if not artist_name:
            return Response({"error": "artist_name required"}, status=400)
        
        try:
            # Get recommendations using the sophisticated algorithm
            recommendations_data = recommend_tracks(artist_name)
            return Response(recommendations_data)
            
        except Exception as e:
            return Response({"error": f"Failed to generate recommendations: {str(e)}"}, status=500)


class AddRecommendationsView(APIView):
    serializer_class = AddPlaylistVibeResponseSerializer
    
    @extend_schema(
        description='Get track recommendations and add them to session playlist/vibe with popularity data',
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Session ID"
            ),
            OpenApiParameter(
                name="artist_name",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Artist name to base recommendations on"
            ),
            OpenApiParameter(
                name="add_to_playlist",
                required=False,
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Add to playlist (default: true)"
            ),
            OpenApiParameter(
                name="add_to_vibe",
                required=False,
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Add to vibe (default: true)"
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        artist_name = request.query_params.get("artist_name")
        add_to_playlist = request.query_params.get("add_to_playlist", "true").lower() == "true"
        add_to_vibe = request.query_params.get("add_to_vibe", "true").lower() == "true"
        
        # Validate session
        is_valid, error_response = validate_session(session_id)
        if not is_valid:
            return error_response
        
        if not artist_name:
            return Response({"error": "artist_name required"}, status=400)
        
        try:
            # Get session object
            session = Session.objects.get(session_id=session_id)
            
            # Get recommendations using the sophisticated algorithm
            recommendations_data = recommend_tracks(artist_name)
            recommendations = recommendations_data.get("results", {}).get("recommendations", [])
            
            if not recommendations:
                return Response({
                    "results": {
                        "message": "No recommendations found",
                        "added_count": 0
                    }
                }, status=200)
            
            added_songs = []
            added_count = 0
            
            for rec in recommendations:
                song_name = rec.get("name", "")
                artist_name_rec = rec.get("artist_name", "")
                artist_mbid = rec.get("artist_mbid", "")
                song_mbid = rec.get("mbid", "")
                popularity = rec.get("popularity", 0)
                
                if not song_name or not artist_name_rec:
                    continue
                
                # Check if song already exists in this session
                existing_song = Song.objects.filter(
                    session=session,
                    song_title=song_name,
                    artist_name=artist_name_rec
                ).first()
                
                if existing_song:
                    continue  # Skip if already exists
                
                # Calculate sequences
                vibe_sequence = None
                playlist_sequence = None
                
                if add_to_vibe:
                    max_vibe_seq = Song.objects.filter(
                        session=session,
                        vibe_sequence__isnull=False
                    ).aggregate(
                        max_seq=models.Max('vibe_sequence')
                    )['max_seq']
                    vibe_sequence = (max_vibe_seq or 0) + 1
                
                if add_to_playlist:
                    max_playlist_seq = Song.objects.filter(
                        session=session,
                        playlist_sequence__isnull=False
                    ).aggregate(
                        max_seq=models.Max('playlist_sequence')
                    )['max_seq']
                    playlist_sequence = (max_playlist_seq or 0) + 1
                
                # Create new song record
                new_song = Song.objects.create(
                    session=session,
                    artist_id=artist_mbid,
                    artist_name=artist_name_rec,
                    song_id=song_mbid,
                    song_title=song_name,
                    song_popularity=popularity,  # Use popularity from recommendation
                    vibe_sequence=vibe_sequence,
                    playlist_sequence=playlist_sequence,
                    playlist_hist_sequence=0,
                    is_playing=False,
                    is_played=False
                )
                
                added_songs.append({
                    "song_title": song_name,
                    "artist_name": artist_name_rec,
                    "popularity": popularity,
                    "vibe_sequence": vibe_sequence,
                    "playlist_sequence": playlist_sequence
                })
                added_count += 1
            
            return Response({
                "results": {
                    "message": f"Successfully added {added_count} recommended songs",
                    "added_count": added_count,
                    "added_songs": added_songs,
                    "seed_artist": recommendations_data.get("results", {}).get("seed_artist", ""),
                    "similar_artists": recommendations_data.get("results", {}).get("similar_artists", [])
                }
            })
            
        except Exception as e:
            return Response({"error": f"Failed to add recommendations: {str(e)}"}, status=500)


class AddSongView(APIView):
    serializer_class = AddPlaylistVibeResponseSerializer
    
    @extend_schema(
        description='Add a song to playlist and/or vibe with flexible list_type parameter',
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Session ID"
            ),
            OpenApiParameter(
                name="list_type",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Comma-separated list types: 'playlist', 'vibe', or 'playlist,vibe'"
            ),
            OpenApiParameter(
                name="artist_id",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Artist ID (optional)"
            ),
            OpenApiParameter(
                name="artist_name",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Artist name"
            ),
            OpenApiParameter(
                name="song_id",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Song ID (optional)"
            ),
            OpenApiParameter(
                name="song_title",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Song title"
            ),
            OpenApiParameter(
                name="song_popularity",
                required=False,
                type=int,
                location=OpenApiParameter.QUERY,
                description="Song popularity (optional, defaults to 0)"
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        list_type = request.query_params.get("list_type")
        artist_id = request.query_params.get("artist_id", "")
        artist_name = request.query_params.get("artist_name")
        song_id = request.query_params.get("song_id", "")
        song_title = request.query_params.get("song_title")
        song_popularity = request.query_params.get("song_popularity", "0")
        
        # Validate session
        is_valid, error_response = validate_session(session_id)
        if not is_valid:
            return error_response
        
        # Validate required parameters
        if not list_type:
            return Response({"error": "list_type required"}, status=400)
        if not artist_name:
            return Response({"error": "artist_name required"}, status=400)
        if not song_title:
            return Response({"error": "song_title required"}, status=400)
        
        # Parse list_type - can be "playlist", "vibe", or "playlist,vibe"
        list_types = [lt.strip().lower() for lt in list_type.split(",")]
        valid_types = ["playlist", "vibe"]
        
        for lt in list_types:
            if lt not in valid_types:
                return Response({"error": f"Invalid list_type '{lt}'. Must be 'playlist', 'vibe', or 'playlist,vibe'"}, status=400)
        
        add_to_playlist = "playlist" in list_types
        add_to_vibe = "vibe" in list_types
        
        # Convert popularity to int
        try:
            popularity = int(song_popularity) if song_popularity.isdigit() else 0
        except:
            popularity = 0
        
        try:
            # Get session object
            session = Session.objects.get(session_id=session_id)
            
            # Check if song already exists in this session
            existing_song = Song.objects.filter(
                session=session,
                song_title=song_title,
                artist_name=artist_name
            ).first()
            
            if existing_song:
                return Response({"error": "Song already exists in this session"}, status=400)
            
            # Calculate sequences based on list_type
            vibe_sequence = None
            playlist_sequence = None
            
            if add_to_vibe:
                # Increment all existing vibe sequences by 1
                Song.objects.filter(
                    session=session,
                    vibe_sequence__isnull=False
                ).update(vibe_sequence=models.F('vibe_sequence') + 1)
                
                # Set new song vibe_sequence = 1
                vibe_sequence = 1
            
            if add_to_playlist:
                # Get max playlist_sequence and add 1
                max_playlist_seq = Song.objects.filter(
                    session=session,
                    playlist_sequence__isnull=False
                ).aggregate(
                    max_seq=models.Max('playlist_sequence')
                )['max_seq']
                playlist_sequence = (max_playlist_seq or 0) + 1
            
            # Create new song record
            new_song = Song.objects.create(
                session=session,
                artist_id=artist_id,
                artist_name=artist_name,
                song_id=song_id,
                song_title=song_title,
                song_popularity=popularity,
                vibe_sequence=vibe_sequence,
                playlist_sequence=playlist_sequence,
                playlist_hist_sequence=0,  # Always set to 0
                is_playing=False,  # Always set to False
                is_played=False    # Always set to False
            )
            
            return Response({
                "results": {
                    "message": f"Song '{song_title}' by '{artist_name}' added successfully",
                    "song_id": new_song.id,
                    "added_to_playlist": add_to_playlist,
                    "added_to_vibe": add_to_vibe,
                    "vibe_sequence": vibe_sequence,
                    "playlist_sequence": playlist_sequence,
                    "song_popularity": popularity
                }
            })
            
        except Exception as e:
            return Response({"error": f"Failed to add song: {str(e)}"}, status=500)


class ClearSessionSongsView(APIView):
    @extend_schema(
        description='Clear all songs from a session (both playlist and vibe)',
        parameters=[
            OpenApiParameter(
                name="session_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Session ID"
            )
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'description': 'Whether operation was successful'},
                    'message': {'type': 'string', 'description': 'Success message'},
                    'deleted_songs': {'type': 'integer', 'description': 'Number of songs deleted'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Missing session_id parameter'}
                }
            },
            404: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Session not found'}
                }
            },
            500: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Server error'}
                }
            }
        }
    )
    def post(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        
        # Validate session
        is_valid, error_response = validate_session(session_id)
        if not is_valid:
            return error_response
        
        try:
            session = Session.objects.get(session_id=session_id)
            
            # Delete all songs for this session
            deleted_count = Song.objects.filter(session=session).count()
            Song.objects.filter(session=session).delete()
            
            return Response({
                "success": True,
                "message": f"Successfully cleared {deleted_count} songs from session",
                "deleted_songs": deleted_count
            })
            
        except Session.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)
        except Exception as e:
            return Response({"error": f"Failed to clear session songs: {str(e)}"}, status=500)


# SPOTIFY

def _auth_header(request):
    """
    Extract Spotify access token from Session model and format as Authorization header.
    
    Args:
        request (HttpRequest): Django request object containing session_id parameter
        
    Returns:
        dict: Authorization header with Bearer token, or None if no token exists
        
    Note:
        Access tokens are stored in the Session model spotify_access_token field.
        Tokens typically expire after 1 hour.
    """
    session_id = request.query_params.get("session_id") or request.data.get("session_id")
    if not session_id:
        return None
    
    try:
        session = Session.objects.get(session_id=session_id)
        token = session.spotify_access_token
        if not token:
            return None
        return {"Authorization": f"Bearer {token}"}
    except Session.DoesNotExist:
        return None


class SpotifyDevicesView(APIView):
    """
    Retrieve all available Spotify Connect devices for the authenticated user.
    
    Returns a list of devices where Spotify can play music, including:
    - Desktop/mobile Spotify apps
    - Web players
    - Smart speakers and other Connect-enabled devices
    - Device metadata: name, type, volume, active status
    """
    
    @extend_schema(
        description='Get all available Spotify Connect devices for the authenticated user',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'devices': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'string', 'description': 'Device ID'},
                                'is_active': {'type': 'boolean', 'description': 'Whether device is currently active'},
                                'name': {'type': 'string', 'description': 'Device name'},
                                'type': {'type': 'string', 'description': 'Device type (Computer, Smartphone, etc.)'},
                                'volume_percent': {'type': 'integer', 'description': 'Device volume (0-100)'}
                            }
                        }
                    }
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Authentication error'}
                }
            }
        }
    )
    def get(self, request, *args, **kwargs):
        headers = _auth_header(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
            
        try:
            r = requests.get("https://api.spotify.com/v1/me/player/devices", headers=headers, timeout=15)
            
            # Handle different HTTP status codes
            if r.status_code == 401:
                return Response({"error": "Spotify token expired or invalid"}, status=401)
            elif r.status_code == 403:
                return Response({"error": "Spotify API access forbidden"}, status=403)
            elif r.status_code == 429:
                return Response({"error": "Spotify API rate limit exceeded"}, status=429)
            elif r.status_code >= 500:
                return Response({"error": f"Spotify API server error: {r.status_code}"}, status=502)
            elif not r.ok:
                return Response({"error": f"Spotify API error: {r.status_code}"}, status=r.status_code)
            
            # Try to parse JSON response
            try:
                return Response(r.json())
            except ValueError:
                # If JSON parsing fails, return the raw text or empty response
                return Response({"devices": [], "error": "Invalid response from Spotify API"})
                
        except requests.exceptions.Timeout:
            return Response({"error": "Spotify API request timed out"}, status=504)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to Spotify API"}, status=503)
        except Exception as e:
            # Log the actual error for debugging
            import logging
            logging.error(f"SpotifyDevicesView error: {str(e)}")
            return Response({"error": f"Internal error: {str(e)}"}, status=500)


class SpotifyCurrentlyPlayingView(APIView):
    """
    Get information about the user's current playback, including track details.
    
    Provides detailed information about the currently playing track:
    - Track name, artist(s), album
    - Playback progress and duration
    - Playback context (playlist, album, etc.)
    - Device information
    """
    
    @extend_schema(
        description='Get information about the currently playing track',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'item': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'Track name'},
                            'artists': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'name': {'type': 'string', 'description': 'Artist name'}
                                    }
                                }
                            },
                            'album': {
                                'type': 'object',
                                'properties': {
                                    'name': {'type': 'string', 'description': 'Album name'}
                                }
                            },
                            'duration_ms': {'type': 'integer', 'description': 'Track duration in milliseconds'}
                        }
                    },
                    'progress_ms': {'type': 'integer', 'description': 'Current playback progress in milliseconds'},
                    'is_playing': {'type': 'boolean', 'description': 'Whether track is currently playing'}
                }
            },
            204: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'description': 'Nothing currently playing'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Authentication error'}
                }
            }
        }
    )
    def get(self, request, *args, **kwargs):
        headers = _auth_header(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
            
        try:
            r = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers, timeout=15)
            
            if r.status_code == 204:  # No content - nothing playing
                return Response({"message": "Nothing currently playing"})
            elif r.status_code == 401:
                return Response({"error": "Spotify token expired or invalid"}, status=401)
            elif r.status_code == 403:
                return Response({"error": "Spotify API access forbidden"}, status=403)
            elif r.status_code == 429:
                return Response({"error": "Spotify API rate limit exceeded"}, status=429)
            elif r.status_code >= 500:
                return Response({"error": f"Spotify API server error: {r.status_code}"}, status=502)
            elif not r.ok:
                return Response({"error": f"Spotify API error: {r.status_code}"}, status=r.status_code)
            
            # Try to parse JSON response
            try:
                return Response(r.json())
            except ValueError:
                return Response({"error": "Invalid response from Spotify API"}, status=502)
                
        except requests.exceptions.Timeout:
            return Response({"error": "Spotify API request timed out"}, status=504)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to Spotify API"}, status=503)
        except Exception as e:
            import logging
            logging.error(f"SpotifyCurrentlyPlayingView error: {str(e)}")
            return Response({"error": f"Internal error: {str(e)}"}, status=500)


class SpotifyPlaybackStateView(APIView):
    """
    Get the user's complete playback state including device and settings.
    
    Returns comprehensive playback information:
    - Currently playing track (if any)
    - Active device details
    - Shuffle and repeat mode settings
    - Playback progress and volume
    - Context information (playlist/album being played)
    """
    
    @extend_schema(
        description='Get complete playback state including device and settings',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'device': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string', 'description': 'Device name'},
                            'volume_percent': {'type': 'integer', 'description': 'Device volume'}
                        }
                    },
                    'shuffle_state': {'type': 'boolean', 'description': 'Shuffle mode state'},
                    'repeat_state': {'type': 'string', 'description': 'Repeat mode (off, context, track)'},
                    'item': {'type': 'object', 'description': 'Currently playing track'},
                    'is_playing': {'type': 'boolean', 'description': 'Whether playback is active'},
                    'progress_ms': {'type': 'integer', 'description': 'Current playback progress'}
                }
            },
            204: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'description': 'No active playback'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Authentication error'}
                }
            }
        }
    )
    def get(self, request, *args, **kwargs):
        headers = _auth_header(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
            
        r = requests.get("https://api.spotify.com/v1/me/player", headers=headers, timeout=15)
        
        if r.status_code == 204:  # No content - nothing playing
            return Response({"message": "No active playback"})
        return Response(r.json())


class SpotifyRecentTracksView(APIView):
    """
    Get the user's recently played tracks history.
    
    Returns the last 10 tracks played by the user, including:
    - Track details (name, artist, album)
    - Timestamp of when each track was played
    - Context information (playlist/album source)
    """
    
    @extend_schema(
        description='Get recently played tracks history (last 10 tracks)',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'items': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'track': {
                                    'type': 'object',
                                    'properties': {
                                        'name': {'type': 'string', 'description': 'Track name'},
                                        'artists': {
                                            'type': 'array',
                                            'items': {
                                                'type': 'object',
                                                'properties': {
                                                    'name': {'type': 'string', 'description': 'Artist name'}
                                                }
                                            }
                                        }
                                    }
                                },
                                'played_at': {'type': 'string', 'description': 'When track was played (ISO 8601)'},
                                'context': {
                                    'type': 'object',
                                    'properties': {
                                        'type': {'type': 'string', 'description': 'Context type (playlist, album, etc.)'},
                                        'href': {'type': 'string', 'description': 'Context URL'}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Authentication error'}
                }
            }
        }
    )
    def get(self, request, *args, **kwargs):
        headers = _auth_header(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
            
        r = requests.get("https://api.spotify.com/v1/me/player/recently-played?limit=10", headers=headers, timeout=15)
        return Response(r.json())


class SpotifyUserProfileView(APIView):
    """
    Get the current user's Spotify profile information.
    
    Returns basic profile data for the authenticated user:
    - Display name and user ID
    - Profile images
    - Follower count
    - Country and subscription level (Premium/Free)
    """
    
    @extend_schema(
        description='Get current user\'s Spotify profile information',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'display_name': {'type': 'string', 'description': 'User display name'},
                    'id': {'type': 'string', 'description': 'User ID'},
                    'images': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'url': {'type': 'string', 'description': 'Profile image URL'}
                            }
                        }
                    },
                    'followers': {
                        'type': 'object',
                        'properties': {
                            'total': {'type': 'integer', 'description': 'Follower count'}
                        }
                    },
                    'country': {'type': 'string', 'description': 'User country'},
                    'product': {'type': 'string', 'description': 'Subscription level (premium/free)'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Authentication error'}
                }
            }
        }
    )
    def get(self, request, *args, **kwargs):
        headers = _auth_header(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
            
        r = requests.get("https://api.spotify.com/v1/me", headers=headers, timeout=15)
        return Response(r.json())


class SpotifySearchTracksView(APIView):
    """
    Search for tracks using Spotify's search API.
    
    Searches across Spotify's catalog for matching tracks and returns
    the first 10 results with complete metadata including:
    - Track name and duration
    - Artist(s) and album information
    - Spotify URI for playback
    - Preview URLs (if available)
    - Popularity scores
    """
    
    @extend_schema(
        description='Search for tracks using Spotify\'s search API',
        parameters=[
            OpenApiParameter(
                name="q",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search query string (artist, track, album, or combination)"
            )
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'tracks': {
                        'type': 'object',
                        'properties': {
                            'items': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'name': {'type': 'string', 'description': 'Track name'},
                                        'artists': {
                                            'type': 'array',
                                            'items': {
                                                'type': 'object',
                                                'properties': {
                                                    'name': {'type': 'string', 'description': 'Artist name'}
                                                }
                                            }
                                        },
                                        'album': {
                                            'type': 'object',
                                            'properties': {
                                                'name': {'type': 'string', 'description': 'Album name'}
                                            }
                                        },
                                        'uri': {'type': 'string', 'description': 'Spotify URI for playback'},
                                        'duration_ms': {'type': 'integer', 'description': 'Track duration'},
                                        'popularity': {'type': 'integer', 'description': 'Popularity score (0-100)'}
                                    }
                                }
                            },
                            'total': {'type': 'integer', 'description': 'Total results available'},
                            'limit': {'type': 'integer', 'description': 'Results limit'}
                        }
                    }
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Missing search query'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Authentication error'}
                }
            }
        }
    )
    def get(self, request, *args, **kwargs):
        query = request.query_params.get("q", "")
        if not query:
            return Response({"error": "No search query provided"}, status=400)
        
        headers = _auth_header(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
        
        try:
            url = f"https://api.spotify.com/v1/search?q={query}&type=track&limit=10"
            r = requests.get(url, headers=headers, timeout=15)
            
            if r.status_code == 401:
                return Response({"error": "Spotify token expired or invalid"}, status=401)
            elif r.status_code == 403:
                return Response({"error": "Spotify API access forbidden"}, status=403)
            elif r.status_code == 429:
                return Response({"error": "Spotify API rate limit exceeded"}, status=429)
            elif r.status_code >= 500:
                return Response({"error": f"Spotify API server error: {r.status_code}"}, status=502)
            elif not r.ok:
                return Response({"error": f"Spotify API error: {r.status_code}"}, status=r.status_code)
            
            try:
                return Response(r.json())
            except ValueError:
                return Response({"error": "Invalid response from Spotify API"}, status=502)
                
        except requests.exceptions.Timeout:
            return Response({"error": "Spotify API request timed out"}, status=504)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to Spotify API"}, status=503)
        except Exception as e:
            import logging
            logging.error(f"SpotifySearchTracksView error: {str(e)}")
            return Response({"error": f"Internal error: {str(e)}"}, status=500)


class SpotifyPlayTrackView(APIView):
    """
    Start playback of a specific track by Spotify URI.
    
    This endpoint immediately starts playing the specified track,
    interrupting any current playback. The track URI can be obtained
    from search results or other Spotify API endpoints.
    """
    
    @extend_schema(
        description='Start playback of a specific track by Spotify URI',
        parameters=[
            OpenApiParameter(
                name="device_id",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Target device for playback (optional)"
            )
        ],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'track_uri': {
                        'type': 'string',
                        'description': 'Spotify track URI (e.g., spotify:track:4iV5W9uYEdYUVa79Axb7Rh)'
                    }
                },
                'required': ['track_uri'],
                'example': {'track_uri': 'spotify:track:4iV5W9uYEdYUVa79Axb7Rh'}
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer', 'description': 'HTTP status from Spotify API'},
                    'message': {'type': 'string', 'description': 'Result message'},
                    'response': {'type': 'string', 'description': 'Response body from Spotify API'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Missing or invalid track URI'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Authentication error'}
                }
            }
        }
    )
    def post(self, request, *args, **kwargs):
        
        headers = _auth_header(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
        
        track_uri = request.data.get("track_uri")
        device_id = request.query_params.get("device_id")
        
        if not track_uri:
            return Response({"error": "No track URI provided"}, status=400)
        
        try:
            # Build Spotify API URL with optional device targeting
            url = f"https://api.spotify.com/v1/me/player/play"
            if device_id:
                url += f"?device_id={device_id}"
            
            # Spotify expects URIs in an array format
            payload = {"uris": [track_uri]}
            
            r = requests.put(url, headers=headers, json=payload, timeout=15)
            
            if r.status_code == 204:
                return Response({
                    "status": r.status_code,
                    "message": "Track started successfully",
                    "response": "No response body"
                })
            elif r.status_code == 401:
                return Response({"error": "Spotify token expired or invalid"}, status=401)
            elif r.status_code == 403:
                return Response({"error": "Spotify API access forbidden"}, status=403)
            elif r.status_code == 404:
                return Response({"error": "No active device found. Open Spotify on a device first."}, status=404)
            elif r.status_code == 429:
                return Response({"error": "Spotify API rate limit exceeded"}, status=429)
            elif r.status_code >= 500:
                return Response({"error": f"Spotify API server error: {r.status_code}"}, status=502)
            else:
                return Response({
                    "status": r.status_code,
                    "message": "Error playing track",
                    "response": r.text if r.text else "No response body",
                    "error": f"Spotify API returned status {r.status_code}"
                }, status=r.status_code)
                
        except requests.exceptions.Timeout:
            return Response({"error": "Spotify API request timed out"}, status=504)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to Spotify API"}, status=503)
        except Exception as e:
            import logging
            logging.error(f"SpotifyPlayTrackView error: {str(e)}")
            return Response({"error": f"Internal error: {str(e)}"}, status=500)


class SpotifyPlayView(APIView):
    """
    Resume playbook or start a default playlist if no active context exists.
    
    This endpoint attempts to resume the current playback context (playlist,
    album, or queue). If there's no active context to resume, it will
    automatically start playing Spotify's "Today's Top Hits" playlist.
    """
    
    @extend_schema(
        description='Resume playback or start default playlist if no active context',
        parameters=[
            OpenApiParameter(
                name="device_id",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Target device for playback (optional)"
            )
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer', 'description': 'HTTP status from Spotify API'},
                    'url': {'type': 'string', 'description': 'API URL called'},
                    'headers_sent': {'type': 'boolean', 'description': 'Whether auth headers were sent'},
                    'response': {'type': 'string', 'description': 'Response body from Spotify API'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Authentication error'}
                }
            }
        }
    )
    def post(self, request, *args, **kwargs):
        headers = _auth_header(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
        
        device_id = request.query_params.get("device_id")
        url = f"https://api.spotify.com/v1/me/player/play"
        if device_id:
            url += f"?device_id={device_id}"
        
        # Step 1: Try to resume current playback context
        r = requests.put(url, headers=headers, json={}, timeout=15)
        
        # Step 2: If no active context, start a popular playlist
        if r.status_code == 404 and "Device not found" not in r.text:
            # Fallback to Today's Top Hits playlist (globally popular playlist)
            payload = {
                "context_uri": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
                "position_ms": 0  # Start from beginning
            }
            r = requests.put(url, headers=headers, json=payload, timeout=15)
        
        return Response({
            "status": r.status_code,
            "url": url,
            "headers_sent": bool(headers.get("Authorization")),
            "response": r.text if r.text else "No response body"
        })


class SpotifyPauseView(APIView):
    """
    Pause the user's currently active playback.
    
    This endpoint pauses playback on the specified or currently active device.
    The playback position is preserved and can be resumed later.
    """
    
    @extend_schema(
        description='Pause currently active playback',
        parameters=[
            OpenApiParameter(
                name="device_id",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Target device to pause (optional)"
            )
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer', 'description': 'HTTP status from Spotify API (204 = success)'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Authentication error'}
                }
            }
        }
    )
    def post(self, request, *args, **kwargs):
        headers = _auth_header(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
        
        device_id = request.query_params.get("device_id")
        url = f"https://api.spotify.com/v1/me/player/pause"
        if device_id:
            url += f"?device_id={device_id}"
        
        r = requests.put(url, headers=headers, timeout=15)
        return Response({"status": r.status_code})


class SpotifyNextTrackView(APIView):
    """
    Skip to the next track in the user's playback queue.
    
    This endpoint advances to the next track in the current playback context
    (playlist, album, queue, etc.). If shuffle is enabled, the next track 
    will be randomly selected from the remaining tracks in the context.
    """
    
    @extend_schema(
        description='Skip to the next track in playback queue',
        parameters=[
            OpenApiParameter(
                name="device_id",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Target device for the skip command (optional)"
            )
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer', 'description': 'HTTP status from Spotify API (204 = success)'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Authentication error'}
                }
            }
        }
    )
    def post(self, request, *args, **kwargs):
        headers = _auth_header(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
        
        device_id = request.query_params.get("device_id")
        url = f"https://api.spotify.com/v1/me/player/next"
        if device_id:
            url += f"?device_id={device_id}"
        
        r = requests.post(url, headers=headers, timeout=15)
        return Response({"status": r.status_code})


class SpotifyAuthView(APIView):

    @extend_schema(
        description='Initiate Spotify OAuth flow. Returns authorization URL for JSON format or redirects for browser use.',
        parameters=[
            OpenApiParameter(
                name="redirect_uri",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Optional custom redirect URI (defaults to configured SPOTIFY_REDIRECT_URI)"
            ),
            OpenApiParameter(
                name="format",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Response format: 'json' returns authorization URL, 'redirect' redirects to Spotify",
                enum=['json', 'redirect']
            ),
            OpenApiParameter(
                name="session_id",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Session ID to associate with Spotify tokens"
            )
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'authorization_url': {'type': 'string', 'description': 'Spotify authorization URL'},
                    'client_id': {'type': 'string', 'description': 'Spotify client ID'},
                    'redirect_uri': {'type': 'string', 'description': 'Configured redirect URI'},
                    'scopes': {'type': 'string', 'description': 'Requested OAuth scopes'},
                    'instructions': {'type': 'string', 'description': 'Usage instructions'}
                }
            },
            302: {'description': 'Redirect to Spotify authorization page'},
            500: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Error message'}
                }
            }
        }
    )
    def get(self, request, *args, **kwargs):
        # get spotify stuff from settings directly
        try:
            client_id = settings.SPOTIFY_CLIENT_ID
            redirect_uri = request.query_params.get("redirect_uri", getattr(settings, "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/api/spotify/callback/"))
        except Exception as e:
            print("settings problem:", e)
            return Response({"error": "spotify settings not set right"}, status=500)

        scopes = "user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-recently-played"
        
        # Get session_id and include it in the state parameter
        session_id = request.query_params.get("session_id")
        state = session_id if session_id else ""

        qs = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "state": state
        }

        url = "https://accounts.spotify.com/authorize?" + urlencode(qs)
        
        # Check if JSON response is requested or if this is an API call
        response_format = request.query_params.get("format")
        accept_header = request.headers.get('Accept', '')
        
        # Default to JSON for API calls (Swagger, curl with Accept: application/json, etc.)
        # Default to redirect for browser calls
        if response_format == "json" or (response_format != "redirect" and "application/json" in accept_header):
            return Response({
                "authorization_url": url,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scopes": scopes,
                "instructions": "Copy the authorization_url and open it in your browser to authorize the application"
            })
        
        # Default behavior for browser: redirect to Spotify
        return HttpResponseRedirect(url)

    @extend_schema(
        parameters=[
            OpenApiParameter(name="code", required=True, type=str, location=OpenApiParameter.QUERY, description="auth code"),
            OpenApiParameter(name="state", required=False, type=str, location=OpenApiParameter.QUERY, description="state param"),
            OpenApiParameter(name="error", required=False, type=str, location=OpenApiParameter.QUERY, description="error from spotify"),
            OpenApiParameter(name="session_id", required=True, type=str, location=OpenApiParameter.QUERY, description="session id")
        ]
    )
    def post(self, request, *args, **kwargs):
        # check for error
        if request.query_params.get("error"):
            return Response({"error": "spotify said no :("}, status=400)

        code = request.query_params.get("code")
        session_id = request.query_params.get("session_id")
        
        if not code:
            return Response({"error": "missing code"}, status=400)
            
        if not session_id:
            return Response({"error": "missing session_id"}, status=400)

        try:
            client_id = settings.SPOTIFY_CLIENT_ID
            client_secret = settings.SPOTIFY_CLIENT_SECRET
            redirect_uri = settings.SPOTIFY_REDIRECT_URI
        except Exception as e:
            print("settings problem:", e)
            return Response({"error": "spotify settings not configured"}, status=500)

        # auth header
        try:
            raw = f"{client_id}:{client_secret}".encode()
            basic = base64.b64encode(raw).decode()
        except Exception as e:
            print("encoding err:", e)
            return Response({"error": "could not make auth header"}, status=500)

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri
        }

        headers = {"Authorization": "Basic " + basic}

        # request
        try:
            r = requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers)
        except Exception as e:
            print("network err:", e)
            return Response({"error": "network problem"}, status=500)

        if r.status_code != 200:
            # not super detailed
            print("bad status:", r.status_code, r.text)
            return Response({"error": "could not get tokens"}, status=r.status_code)

        try:
            tokens = r.json()
        except Exception:
            tokens = {}

        # Store tokens in Session model instead of Django session
        try:
            session = Session.objects.get(session_id=session_id)
            session.spotify_access_token = tokens.get("access_token", "")
            session.spotify_refresh_token = tokens.get("refresh_token", "")
            session.spotify_user_id = tokens.get("user_id", "")
            
            # Calculate expiry time
            expires_in = tokens.get("expires_in", 3600)  # Default to 1 hour
            from django.utils import timezone
            import datetime
            session.spotify_token_expires = timezone.now() + datetime.timedelta(seconds=expires_in)
            
            session.save()
        except Session.DoesNotExist:
            return Response({"error": "invalid session_id"}, status=400)

        return Response({
            "success": True,
            "message": "ok",
            "access_token": tokens.get("access_token", ""),
            "token_type": tokens.get("token_type", ""),
            "expires_in": tokens.get("expires_in", 0),
            "scope": tokens.get("scope", "")
        }, status=200)


class SpotifyCallbackView(APIView):
    @extend_schema(
        description='Handle Spotify OAuth callback with authorization code',
        parameters=[
            OpenApiParameter(name="code", required=True, type=str, location=OpenApiParameter.QUERY, description="Authorization code from Spotify"),
            OpenApiParameter(name="state", required=False, type=str, location=OpenApiParameter.QUERY, description="State parameter"),
            OpenApiParameter(name="error", required=False, type=str, location=OpenApiParameter.QUERY, description="Error from Spotify")
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'description': 'Whether authorization was successful'},
                    'message': {'type': 'string', 'description': 'Success message'},
                    'access_token': {'type': 'string', 'description': 'Access token'},
                    'token_type': {'type': 'string', 'description': 'Token type'},
                    'expires_in': {'type': 'integer', 'description': 'Token expiration time'},
                    'scope': {'type': 'string', 'description': 'Granted scopes'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Error message'}
                }
            }
        }
    )
    def get(self, request, *args, **kwargs):
        # Handle the callback from Spotify (same logic as the old POST method)
        # Check for error
        if request.query_params.get("error"):
            return HttpResponseRedirect("/?error=spotify_denied")

        code = request.query_params.get("code")
        state = request.query_params.get("state")  # This contains the session_id
        
        if not code:
            return HttpResponseRedirect("/?error=missing_code")
            
        if not state:  # session_id is required
            return HttpResponseRedirect("/?error=missing_session")

        try:
            client_id = settings.SPOTIFY_CLIENT_ID
            client_secret = settings.SPOTIFY_CLIENT_SECRET
            redirect_uri = settings.SPOTIFY_REDIRECT_URI
        except Exception as e:
            print("settings problem:", e)
            return HttpResponseRedirect("/?error=spotify_settings")

        # Auth header
        try:
            raw = f"{client_id}:{client_secret}".encode()
            basic = base64.b64encode(raw).decode()
        except Exception as e:
            print("encoding err:", e)
            return HttpResponseRedirect("/?error=encoding")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri
        }

        headers = {"Authorization": "Basic " + basic}

        # Request tokens
        try:
            r = requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers)
        except Exception as e:
            print("network err:", e)
            return HttpResponseRedirect("/?error=network")

        if r.status_code != 200:
            print("bad status:", r.status_code, r.text)
            return HttpResponseRedirect("/?error=token_exchange")

        try:
            tokens = r.json()
        except Exception:
            tokens = {}

        # Store tokens in Session model instead of Django session
        try:
            session = Session.objects.get(session_id=state)  # state contains session_id
            session.spotify_access_token = tokens.get("access_token", "")
            session.spotify_refresh_token = tokens.get("refresh_token", "")
            session.spotify_user_id = tokens.get("user_id", "")
            
            # Calculate expiry time
            expires_in = tokens.get("expires_in", 3600)  # Default to 1 hour
            from django.utils import timezone
            import datetime
            session.spotify_token_expires = timezone.now() + datetime.timedelta(seconds=expires_in)
            
            session.save()
            
            # Redirect back to the Spotify section with success
            return HttpResponseRedirect("/?spotify=connected")
            
        except Session.DoesNotExist:
            return HttpResponseRedirect("/?error=invalid_session")


class SpotifyRefreshTokenView(APIView):
    @extend_schema(
        description='Refresh Spotify access token using the refresh token stored in session',
        request=None,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'description': 'Whether refresh was successful'},
                    'message': {'type': 'string', 'description': 'Success message'},
                    'access_token': {'type': 'string', 'description': 'New access token'},
                    'token_type': {'type': 'string', 'description': 'Token type (usually "Bearer")'},
                    'expires_in': {'type': 'integer', 'description': 'Token expiration time in seconds'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Error message (no refresh token in session)'}
                }
            },
            500: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Error message (server configuration or network issues)'}
                }
            }
        }
    )
    def post(self, request, *args, **kwargs):
        session_id = request.data.get("session_id") or request.query_params.get("session_id")
        if not session_id:
            return Response({"error": "session_id required"}, status=400)
        
        # Get refresh token from Session model
        try:
            session = Session.objects.get(session_id=session_id)
            refresh_token = session.spotify_refresh_token
            if not refresh_token:
                return Response({"error": "no refresh_token in session"}, status=400)
        except Session.DoesNotExist:
            return Response({"error": "invalid session_id"}, status=400)

        # pull client creds straight from settings again
        try:
            cid = settings.SPOTIFY_CLIENT_ID
            cs = settings.SPOTIFY_CLIENT_SECRET
        except Exception as e:
            print("settings problem:", e)
            return Response({"error": "missing spotify creds"}, status=500)

       #auth 
        try:
            raw2 = f"{cid}:{cs}".encode()
            basic2 = base64.b64encode(raw2).decode()
        except Exception as e:
            print("encoding err:", e)
            return Response({"error": "auth header fail"}, status=500)

        stuff = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        hdrs = {"Authorization": "Basic " + basic2}

        try:
            res = requests.post("https://accounts.spotify.com/api/token", data=stuff, headers=hdrs)
        except Exception as e:
            print("network err:", e)
            return Response({"error": "network problem"}, status=500)

        if res.status_code != 200:
            print("refresh fail:", res.status_code, res.text)
            return Response({"error": "refresh failed"}, status=res.status_code)

        try:
            new_tokens = res.json()
        except Exception:
            new_tokens = {}

        # Update Session model
        session.spotify_access_token = new_tokens.get("access_token", session.spotify_access_token)
        
        # Update expiry time if provided
        expires_in = new_tokens.get("expires_in")
        if expires_in:
            from django.utils import timezone
            import datetime
            session.spotify_token_expires = timezone.now() + datetime.timedelta(seconds=expires_in)
            
        # Update refresh token if provided (sometimes Spotify provides a new one)
        if "refresh_token" in new_tokens:
            session.spotify_refresh_token = new_tokens["refresh_token"]
            
        session.save()

        return Response({
            "success": True,
            "message": "refreshed",
            "access_token": new_tokens.get("access_token", ""),
            "token_type": new_tokens.get("token_type", ""),
            "expires_in": new_tokens.get("expires_in", 0)
        }, status=200)

from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response
from .views import (
    # Session views - note: ViewSets need action methods
    SessionViewSet, SongViewSet,
    # Last.fm search views
    ArtistSearchLFMView, ArtistSearchSongLFMView, SongSearchLFMView,
    # Playlist/Vibe management views
    AddPlaylistVibeView, GetSongsView, OrderPlaylistView, OrderVibeView,
    RemoveListView, ClearVibeView, RecommendView, AddRecommendationsView,
    AddSongView, ClearSessionSongsView, NextSongView
)


class APIRootView(APIView):

    def get(self, request, *args, **kwargs):
        return Response({
                "API": {
                    "start": "/api/sessions/start/ (POST)",
                    "check": "/api/sessions/{id}/check/ (GET)",
                    "stop": "/api/sessions/{id}/stop/ (DELETE)",
                    "artists": "/api/artist-search-lfm/ (GET)",
                    "artist_songs": "/api/artist-search-song-lfm/ (GET)",
                    "songs": "/api/song-search-lfm/ (GET)",
                    "add_to_lists": "/api/add-playlist-vibe/ (POST)",
                    "add_song": "/api/add-song/ (POST)",
                    "get_songs": "/api/get-songs/ (GET)",
                    "order_playlist": "/api/order-playlist/ (POST)",
                    "order_vibe": "/api/order-vibe/ (POST)",
                    "remove_from_list": "/api/remove-list/ (POST)",
                    "clear_vibe": "/api/clear-vibe/ (POST)",
                    "clear_session_songs": "/api/clear-session-songs/ (POST)",
                    "get": "/api/recommend/ (GET)",
                    "add": "/api/add-recommendations/ (POST)",
                    "next_song": "/api/next-song/ (POST)"
                }
            
        })


urlpatterns = [
    # API Root
    path('', APIRootView.as_view(), name='api_root'),
    
    # Session management (ViewSet actions as individual endpoints)
    path('sessions/start/', SessionViewSet.as_view({'post': 'start_session'}), name='start_session'),
    path('sessions/<str:pk>/stop/', SessionViewSet.as_view({'delete': 'stop_session'}), name='stop_session'),
    path('sessions/<str:pk>/check/', SessionViewSet.as_view({'get': 'check_session'}), name='check_session'),
    
    # Songs endpoint (placeholder for future CRUD)
    # path('songs/', SongViewSet.as_view(), name='songs'),
    
    # Last.fm search endpoints
    path('artist-search-lfm/', ArtistSearchLFMView.as_view(), name='artist_search_lfm'),
    path('artist-search-song-lfm/', ArtistSearchSongLFMView.as_view(), name='artist_search_song_lfm'),
    path('song-search-lfm/', SongSearchLFMView.as_view(), name='song_search_lfm'),
    
    # Playlist/Vibe management
    path('add-playlist-vibe/', AddPlaylistVibeView.as_view(), name='add_playlist_vibe'),
    path('add-song/', AddSongView.as_view(), name='add_song'),
    path('get-songs/', GetSongsView.as_view(), name='get_songs'),
    path('order-playlist/', OrderPlaylistView.as_view(), name='order_playlist'),
    path('order-vibe/', OrderVibeView.as_view(), name='order_vibe'),
    path('remove-list/', RemoveListView.as_view(), name='remove_list'),
    path('clear-vibe/', ClearVibeView.as_view(), name='clear_vibe'),
    path('clear-session-songs/', ClearSessionSongsView.as_view(), name='clear_session_songs'),
    
    # Recommendations
    path('recommend/', RecommendView.as_view(), name='recommend'),
    path('add-recommendations/', AddRecommendationsView.as_view(), name='add_recommendations'),
    
    # Next song functionality 
    path('next-song/', NextSongView.as_view(), name='next_song'),
]

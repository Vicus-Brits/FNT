# HELPERS
# headerToken(request) - get Spotify access token , create authorization header
# getDescription(code) - Descriptions for HTTP status codes
# callSpotifyAPI(url, headers, empty204=None, method="GET", json_data=None) 
#   Generic Spotify API caller with error handling

# VIEWS 
# SpotifyAPIRootView - Displays available endpoints 
# SpotifyDevicesView - list playback devices
# SpotifyCurrentlyPlayingView - Current Track info
# SpotifyPlaybackStateView - Spotify playback state (device and player)
# SpotifyRecentTracksView - Last 10 tracks
# SpotifyUserProfileView - User profile information
# SpotifySearchTracksView - Search  Tracks on Spotify
# SpotifyPlayTrackView - Play track (uri)
# SpotifyPlayView - Resumes playback /starts fallback playlist
# SpotifyPauseView - Pauses current track
# SpotifyNextTrackView - Skip track (spotify list)
# SpotifyAuthView - Spotify OAuth authorization flow (GET) and token (POST)
# SpotifyCallbackView - Processes OAuth callback , store token in session
# SpotifyRefreshTokenView - Refreshes token 

import base64
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework.views import APIView
from rest_framework.response import Response

from api.models import Session


# HELPERS 
# header token 
def headerToken(request):
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

# error codes from Spotify API documentation
def getDescription(code):
    if code == 200:
        return "OK - The request has succeeded. The client can read the result of the request in the body and the headers of the response."
    elif code == 201:
        return "Created - The request has been fulfilled and resulted in a new resource being created."
    elif code == 202:
        return "Accepted - The request has been accepted for processing, but the processing has not been completed."
    elif code == 204:
        return "No Content - The request has succeeded but returns no message body."
    elif code == 304:
        return "Not Modified. See Conditional requests."
    elif code == 400:
        return "Bad Request - The request could not be understood by the server due to malformed syntax."
    elif code == 401:
        return "Unauthorized - The request requires user authentication or, if the request included authorization credentials, authorization has been refused."
    elif code == 403:
        return "Forbidden - The server understood the request, but is refusing to fulfill it."
    elif code == 404:
        return "Not Found - The requested resource could not be found."
    elif code == 429:
        return "Too Many Requests - Rate limiting has been applied."
    elif code == 500:
        return "Internal Server Error - Please report this error."
    elif code == 502:
        return "Bad Gateway - The server got an invalid response from the upstream server."
    elif code == 503:
        return "Service Unavailable - The server is currently unable to handle the request."
    else:
        return "Unknown status code."

# call api helper 
def callSpotifyAPI(url, headers, empty204=None, method="GET", json_data=None):
    # make request
    try:
        if method.upper() == "POST":
            result = requests.post(url, headers=headers, json=json_data, timeout=15)
        elif method.upper() == "PUT":
            result = requests.put(url, headers=headers, json=json_data, timeout=15)
        else:
            result = requests.get(url, headers=headers, timeout=15)
    except Exception as e:
        return Response({"error": "Internal error: " + str(e)}, status=500)

    # success
    if result.status_code == 200:
        try:
            return Response(result.json(), status=200)
        except ValueError:
            return Response({"error": "Invalid response from Spotify"}, status=502)

    # null return    
    elif result.status_code == 204:
        payload = {
            "status_code": 204,
            "description": getDescription(204),
        }
        if empty204 is not None:
            payload["message"] = empty204
        return Response(payload, status=200)

    # known error codes
    elif result.status_code in [400, 401, 403, 404, 429, 500, 502, 503]:
        return Response(
            {
                "error": "Spotify error " + str(result.status_code),
                "description": getDescription(result.status_code),
            },
            status=result.status_code,
        )

    # catch
    else:
        return Response(
            {
                "status_code": result.status_code,
                "description": getDescription(result.status_code),
            },
            status=result.status_code,
        )

# SPOTIFY API ROOT  used to view URLS
class SpotifyAPIRootView(APIView):
    def get(self, request, *args, **kwargs):
        API = {
         
                "auth": request.build_absolute_uri("/spotify/auth/"),
                "callback": request.build_absolute_uri("/spotify/callback/"),
                "refresh": request.build_absolute_uri("/spotify/refresh/"),
                "devices": request.build_absolute_uri("/spotify/devices/"),
                "currently_playing": request.build_absolute_uri("/spotify/currently-playing/"),
                "playback_state": request.build_absolute_uri("/spotify/playback-state/"),
                "recent_tracks": request.build_absolute_uri("/spotify/recent-tracks/"),
                "user_profile": request.build_absolute_uri("/spotify/user-profile/"),
                "search_tracks": request.build_absolute_uri("/spotify/search-tracks/?q=query"),
                "play_track": request.build_absolute_uri("/spotify/play-track/"),
                "play": request.build_absolute_uri("/spotify/play/"),
                "pause": request.build_absolute_uri("/spotify/pause/"),
                "next": request.build_absolute_uri("/spotify/next/"),
                "repeat_off": request.build_absolute_uri("/spotify/repeat-off/"),
        }
        return Response({
            "SPOTIFY-API": API
        })


# SPOTIFY
# get Devices
class SpotifyDevicesView(APIView):
    def get(self, request, *args, **kwargs):
        headers = headerToken(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
        return callSpotifyAPI(
            "https://api.spotify.com/v1/me/player/devices",
            headers=headers,
            empty204="No devices available",
        )


# Currently Playing: GET /currently-playing
class SpotifyCurrentlyPlayingView(APIView):
    def get(self, request, *args, **kwargs):
        headers = headerToken(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
        return callSpotifyAPI(
            "https://api.spotify.com/v1/me/player/currently-playing",
            headers=headers,
            empty204="Nothing currently playing",
        )


# Playback state: GET /player/state
class SpotifyPlaybackStateView(APIView):
    def get(self, request, *args, **kwargs):
        headers = headerToken(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
        return callSpotifyAPI(
            "https://api.spotify.com/v1/me/player",
            headers=headers,
            empty204="No active playback",
        )


# Recent tracks   GET /recent-tracks
class SpotifyRecentTracksView(APIView):
    def get(self, request, *args, **kwargs):
        headers = headerToken(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
        return callSpotifyAPI(
            "https://api.spotify.com/v1/me/player/recently-played?limit=10",
            headers=headers,
            empty204="No recent tracks available",
        )


# User GET /me (user profile)
class SpotifyUserProfileView(APIView):
    def get(self, request, *args, **kwargs):
        headers = headerToken(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
        return callSpotifyAPI(
            "https://api.spotify.com/v1/me",
            headers=headers,
            empty204="No user profile data",  # unlikely
        )

# Search Tracks: GET /search-tracks?q=
class SpotifySearchTracksView(APIView):
    def get(self, request, *args, **kwargs):
        query = request.query_params.get("q", "")
        if not query:
            return Response({"error": "No search query provided"}, status=400)
        
        headers = headerToken(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)
        
        url = f"https://api.spotify.com/v1/search?q={query}&type=track&limit=10"
        return callSpotifyAPI(url, headers)


# Play Specific Track  POST /play-track {uri}
class SpotifyPlayTrackView(APIView):
    def post(self, request, *args, **kwargs):
        headers = headerToken(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)

        track_uri = request.data.get("track_uri")
        if not track_uri:
            return Response({"error": "No track URI provided"}, status=400)

        device_id = request.query_params.get("device_id")
        url = "https://api.spotify.com/v1/me/player/play"
        if device_id:
            url += f"?device_id={device_id}"

        payload = {"uris": [track_uri]}
        return callSpotifyAPI(url, headers, empty204="Track started successfully", method="PUT", json_data=payload)


# Play/Resume: POST /play  (fallback playlist)
class SpotifyPlayView(APIView):
    def post(self, request, *args, **kwargs):
        headers = headerToken(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)

        device_id = request.query_params.get("device_id")
        url = "https://api.spotify.com/v1/me/player/play"
        if device_id:
            url += f"?device_id={device_id}"

        # Try to resume first
        response = callSpotifyAPI(url, headers, method="PUT", json_data={})
        
        # If no active context, start a popular playlist
        if hasattr(response, 'status_code') and response.status_code == 404:
            payload = {
                "context_uri": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",  # Today's Top Hits
                "position_ms": 0,
            }
            return callSpotifyAPI(url, headers, method="PUT", json_data=payload)
        
        return response


# Pause   POST /pause
class SpotifyPauseView(APIView):
    def post(self, request, *args, **kwargs):
        headers = headerToken(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)

        device_id = request.query_params.get("device_id")
        url = "https://api.spotify.com/v1/me/player/pause"
        if device_id:
            url += f"?device_id={device_id}"

        return callSpotifyAPI(url, headers, method="PUT")


# Next Track: POST /next
class SpotifyNextTrackView(APIView):
    def post(self, request, *args, **kwargs):
        headers = headerToken(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)

        device_id = request.query_params.get("device_id")
        url = "https://api.spotify.com/v1/me/player/next"
        if device_id:
            url += f"?device_id={device_id}"

        return callSpotifyAPI(url, headers, method="POST")


# Turn off repeat mode: PUT /repeat-off
class SpotifyRepeatOffView(APIView):
    def put(self, request, *args, **kwargs):
        headers = headerToken(request)
        if not headers:
            return Response({"error": "Not authenticated"}, status=401)

        device_id = request.query_params.get("device_id")
        url = "https://api.spotify.com/v1/me/player/repeat?state=off"
        if device_id:
            url += f"&device_id={device_id}"

        return callSpotifyAPI(url, headers, method="PUT", empty204="Repeat mode turned off")


# OAuth: GET /auth (returns auth URL)
class SpotifyAuthView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            client_id = settings.SPOTIFY_CLIENT_ID
            redirect_uri = request.query_params.get(
                "redirect_uri",
                getattr(settings, "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/spotify/callback/"),
            )
        except Exception as e:
            return Response({"error": f"Spotify error: {e}"}, status=500)

        scopes = "user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-recently-played"
        qs = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": scopes,
        }
        url = "https://accounts.spotify.com/authorize?" + urlencode(qs)

        response_format = request.query_params.get("format")
        accept_header = request.headers.get("Accept", "")

        if response_format == "json" or (response_format != "redirect" and "application/json" in accept_header):
            return Response({
                "authorization_url": url,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scopes": scopes,
                "instructions": "Open authorization_url in your browser to authorize this app."
            })

        return HttpResponseRedirect(url)

    # Token Exchange over POST (optional helper)
    def post(self, request, *args, **kwargs):
        if request.query_params.get("error"):
            return Response({"error": "Spotify denied the request"}, status=400)

        code = request.query_params.get("code")
        if not code:
            return Response({"error": "Missing code"}, status=400)

        try:
            client_id = settings.SPOTIFY_CLIENT_ID
            client_secret = settings.SPOTIFY_CLIENT_SECRET
            redirect_uri = settings.SPOTIFY_REDIRECT_URI
        except Exception as e:
            return Response({"error": f"Spotify settings not configured: {e}"}, status=500)

        try:
            raw = f"{client_id}:{client_secret}".encode()
            basic = base64.b64encode(raw).decode()
        except Exception as e:
            return Response({"error": f"Encoding error: {e}"}, status=500)

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        headers = {"Authorization": "Basic " + basic}

        try:
            result = requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers)
        except Exception as e:
            return Response({"error": f"Network error: {e}"}, status=500)

        if result.status_code != 200:
            return Response({"error": "Could not get tokens"}, status=result.status_code)

        try:
            tokens = result.json()
        except Exception:
            tokens = {}

        request.session["spotify"] = tokens
        return Response({
            "success": True,
            "message": "ok",
            "access_token": tokens.get("access_token", ""),
            "token_type": tokens.get("token_type", ""),
            "expires_in": tokens.get("expires_in", 0),
            "scope": tokens.get("scope", ""),
        }, status=200)


# OAuth Callback: GET /callback (redirects)
class SpotifyCallbackView(APIView):
    def get(self, request, *args, **kwargs):
        if request.query_params.get("error"):
            return HttpResponseRedirect("/?error=spotify_denied")

        code = request.query_params.get("code")
        if not code:
            return HttpResponseRedirect("/?error=missing_code")

        try:
            client_id = settings.SPOTIFY_CLIENT_ID
            client_secret = settings.SPOTIFY_CLIENT_SECRET
            redirect_uri = settings.SPOTIFY_REDIRECT_URI
        except Exception:
            return HttpResponseRedirect("/?error=spotify_settings")

        try:
            raw = f"{client_id}:{client_secret}".encode()
            basic = base64.b64encode(raw).decode()
        except Exception:
            return HttpResponseRedirect("/?error=encoding")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        headers = {"Authorization": "Basic " + basic}

        try:
            result = requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers)
        except Exception:
            return HttpResponseRedirect("/?error=network")

        if result.status_code != 200:
            return HttpResponseRedirect("/?error=token_exchange")

        try:
            tokens = result.json()
        except Exception:
            tokens = {}

        # Store tokens in Django session for compatibility
        request.session["spotify"] = tokens
        
        # Also store tokens in Session model for API access
        # Get current session from Django session
        current_session_data = request.session.get("current_session")
        if current_session_data and current_session_data.get("session_id"):
            try:
                session_obj = Session.objects.get(session_id=current_session_data["session_id"])
                session_obj.spotify_access_token = tokens.get("access_token")
                session_obj.spotify_refresh_token = tokens.get("refresh_token")
                # Calculate expiry time
                expires_in = tokens.get("expires_in", 3600)
                from datetime import datetime, timedelta
                session_obj.spotify_token_expires = datetime.now() + timedelta(seconds=expires_in)
                session_obj.save()
            except Session.DoesNotExist:
                pass  # Session not found, continue anyway
        
        return HttpResponseRedirect("/?spotify=connected")


# Refresh Token: POST /refresh-token
class SpotifyRefreshTokenView(APIView):
    def post(self, request, *args, **kwargs):
        # Get session_id from request
        session_id = request.data.get("session_id") or request.query_params.get("session_id")
        
        # First try to get refresh token from Session model
        refresh_token = None
        session_obj = None
        
        if session_id:
            try:
                session_obj = Session.objects.get(session_id=session_id)
                refresh_token = session_obj.spotify_refresh_token
            except Session.DoesNotExist:
                pass
        
        # Fallback to Django session if no session_id or no token in database
        if not refresh_token:
            session_data = request.session.get("spotify", {})
            refresh_token = session_data.get("refresh_token")
        
        if not refresh_token:
            return Response({"error": "No refresh_token available"}, status=400)

        try:
            cid = settings.SPOTIFY_CLIENT_ID
            cs = settings.SPOTIFY_CLIENT_SECRET
        except Exception as e:
            return Response({"error": f"Missing Spotify creds: {e}"}, status=500)

        try:
            raw = f"{cid}:{cs}".encode()
            basic = base64.b64encode(raw).decode()
        except Exception as e:
            return Response({"error": f"Auth header error: {e}"}, status=500)

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        headers = {"Authorization": "Basic " + basic}

        try:
            result = requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers)
        except Exception as e:
            return Response({"error": f"Network error: {e}"}, status=500)

        if result.status_code != 200:
            return Response({"error": "Refresh failed"}, status=result.status_code)

        try:
            new_tokens = result.json()
        except Exception:
            new_tokens = {}

        # Update Django session
        session_data = request.session.get("spotify", {})
        session_data.update(new_tokens)
        request.session["spotify"] = session_data

        # Update Session model if we have a session object
        if session_obj:
            session_obj.spotify_access_token = new_tokens.get("access_token")
            # Only update refresh token if a new one was provided
            if "refresh_token" in new_tokens:
                session_obj.spotify_refresh_token = new_tokens.get("refresh_token")
            # Calculate expiry time
            expires_in = new_tokens.get("expires_in", 3600)
            from datetime import datetime, timedelta
            session_obj.spotify_token_expires = datetime.now() + timedelta(seconds=expires_in)
            session_obj.save()

        return Response({
            "success": True,
            "message": "refreshed",
            "access_token": new_tokens.get("access_token", ""),
            "token_type": new_tokens.get("token_type", ""),
            "expires_in": new_tokens.get("expires_in", 0),
        }, status=200)


# SpotifyDisconnectView - clear sesson tokens
class SpotifyDisconnectView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            session_id = request.data.get("session_id") or request.query_params.get("session_id")
            if not session_id:
                return Response({"error": "session_id required"}, status=400)
                
            # Clear Spotify tokens from Session model
            try:
                session = Session.objects.get(session_id=session_id)
                session.spotify_access_token = None
                session.spotify_refresh_token = None
                session.spotify_token_expires = None
                session.spotify_user_id = None
                session.save()
            except Session.DoesNotExist:
                return Response({"error": "invalid session_id"}, status=400)
            
            return Response({
                "success": True,
                "message": "Successfully disconnected from Spotify"
            }, status=200)
            
        except Exception as e:
            return Response({
                "error": f"Error during disconnect: {str(e)}"
            }, status=500)

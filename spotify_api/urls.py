from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SpotifyAPIRootView, SpotifyAuthView, SpotifyCallbackView, SpotifyRefreshTokenView,
    SpotifyDevicesView, SpotifyCurrentlyPlayingView, SpotifyPlaybackStateView,
    SpotifyRecentTracksView, SpotifyUserProfileView, SpotifySearchTracksView,
    SpotifyPlayTrackView, SpotifyPlayView, SpotifyPauseView, SpotifyNextTrackView,
    SpotifyDisconnectView
)

# DRF router for viewsets (empty for now since we're using APIViews)
router = DefaultRouter()

urlpatterns = [
    # Spotify API Root
    path('', SpotifyAPIRootView.as_view(), name='spotify_api_root'),
    
    # Spotify Authentication & Profile
    path('auth/', SpotifyAuthView.as_view(), name='spotify_auth'),
    path('callback/', SpotifyCallbackView.as_view(), name='spotify_callback'),
    path('refresh/', SpotifyRefreshTokenView.as_view(), name='spotify_refresh_token'),
    path('disconnect/', SpotifyDisconnectView.as_view(), name='spotify_disconnect'),
    
    # Spotify Player Controls
    path('devices/', SpotifyDevicesView.as_view(), name='spotify_devices'),
    path('currently-playing/', SpotifyCurrentlyPlayingView.as_view(), name='spotify_currently_playing'),
    path('playback-state/', SpotifyPlaybackStateView.as_view(), name='spotify_playback_state'),
    path('recent-tracks/', SpotifyRecentTracksView.as_view(), name='spotify_recent_tracks'),
    path('user-profile/', SpotifyUserProfileView.as_view(), name='spotify_user_profile'),
    
    # Spotify Search & Playback
    path('search-tracks/', SpotifySearchTracksView.as_view(), name='spotify_search_tracks'),
    path('play-track/', SpotifyPlayTrackView.as_view(), name='spotify_play_track'),
    path('play/', SpotifyPlayView.as_view(), name='spotify_play'),
    path('pause/', SpotifyPauseView.as_view(), name='spotify_pause'),
    path('next/', SpotifyNextTrackView.as_view(), name='spotify_next_track'),
]

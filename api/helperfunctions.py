import requests
from .api import API_KEY

#Helper function, (call Last.fm API with song name to return arr of songs found)
def find_song(song_name, artist_name=None):
    url = "http://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "track.search",
        "track": song_name,
        "api_key": API_KEY,
        "format": "json",
        "limit": 100,
    }
    
    # Add artist if provided
    if artist_name:
        params["artist"] = artist_name
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # Extract and filter track data
    if "results" in data and "trackmatches" in data["results"]:
        tracks = data["results"]["trackmatches"].get("track", [])
        
        # return selected fields  
        filtered_tracks = []
        for track in tracks:
            filtered_track = {
                "name": track.get("name", ""),
                "artist": track.get("artist", ""),
                "listeners": track.get("listeners", "0"),
                "mbid": track.get("mbid", "")
            }
            filtered_tracks.append(filtered_track)
        
        # Remove duplicates (same name and artist), keep only first instance
        unique_tracks = []
        seen_combinations = set()
        
        for track in filtered_tracks:
            track_key = (track["name"].lower(), track["artist"].lower())
            if track_key not in seen_combinations:
                seen_combinations.add(track_key)
                unique_tracks.append(track)
        
        # Sort by listeners descending
        unique_tracks = sort_tracks_by_listeners(unique_tracks)
        
        return {
            "results": {
                "tracks": unique_tracks
            }
        }
    else:
        return {
            "results": {
                "tracks": []
            }
        }


#Helper function, (call Last.fm API with artist name to return array of artists found)
def find_artist(artist_name):
    url = "http://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "artist.search",
        "artist": artist_name,
        "api_key": API_KEY,
        "format": "json",
        "limit": 100,
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    # Extract and filter artist data
    if "results" in data and "artistmatches" in data["results"]:
        artists = data["results"]["artistmatches"].get("artist", [])
        
        # return selected fields  
        filtered_artists = []
        for artist in artists:
            filtered_artist = {
                "name": artist.get("name", ""),
                "listeners": artist.get("listeners", "0"),
                "mbid": artist.get("mbid", "")
            }
            filtered_artists.append(filtered_artist)
        
        return {
            "results": {
                "artists": filtered_artists
            }
        }
    else:
        return {
            "results": {
                "artists": []
            }
        }

#Helper sort function
def sort_tracks_by_playcount(tracks):
    # Copy list  
    sorted_tracks = tracks[:]

    # sort
    for i in range(len(sorted_tracks) - 1):
        for j in range(len(sorted_tracks) - 1 - i):
            # Get playcount for current
            pc_current = sorted_tracks[j]["playcount"]
            if pc_current.isdigit():
                pc_current = int(pc_current)
            else:
                pc_current = 0

            # Get playcount for next
            pc_next = sorted_tracks[j + 1]["playcount"]
            if pc_next.isdigit():
                pc_next = int(pc_next)
            else:
                pc_next = 0

            # Swap if out of order (want bigger first)
            if pc_current < pc_next:
                sorted_tracks[j], sorted_tracks[j + 1] = sorted_tracks[j + 1], sorted_tracks[j]

    return sorted_tracks


#Helper sort function for listeners
def sort_tracks_by_listeners(tracks):
    # Copy list  
    sorted_tracks = tracks[:]

    # sort
    for i in range(len(sorted_tracks) - 1):
        for j in range(len(sorted_tracks) - 1 - i):
            # Get listeners for current
            listeners_current = sorted_tracks[j]["listeners"]
            if listeners_current.isdigit():
                listeners_current = int(listeners_current)
            else:
                listeners_current = 0

            # Get listeners for next
            listeners_next = sorted_tracks[j + 1]["listeners"]
            if listeners_next.isdigit():
                listeners_next = int(listeners_next)
            else:
                listeners_next = 0

            # Swap if out of order (want bigger first)
            if listeners_current < listeners_next:
                sorted_tracks[j], sorted_tracks[j + 1] = sorted_tracks[j + 1], sorted_tracks[j]

    return sorted_tracks


#Helper function, (call Last.fm API with artist mbid to return top tracks)
def get_top_tracks_for_artist(artist_mbid):
    url = "http://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "artist.gettoptracks",
        "api_key": API_KEY,
        "mbid": artist_mbid,
        "format": "json",
        "limit": 100,
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    # Extract track data
    tracks = data.get("toptracks", {}).get("track", [])
    
    if tracks:
        filtered_tracks = []
        for track in tracks:
            filtered_track = {
                "name": track.get("name", ""),
                "playcount": track.get("playcount", "0"),
                "mbid": track.get("mbid", ""),
                "artist_name": track.get("artist", {}).get("name", ""),
                "artist_mbid": track.get("artist", {}).get("mbid", "")
            }
            # Include all tracks (even without mbid)
            filtered_tracks.append(filtered_track)
        
        # Sort by playcount descending
        filtered_tracks = sort_tracks_by_playcount(filtered_tracks)

        return {
            "results": {
                "tracks": filtered_tracks
            }
        }
    else:
        return {
            "results": {
                "tracks": []
            }
        }


#Helper function, (call Last.fm API with artist name or mbid to return top tracks)
def get_top_tracks_for_artist_by_name(artist_name, artist_mbid=None):
    url = "http://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "artist.gettoptracks",
        "api_key": API_KEY,
        "format": "json",
        "limit": 100,
    }
    
    # Use MBID if provided, otherwise use artist name
    if artist_mbid:
        params["mbid"] = artist_mbid
    else:
        params["artist"] = artist_name
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # Extract track data
    tracks = data.get("toptracks", {}).get("track", [])
    
    if tracks:
        filtered_tracks = []
        for track in tracks:
            filtered_track = {
                "name": track.get("name", ""),
                "playcount": track.get("playcount", "0"),
                "mbid": track.get("mbid", ""),
                "artist_name": track.get("artist", {}).get("name", ""),
                "artist_mbid": track.get("artist", {}).get("mbid", "")
            }
            # Include all tracks (even without mbid)
            filtered_tracks.append(filtered_track)
        
        # Sort by playcount descending
        filtered_tracks = sort_tracks_by_playcount(filtered_tracks)

        return {
            "results": {
                "tracks": filtered_tracks
            }
        }
    else:
        return {
            "results": {
                "tracks": []
            }
        }

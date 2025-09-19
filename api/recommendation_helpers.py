import requests
from .api import API_KEY
from .helperfunctions import find_artist, get_top_tracks_for_artist_by_name


#Helper function to find similar artists based on artist MBID or name (with fallback)
def find_similar_artists(artist_mbid=None, artist_name=None):
    url = "http://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "artist.getsimilar",
        "api_key": API_KEY,
        "format": "json",
        "limit": 100,
    }
    
    # Use MBID first, fallback to artist name
    if artist_mbid and artist_mbid.strip():
        params["mbid"] = artist_mbid
    elif artist_name and artist_name.strip():
        params["artist"] = artist_name
    else:
        return []
    
    try:
        response = requests.get(url, params=params, timeout=10)  # 10 second timeout
        data = response.json()
    except Exception as e:
        return []  # Return empty list on timeout or error
    
    artists = data.get("similarartists", {}).get("artist", [])
    
    if artists:
        # Include artists with or without MBID, match >= 0.3, exclude perfect matches (1.0)
        filtered_artists = []
        for artist in artists:
            match_score = float(artist.get("match", 0))
            if match_score >= 0.3 and match_score != 1.0:
                filtered_artists.append({
                    "name": artist.get("name", ""),
                    "match": artist.get("match", "0"),
                    "mbid": artist.get("mbid", "")  # Can be empty string
                })
        
        return filtered_artists
    else:
        return []


#Helper function to get track similarities for recommendation (with fallback)
def get_track_similarities(track_mbid=None, track_name=None, artist_name=None):
    url = "http://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "track.getsimilar",
        "api_key": API_KEY,
        "format": "json",
        "limit": 25,  # Reduced limit for faster response
    }
    
    # Use MBID first, fallback to track and artist names
    if track_mbid and track_mbid.strip():
        params["mbid"] = track_mbid
    elif track_name and track_name.strip():
        params["track"] = track_name
        if artist_name and artist_name.strip():
            params["artist"] = artist_name
    else:
        return []
    
    try:
        response = requests.get(url, params=params, timeout=10)  # 10 second timeout
        data = response.json()
    except Exception as e:
        return []  # Return empty list on timeout or error
    
    tracks = data.get("similartracks", {}).get("track", [])
    
    if tracks:
        filtered_tracks = []
        for track in tracks:
            # Include tracks with or without MBID, as long as match >= 0.2
            if float(track.get("match", 0)) >= 0.2:
                # Get popularity data (playcount is available, listeners may not be)
                playcount = track.get("playcount", "0")
                listeners = track.get("listeners", "0")
                
                # Convert to int for popularity calculation, default to 0 if not valid
                try:
                    playcount_int = int(playcount) if str(playcount).isdigit() else 0
                    listeners_int = int(listeners) if str(listeners).isdigit() else 0
                    # Use playcount as the primary popularity metric since it's available
                    popularity = playcount_int
                except:
                    popularity = 0
                
                filtered_tracks.append({
                    "name": track.get("name", ""),
                    "artist_name": track.get("artist", {}).get("name", ""),
                    "artist_mbid": track.get("artist", {}).get("mbid", ""),
                    "mbid": track.get("mbid", ""),  # Can be empty string
                    "match": float(track.get("match", 0)),
                    "playcount": playcount_int,
                    "listeners": listeners_int,
                    "popularity": popularity
                })
        
        return filtered_tracks
    else:
        return []


#Main recommendation function based on artist name
def recommend_tracks(artist_name):
    # Step 1: Find the artist
    artist_data = find_artist(artist_name)
    artists = artist_data.get("results", {}).get("artists", [])
    
    if not artists:
        return {
            "results": {
                "recommendations": [],
                "message": "No artists found for the given name"
            }
        }
    
    # Use the first artist (most relevant)
    main_artist = artists[0]
    main_artist_mbid = main_artist.get("mbid", "")
    main_artist_name = main_artist.get("name", artist_name)
    
    # Step 2: Find similar artists - using fallback approach
    try:
        if main_artist_mbid:
            similar_artists = find_similar_artists(artist_mbid=main_artist_mbid)
        else:
            similar_artists = find_similar_artists(artist_name=main_artist_name)
        
        if len(similar_artists) < 2:
            return {
                "results": {
                    "recommendations": [],
                    "message": "Not enough similar artists found"
                }
            }
    except Exception as e:
        return {
            "results": {
                "recommendations": [],
                "message": "Error finding similar artists"
            }
        }
    
    # Get artist information for top 3 artists (main + 2 similar)
    artists_info = [
        {"mbid": main_artist_mbid, "name": main_artist_name},
        {"mbid": similar_artists[0].get("mbid", ""), "name": similar_artists[0]["name"]},
        {"mbid": similar_artists[1].get("mbid", ""), "name": similar_artists[1]["name"]}
    ]
    
    # Step 3: Get top tracks from all 3 artists
    all_seed_tracks = []
    for artist_info in artists_info:
        try:
            mbid = artist_info["mbid"]
            name = artist_info["name"]
            # Use MBID if available, otherwise use name
            if mbid:
                tracks_data = get_top_tracks_for_artist_by_name("", mbid)
            else:
                tracks_data = get_top_tracks_for_artist_by_name(name, "")
            tracks = tracks_data.get("results", {}).get("tracks", [])
            all_seed_tracks.extend(tracks)
        except Exception as e:
            continue  # Skip this artist if there's an error
    
    if not all_seed_tracks:
        return {
            "results": {
                "recommendations": [],
                "message": "No seed tracks found"
            }
        }
    
    # Shuffle and limit seed tracks more aggressively for performance
    import random
    random.shuffle(all_seed_tracks)
    # Limit to max 5 seed tracks to avoid too many API calls
    max_seed_tracks = min(5, len(all_seed_tracks))
    all_seed_tracks = all_seed_tracks[:max_seed_tracks]
    
    # Step 4: Find similar tracks for each seed track (with performance optimization)
    all_similar_tracks = []
    processed_tracks = 0
    max_similar_tracks = 100  # Stop when we have enough candidates
    
    for seed_track in all_seed_tracks:
        track_mbid = seed_track.get("mbid", "")
        track_name = seed_track.get("name", "")
        track_artist = seed_track.get("artist", {}).get("name", "")
        
        # Use MBID if available, otherwise use track name and artist
        try:
            if track_mbid:
                similar_tracks = get_track_similarities(track_mbid=track_mbid)
            elif track_name and track_artist:
                similar_tracks = get_track_similarities(track_name=track_name, artist_name=track_artist)
            else:
                continue  # Skip if we don't have enough info
            
            all_similar_tracks.extend(similar_tracks)
            processed_tracks += 1
            
            # Early termination if we have enough candidates
            if len(all_similar_tracks) >= max_similar_tracks:
                break
                
        except Exception as e:
            # Continue with next track if this one fails
            continue
    
    if not all_similar_tracks:
        # Fallback: if no similar tracks found, return top tracks from similar artists
        fallback_recommendations = []
        for artist_info in artists_info[1:3]:  # Skip main artist, use similar artists
            try:
                mbid = artist_info["mbid"]
                name = artist_info["name"]
                if mbid:
                    tracks_data = get_top_tracks_for_artist_by_name("", mbid)
                else:
                    tracks_data = get_top_tracks_for_artist_by_name(name, "")
                tracks = tracks_data.get("results", {}).get("tracks", [])
                for track in tracks[:5]:  # Top 5 from each similar artist
                    # Get popularity from playcount
                    playcount = track.get("playcount", "0")
                    try:
                        popularity = int(playcount) if str(playcount).isdigit() else 0
                    except:
                        popularity = 0
                    
                    fallback_recommendations.append({
                        "name": track.get("name", ""),
                        "artist_name": track.get("artist_name", ""),
                        "artist_mbid": track.get("artist_mbid", ""),
                        "mbid": track.get("mbid", ""),
                        "count_instance": 1,
                        "avg_match": 0.5,
                        "popularity": popularity
                    })
            except Exception as e:
                continue
        
        if fallback_recommendations:
            return {
                "results": {
                    "recommendations": fallback_recommendations[:10],
                    "seed_artist": main_artist_name,
                    "similar_artists": [similar_artists[0]["name"], similar_artists[1]["name"]],
                    "total_candidates": len(fallback_recommendations),
                    "message": f"Found {len(fallback_recommendations[:10])} recommendations (fallback mode)"
                }
            }
        
        return {
            "results": {
                "recommendations": [],
                "message": "No similar tracks found"
            }
        }
    
    # Step 5: Aggregate and rank tracks
    track_stats = {}
    for track in all_similar_tracks:
        track_name = track["name"]
        match_score = track["match"]
        popularity = track.get("popularity", 0)
        
        if track_name in track_stats:
            track_stats[track_name]["count"] += 1
            track_stats[track_name]["total_match"] += match_score
            # Keep the highest popularity value across instances
            track_stats[track_name]["popularity"] = max(track_stats[track_name]["popularity"], popularity)
        else:
            track_stats[track_name] = {
                "count": 1,
                "total_match": match_score,
                "artist_name": track["artist_name"],
                "artist_mbid": track["artist_mbid"],
                "mbid": track["mbid"],
                "popularity": popularity
            }
    
    # Calculate average match and create final results
    recommendations = []
    for track_name, stats in track_stats.items():
        avg_match = stats["total_match"] / stats["count"]
        recommendations.append({
            "name": track_name,
            "artist_name": stats["artist_name"],
            "artist_mbid": stats["artist_mbid"],
            "mbid": stats["mbid"],
            "count_instance": stats["count"],
            "avg_match": round(avg_match, 3),
            "popularity": stats["popularity"]
        })
    
    # Sort by count_instance (descending) then avg_match (descending)
    recommendations.sort(key=lambda x: (x["count_instance"], x["avg_match"]), reverse=True)
    
    # Return top 10
    top_recommendations = recommendations[:10]
    
    return {
        "results": {
            "recommendations": top_recommendations,
            "seed_artist": artists[0]["name"],
            "similar_artists": [similar_artists[0]["name"], similar_artists[1]["name"]],
            "total_candidates": len(all_similar_tracks),
            "message": f"Found {len(top_recommendations)} recommendations"
        }
    }

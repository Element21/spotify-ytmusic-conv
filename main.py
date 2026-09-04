import spotipy
from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic, OAuthCredentials, setup_oauth, LikeStatus
from ytmusicapi.constants import YTM_BASE_API
from ytmusicapi.exceptions import YTMusicServerError

import os, sys, time

youtube_search_strings = []

# Spotify config
scope = "user-library-read"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

# Fetch all saved tracks from Spotify (paginated)
page = 1
limit = 50
offset = 0
spotify_liked_tracks = []
print("Fetching saved tracks from Spotify...")
print()

while True:
    results = sp.current_user_saved_tracks(limit=limit, offset=offset)
    items = results.get("items", [])
    if not items:
        break

    print(f"Spotify Library Page: {page}")
    print()

    spotify_liked_tracks.extend(items)
    offset += len(items)

    if results.get("next") is None:
        break

    page += 1


for item in spotify_liked_tracks:
    track = item["track"]
    youtube_search_strings += [f"{track['name']} - {track['artists'][0]['name']}"]


# YTMusic Config
try:
    yt_client_id = os.environ["YTMUSIC_HEADERS"]
except KeyError as missing_var:
    print(f"ERROR: {missing_var} is not set!")
    sys.exit(1)
print()

# Authenticated client
try:
    yt_auth = YTMusic("browser.json")
except Exception as e:
    print(f"ERROR: Failed to load browser.json: {e}")
    sys.exit(1)

# Head search strings
print(youtube_search_strings[0:5])
print("\n")


# search on YouTube Music, like the first found result using the authenticated client
delay_seconds = 0.5

total = len(youtube_search_strings)
for idx, q in enumerate(youtube_search_strings, start=1):
    print(f"{idx}/{total}: Searching '{q}'...")
    try:
        results = yt_auth.search(q, filter="songs")
    except Exception as e:
        print(f"Search failed for '{q}': {type(e).__name__}: {e}")
        print()
        continue

    video_id = None
    for song in results:
        video_id = song.get("videoId")
        title = song.get("title", "Unknown Title")
        if video_id:
            break
    if not video_id:
        print(f"No videoId found for '{q}', skipping.")
        print()
        continue

    print(f"Found videoId: {video_id}. Adding to favorites...")
    try:
        yt_auth.rate_song(video_id, LikeStatus.LIKE)
        print(f"Liked '{title}' ({video_id})")
    except Exception as e:
        print(f"Failed to like '{title}' ({video_id}): {type(e).__name__}: {e}")

    print()
    time.sleep(delay_seconds)

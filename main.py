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
while True:
    results = sp.current_user_saved_tracks(limit=limit, offset=offset)
    items = results.get('items', [])
    if not items:
        break
    
    print(f"Page {page}")

    spotify_liked_tracks.extend(items)
    offset += len(items)
    
    if results.get('next') is None:
        break

    page += 1

for item in spotify_liked_tracks:
    track = item['track']
    youtube_search_strings += [f"{track['name']} - {track['artists'][0]['name']}"]

# YTMusic Config
try:
    yt_client_id = os.environ['YTMUSIC_CLIENT_ID']
    yt_client_secret = os.environ['YTMUSIC_CLIENT_SECRET']
except KeyError as missing_var:
    print(f"ERROR: {missing_var} is not set!")
    sys.exit(1)

if not os.path.exists("oauth.json"):
    setup_oauth(yt_client_id, yt_client_secret, filepath="oauth.json", open_browser=True)

# Authenticated client (ibrary actions)
yt_auth = YTMusic('oauth.json', oauth_credentials=OAuthCredentials(client_id=yt_client_id, client_secret=yt_client_secret))

# Unauthenticated client (searches)
yt = YTMusic()

print(youtube_search_strings[0:5])

# search on YouTube Music, like the first found result using the authenticated client. Rate-limited.
delay_seconds = 0.5
total = len(youtube_search_strings)
for idx, q in enumerate(youtube_search_strings, start=1):
    print(f"{idx}/{total}: Searching '{q}'...")
    try:
        results = yt.search(q)
    except Exception as e:
        print(f"  Search failed for '{q}':", type(e).__name__, e)
        continue

    video_id = None
    for r in results:
        if isinstance(r, dict) and r.get('videoId'):
            video_id = r.get('videoId')
            break

    if not video_id:
        print(f"  No videoId found for '{q}', skipping.")
        continue

    print(f"  Found videoId: {video_id}. Adding to favorites...")
    try:
        resp = yt_auth.rate_song(video_id, LikeStatus.LIKE)
        print(f"  Liked {video_id}")
    except Exception as e:
        print(f"  Failed to like {video_id}:", type(e).__name__, e)

    time.sleep(delay_seconds)
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
batch_size = 25

pending_add_tokens = []


def flush_add_tokens() -> None:
    """Send current batch of token to youtube music api"""
    global pending_add_tokens

    if not pending_add_tokens:
        return

    try:
        yt_auth.edit_song_library_status(pending_add_tokens)
        print(f"Added {len(pending_add_tokens)} songs to library in one batch")
    except Exception as e:
        print(f"Failed to add a batch of {len(pending_add_tokens)} songs to library: {type(e).__name__}: {e}")
    finally:
        pending_add_tokens = []

total = len(youtube_search_strings)
for idx, q in enumerate(reversed(youtube_search_strings), start=1):
    print(f"{idx}/{total}: Searching '{q}'...")
    try:
        results = yt_auth.search(q, filter="songs")
    except Exception as e:
        print(f"Search failed for '{q}': {type(e).__name__}: {e}")
        print()
        continue

    video_id = None
    add_token = None
    for song in results:
        video_id = song.get("videoId")
        title = song.get("title", "Unknown Title")
        feedback_tokens = song.get("feedbackTokens") or {}
        add_token = feedback_tokens.get("add")
        if video_id:
            break

    print(f"Found videoId: {video_id}. Adding to favorites...")

    if add_token:
        pending_add_tokens.append(add_token)
        print(f"Queued '{title}' ({video_id}) for library add")

        if len(pending_add_tokens) >= batch_size:
            flush_add_tokens()
    else:
        print(f"No library add token found for '{title}' ({video_id}), skipping library add")

    try:
        yt_auth.rate_song(video_id, LikeStatus.LIKE)
        print(f"Liked '{title}' ({video_id})")
    except Exception as e:
        print(f"Failed to like '{title}' ({video_id}): {type(e).__name__}: {e}")

    print()
    time.sleep(delay_seconds)

flush_add_tokens()

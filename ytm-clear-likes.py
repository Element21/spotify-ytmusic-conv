import spotipy
from spotipy.oauth2 import SpotifyOAuth
import ytmusicapi
from ytmusicapi import YTMusic, LikeStatus
from ytmusicapi.constants import YTM_BASE_API
from ytmusicapi.exceptions import YTMusicServerError

import os, sys, time

try:
    yt_headers = os.environ["YTMUSIC_HEADERS"]
except KeyError as missing_var:
    print(f"ERROR: {missing_var} is not set!")
    sys.exit(1)
print()

if not os.path.exists("browser.json"):
    ytmusicapi.setup(filepath="browser.json", headers_raw=yt_headers)


# Authenticated client
try:
    yt_auth = YTMusic("browser.json")
except Exception as e:
    print(f"ERROR: Failed to load browser.json: {e}")
    sys.exit(1)


delay_seconds = 0.5

# Get current ytm library
liked_songs = yt_auth.get_library_songs(limit=9999)

total = len(liked_songs)
for idx, song in enumerate(liked_songs, start=1):
    video_id = song.get("videoId")
    title = song.get("title", "Unknown Title")

    print(f"{idx}/{total}: Deleting '{title}' ({video_id})...")

    try:
        yt_auth.rate_song(video_id, LikeStatus.INDIFFERENT)
    except Exception as e:
        print(f"Failed to delete '{title}' ({video_id}): {type(e).__name__}: {e}")

    time.sleep(delay_seconds)

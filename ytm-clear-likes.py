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
batch_size = 25

pending_remove_tokens = []


def flush_remove_tokens() -> None:
    global pending_remove_tokens

    if not pending_remove_tokens:
        return

    try:
        yt_auth.edit_song_library_status(pending_remove_tokens)
        print(f"Removed {len(pending_remove_tokens)} songs from library in one batch")
    except Exception as e:
        print(f"Failed to remove a batch of {len(pending_remove_tokens)} songs from library: {type(e).__name__}: {e}")
    finally:
        pending_remove_tokens = []

# Get current YTM library and liked songs.
liked_songs = yt_auth.get_liked_songs(limit=9999)
library_songs = yt_auth.get_library_songs(limit=9999)

songs_by_video_id = {}


def add_song(song, source):
    if not isinstance(song, dict):
        return

    video_id = song.get("videoId")
    if not video_id:
        return

    entry = songs_by_video_id.setdefault(
        video_id,
        {
            "videoId": video_id,
            "title": song.get("title", "Unknown Title"),
            "liked": False,
            "remove_tokens": set(),
        },
    )

    if entry["title"] == "Unknown Title" and song.get("title"):
        entry["title"] = song["title"]

    if source == "liked":
        entry["liked"] = True

    feedback_tokens = song.get("feedbackTokens") or {}
    remove_token = feedback_tokens.get("remove")
    if remove_token:
        entry["remove_tokens"].add(remove_token)


liked_tracks = liked_songs.get("tracks", []) if isinstance(liked_songs, dict) else list(liked_songs)
for song in liked_tracks:
    add_song(song, "liked")

for song in library_songs:
    add_song(song, "library")

songs = list(songs_by_video_id.values())
total = len(songs)

for idx, song in enumerate(songs, start=1):
    video_id = song["videoId"]
    title = song["title"]

    print(f"{idx}/{total}: Removing '{title}' ({video_id})...")

    if song["liked"]:
        try:
            yt_auth.rate_song(video_id, LikeStatus.INDIFFERENT)
        except Exception as e:
            print(f"Failed to remove liked status for '{title}' ({video_id}): {type(e).__name__}: {e}")

    if song["remove_tokens"]:
        pending_remove_tokens.extend(song["remove_tokens"])
        print(f"Queued '{title}' ({video_id}) for library removal")

        if len(pending_remove_tokens) >= batch_size:
            flush_remove_tokens()

    time.sleep(delay_seconds)

flush_remove_tokens()

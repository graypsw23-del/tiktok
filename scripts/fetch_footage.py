#!/usr/bin/env python3
"""Fetch free, commercial-use stock video clips of today's animal from Pexels.

Reads data/today_state.json for the search query, downloads a handful of
vertical-friendly clips (prefers HD, landscape-or-square source is fine since
assemble_video.py crops to 9:16), and saves them into the given work dir.

Requires PEXELS_API_KEY in the environment (see config.json / .env).
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "data" / "today_state.json"
PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
MIN_CLIP_DURATION = 3  # seconds, skip clips shorter than this
TARGET_CLIP_COUNT = 5


def get_api_key():
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        config_path = BASE_DIR / "config.json"
        if config_path.exists():
            key = json.loads(config_path.read_text()).get("pexels_api_key")
    if not key:
        print("ERROR: PEXELS_API_KEY not set (env var or config.json)", file=sys.stderr)
        sys.exit(1)
    return key


def search_videos(query, api_key, per_page=15):
    url = f"{PEXELS_SEARCH_URL}?query={urllib.parse.quote(query)}&per_page={per_page}&orientation=portrait"
    req = urllib.request.Request(url, headers={"Authorization": api_key})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def pick_best_file(video):
    # Prefer portrait HD files (matches our 9:16 target most closely), fall back to any HD file.
    candidates = [f for f in video["video_files"] if f.get("height", 0) >= f.get("width", 1)]
    if not candidates:
        candidates = video["video_files"]
    candidates = [f for f in candidates if f.get("height", 0) >= 720] or candidates
    candidates.sort(key=lambda f: f.get("height", 0), reverse=True)
    return candidates[0] if candidates else None


def download_file(url, dest_path):
    urllib.request.urlretrieve(url, dest_path)


def fetch_footage(work_dir, query=None, target_count=TARGET_CLIP_COUNT):
    state = json.loads(STATE_FILE.read_text())
    query = query or state["pexels_query"]
    api_key = get_api_key()

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    results = search_videos(query, api_key)
    videos = [v for v in results.get("videos", []) if v.get("duration", 0) >= MIN_CLIP_DURATION]

    if not videos:
        # broaden the search to the bare animal name if the specific query found nothing
        results = search_videos(state["animal"], api_key)
        videos = [v for v in results.get("videos", []) if v.get("duration", 0) >= MIN_CLIP_DURATION]

    if not videos:
        print(f"ERROR: no Pexels videos found for '{query}' or '{state['animal']}'", file=sys.stderr)
        sys.exit(1)

    downloaded = []
    for i, video in enumerate(videos[:target_count]):
        file_info = pick_best_file(video)
        if not file_info:
            continue
        dest = work_dir / f"clip_{i:02d}.mp4"
        print(f"Downloading clip {i} (video id {video['id']}, {file_info.get('width')}x{file_info.get('height')})...")
        download_file(file_info["link"], dest)
        downloaded.append(str(dest))

    if not downloaded:
        print("ERROR: found videos but failed to download any files", file=sys.stderr)
        sys.exit(1)

    manifest = work_dir / "clips_manifest.json"
    manifest.write_text(json.dumps(downloaded, indent=2))
    print(f"Downloaded {len(downloaded)} clips to {work_dir}")
    return downloaded


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("work_dir")
    parser.add_argument("--query", default=None)
    args = parser.parse_args()
    fetch_footage(args.work_dir, query=args.query)

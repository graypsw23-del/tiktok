#!/usr/bin/env python3
"""Generate a free TTS voiceover of today's script using edge-tts.

edge-tts is a free wrapper around Microsoft Edge's "Read Aloud" service -
no API key required. We request word-level boundary events so
assemble_video.py can burn in captions that highlight word-by-word in sync
with the voiceover.

Writes:
    <work_dir>/voiceover.mp3
    <work_dir>/word_timings.json   [{"word": "If", "start": 0.0, "end": 0.2}, ...]
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

import edge_tts

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPT_FILE = BASE_DIR / "data" / "today_script.txt"

TICKS_PER_SECOND = 10_000_000
DEFAULT_VOICE = "en-US-GuyNeural"


async def synthesize(text, voice, audio_path, timings_path):
    communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    word_timings = []
    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / TICKS_PER_SECOND
                end = start + chunk["duration"] / TICKS_PER_SECOND
                word_timings.append({"word": chunk["text"], "start": start, "end": end})

    if not word_timings:
        raise RuntimeError("No audio/word-boundary data received from edge-tts")

    timings_path.write_text(json.dumps(word_timings, indent=2))
    return word_timings


def generate_voiceover(work_dir, voice=DEFAULT_VOICE):
    if not SCRIPT_FILE.exists():
        print("ERROR: run generate_script.py first", file=sys.stderr)
        sys.exit(1)

    text = SCRIPT_FILE.read_text().strip()
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    audio_path = work_dir / "voiceover.mp3"
    timings_path = work_dir / "word_timings.json"

    word_timings = asyncio.run(synthesize(text, voice, audio_path, timings_path))
    duration = word_timings[-1]["end"] if word_timings else 0
    print(f"Voiceover written: {audio_path} ({duration:.1f}s, {len(word_timings)} words)")
    return audio_path, timings_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("work_dir")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    args = parser.parse_args()
    generate_voiceover(args.work_dir, voice=args.voice)

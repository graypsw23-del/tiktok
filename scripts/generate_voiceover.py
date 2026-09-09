#!/usr/bin/env python3
"""Generate a free TTS voiceover of today's script using gTTS (Google Translate's
TTS endpoint).

Originally this used edge-tts, which gets real word-boundary events from
Microsoft's service - but edge-tts talks over a WebSocket connection, which
is blocked in some sandboxed/proxied network environments (including the one
this repo was first built in). gTTS uses plain HTTPS requests, which works
everywhere edge-tts didn't. The tradeoff: gTTS has no built-in word-boundary
API, so word timings are *estimated* by splitting the audio's total duration
proportionally across words by character length. This is good enough for
word-by-word burned-in captions but not frame-perfect.

If you later run this on a machine with unrestricted outbound network access
and want edge-tts's slightly more natural voice + exact word timings back,
swap this module for the edge-tts version (see git history) - nothing else
in the pipeline needs to change since both write the same
voiceover.mp3 / word_timings.json shape.

Writes:
    <work_dir>/voiceover.mp3
    <work_dir>/word_timings.json   [{"word": "If", "start": 0.0, "end": 0.2}, ...]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from gtts import gTTS

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPT_FILE = BASE_DIR / "data" / "today_script.txt"

DEFAULT_LANG = "en"
DEFAULT_TLD = "us"  # "us" English accent; try "co.uk" / "com.au" for others


def get_audio_duration(audio_path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def estimate_word_timings(text, duration):
    words = text.split()
    if not words:
        return []
    weights = [max(len(w), 1) for w in words]
    total_weight = sum(weights)
    t = 0.0
    timings = []
    for word, weight in zip(words, weights):
        span = duration * weight / total_weight
        timings.append({"word": word, "start": round(t, 3), "end": round(t + span, 3)})
        t += span
    return timings


def synthesize(text, audio_path, timings_path, lang, tld):
    tts = gTTS(text=text, lang=lang, tld=tld)
    tts.save(str(audio_path))

    duration = get_audio_duration(audio_path)
    word_timings = estimate_word_timings(text, duration)
    if not word_timings:
        raise RuntimeError("No words to time - is today_script.txt empty?")

    timings_path.write_text(json.dumps(word_timings, indent=2))
    return word_timings


def generate_voiceover(work_dir, lang=DEFAULT_LANG, tld=DEFAULT_TLD):
    if not SCRIPT_FILE.exists():
        print("ERROR: run generate_script.py first", file=sys.stderr)
        sys.exit(1)

    text = SCRIPT_FILE.read_text().strip()
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    audio_path = work_dir / "voiceover.mp3"
    timings_path = work_dir / "word_timings.json"

    word_timings = synthesize(text, audio_path, timings_path, lang, tld)
    duration = word_timings[-1]["end"] if word_timings else 0
    print(f"Voiceover written: {audio_path} ({duration:.1f}s, {len(word_timings)} words)")
    return audio_path, timings_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("work_dir")
    parser.add_argument("--lang", default=DEFAULT_LANG)
    parser.add_argument("--tld", default=DEFAULT_TLD, help="accent domain, e.g. us/co.uk/com.au")
    args = parser.parse_args()
    generate_voiceover(args.work_dir, lang=args.lang, tld=args.tld)

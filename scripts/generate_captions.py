#!/usr/bin/env python3
"""Generate TikTok, YouTube Shorts, and Instagram Reels captions for today's video.

Reads data/today_state.json + data/today_script.txt, increments the running
part-number counter in data/part_counter.json, and writes three .txt files
into the given output directory:
    {date}-{animal-slug}-tiktok.txt
    {date}-{animal-slug}-shorts.txt
    {date}-{animal-slug}-reels.txt
"""
import argparse
import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "data" / "today_state.json"
SCRIPT_FILE = BASE_DIR / "data" / "today_script.txt"
COUNTER_FILE = BASE_DIR / "data" / "part_counter.json"

SHORTS_HASHTAGS = ["#shorts", "#animalfacts", "#personalitytest"]
REELS_HASHTAGS = ["#reels", "#animalpersonality", "#whichanimalareyou"]


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def next_part_number():
    if COUNTER_FILE.exists():
        data = json.loads(COUNTER_FILE.read_text())
        part = data.get("next_part", 1)
    else:
        part = 1
    COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    COUNTER_FILE.write_text(json.dumps({"next_part": part + 1}))
    return part


def build_tiktok_caption(state, part, script):
    animal, emoji = state["animal"], state["emoji"]
    hashtags = " ".join(state["hashtags"][:5])
    return (
        f"Part {part}: The {animal} {emoji} Which animal are YOU? \U0001F447\n\n"
        f"{hashtags}"
    )


def build_shorts_caption(state, part, script):
    animal, emoji = state["animal"], state["emoji"]
    first_line = script.split(".")[0].strip() + "."
    hashtags = " ".join(SHORTS_HASHTAGS[:3])
    return (
        f"Part {part}: are you secretly a {animal.lower()} {emoji}? {first_line}\n"
        f"Comment your animal below.\n\n"
        f"{hashtags}"
    )


def build_reels_caption(state, part, script):
    animal, emoji = state["animal"], state["emoji"]
    hashtags = " ".join(REELS_HASHTAGS[:3])
    return (
        f"{animal} energy, part {part} {emoji}\n"
        f"Tag someone who's exactly like this.\n\n"
        f"{hashtags}"
    )


def generate_captions(output_dir):
    state = json.loads(STATE_FILE.read_text())
    script = SCRIPT_FILE.read_text().strip()
    part = next_part_number()

    date = state["date"]
    slug = slugify(state["animal"])
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        f"{date}-{slug}-tiktok.txt": build_tiktok_caption(state, part, script),
        f"{date}-{slug}-shorts.txt": build_shorts_caption(state, part, script),
        f"{date}-{slug}-reels.txt": build_reels_caption(state, part, script),
    }
    for filename, content in files.items():
        (output_dir / filename).write_text(content + "\n")

    return part, list(files.keys())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir")
    args = parser.parse_args()

    if not STATE_FILE.exists() or not SCRIPT_FILE.exists():
        print("ERROR: run pick_animal.py and generate_script.py first", file=sys.stderr)
        sys.exit(1)

    part, filenames = generate_captions(args.output_dir)
    print(f"Part {part} captions written:")
    for f in filenames:
        print(f"  {f}")

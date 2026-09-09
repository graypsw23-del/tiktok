#!/usr/bin/env python3
"""Pick today's animal + hook style + CTA style, avoiding repeats from the last 30 days.

Writes data/today_state.json with the full pick, and appends to data/used_animals.log
(only call mark_used() after the video actually finishes successfully).
"""
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ANIMALS_FILE = BASE_DIR / "scripts" / "animals.json"
USED_LOG = BASE_DIR / "data" / "used_animals.log"
STATE_FILE = BASE_DIR / "data" / "today_state.json"
NO_REPEAT_DAYS = 30


def load_animals():
    with open(ANIMALS_FILE) as f:
        return json.load(f)


def load_recent_used(days=NO_REPEAT_DAYS):
    if not USED_LOG.exists():
        return set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    used = set()
    for line in USED_LOG.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            entry_date = datetime.fromisoformat(entry["date"]).replace(tzinfo=timezone.utc)
            if entry_date >= cutoff:
                used.add(entry["animal"])
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return used


def choose_hook_style():
    return random.choice(["A", "B"])  # roughly 50/50


def choose_cta_style():
    # ~1 in 5 videos gets the duet/stitch bait line, rest get call-to-comment
    return "duet_bait" if random.random() < 0.2 else "call_to_comment"


def pick_animal(force_animal=None):
    animals = load_animals()
    recent = load_recent_used()
    available = [a for a in animals if a["name"] not in recent]

    if force_animal:
        match = next((a for a in animals if a["name"].lower() == force_animal.lower()), None)
        if not match:
            print(f"ERROR: unknown animal '{force_animal}'", file=sys.stderr)
            sys.exit(1)
        chosen = match
    elif available:
        chosen = random.choice(available)
    else:
        # Every animal used in the last 30 days (list too short) - fall back to
        # the least-recently-used animal rather than failing the pipeline.
        print("WARNING: all animals used in the last 30 days, picking any animal", file=sys.stderr)
        chosen = random.choice(animals)

    state = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "animal": chosen["name"],
        "emoji": chosen["emoji"],
        "traits": chosen["traits"],
        "quirks": chosen["quirks"],
        "theories": chosen["theories"],
        "pexels_query": chosen["pexels_query"],
        "hashtags": chosen["hashtags"],
        "hook_style": choose_hook_style(),
        "cta_style": choose_cta_style(),
    }

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))
    return state


def mark_used(state):
    USED_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(USED_LOG, "a") as f:
        f.write(json.dumps({"date": state["date"], "animal": state["animal"]}) + "\n")


if __name__ == "__main__":
    force = sys.argv[1] if len(sys.argv) > 1 else None
    state = pick_animal(force_animal=force)
    print(json.dumps(state, indent=2))

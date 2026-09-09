#!/usr/bin/env python3
"""Generate a punchy 100-150 word personality script for today's animal.

Reads data/today_state.json (written by pick_animal.py) and writes the
script text to data/today_script.txt (and prints it to stdout).

No network / LLM call needed - this is a template engine that mixes and
matches the animal's traits/quirks/theories with randomized connector
phrasing, so repeated animals (after the 30 day cooldown) still read fresh.
"""
import json
import random
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "data" / "today_state.json"
SCRIPT_FILE = BASE_DIR / "data" / "today_script.txt"

MIN_WORDS = 100
MAX_WORDS = 150

TRAIT_CONNECTORS = [
    "Also, {x}.",
    "On top of that, {x}.",
    "Not only that, but {x}.",
    "Plus, {x}.",
    "Add to that: {x}.",
]

QUIRK_CONNECTORS = [
    "Case in point: {x}.",
    "Exhibit A: {x}.",
    "Like, {x}.",
    "For example, {x}.",
    "Proof: {x}.",
]

THEORY_JUSTIFY_OPENERS = [
    "Think about it.",
    "Hear me out.",
    "Stay with me here.",
    "No, seriously, think about it.",
    "It checks out.",
]

THEORY_JUSTIFY_CLOSERS = [
    "That's not a coincidence, that's just {animal} energy.",
    "Coincidence? I don't think so.",
    "Scientists won't confirm it, but we all know it's true.",
    "It's not a theory anymore, it's basically a law of nature.",
    "You can't explain that away, it's just how it works.",
]

CALL_TO_COMMENT = [
    "Which animal are you? Drop it below.",
    "So, which animal are you? Comment and let's find out.",
    "Tell me your animal in the comments, I need to know.",
    "Drop your animal below, I'm curious what we're working with.",
    "Comment your animal, let's see who else is out here like this.",
    "Which one's you? Comment below and let's compare notes.",
]

DUET_BAIT = [
    "Comment your animal and I'll make you one next.",
    "Drop your animal below and yours might be the next video.",
    "Tell me your animal in the comments, I'm doing yours next.",
    "Comment your animal, I'm picking the next one from here.",
]


def word_count(text):
    return len(text.split())


def ensure_period(sentence):
    return sentence if sentence.endswith((".", "!", "?")) else sentence + "."


def build_style_a(state):
    animal = state["animal"]
    traits = list(state["traits"])
    quirks = list(state["quirks"])
    random.shuffle(traits)
    random.shuffle(quirks)

    hook_trait = traits.pop(0)
    sentences = [f"If you're a {animal}, {hook_trait}."]

    remaining_pool = []
    for t in traits:
        remaining_pool.append(("trait", t))
    for q in quirks:
        remaining_pool.append(("quirk", q))
    random.shuffle(remaining_pool)

    cta = pick_cta(state)
    for kind, x in remaining_pool:
        candidate = (
            random.choice(TRAIT_CONNECTORS).format(x=x)
            if kind == "trait"
            else random.choice(QUIRK_CONNECTORS).format(x=x)
        )
        projected = word_count(" ".join(sentences)) + word_count(candidate) + word_count(cta)
        if word_count(" ".join(sentences)) >= MIN_WORDS and projected > MAX_WORDS:
            break
        sentences.append(candidate)
        if word_count(" ".join(sentences)) >= MIN_WORDS:
            break

    sentences.append(cta)
    return " ".join(sentences)


def build_style_b(state):
    animal = state["animal"]
    theories = list(state["theories"])
    traits = list(state["traits"])
    quirks = list(state["quirks"])
    random.shuffle(theories)
    random.shuffle(traits)
    random.shuffle(quirks)

    theory = theories.pop(0)
    sentences = [f"{theory} - here's the theory."]
    sentences.append(random.choice(THEORY_JUSTIFY_OPENERS))

    cta = pick_cta(state)
    justify_pool = [("trait", t) for t in traits] + [("quirk", q) for q in quirks]
    random.shuffle(justify_pool)

    for kind, x in justify_pool:
        candidate = ensure_period(x[0].upper() + x[1:]) if kind == "quirk" else f"Every {animal.lower()} out there, {x}."
        projected = word_count(" ".join(sentences)) + word_count(candidate) + word_count(cta)
        if word_count(" ".join(sentences)) >= MIN_WORDS - 15 and projected > MAX_WORDS:
            break
        sentences.append(candidate)
        if word_count(" ".join(sentences)) >= MIN_WORDS - 15:
            break

    sentences.append(random.choice(THEORY_JUSTIFY_CLOSERS).format(animal=animal.lower()))
    sentences.append(cta)
    return " ".join(sentences)


def pick_cta(state):
    return random.choice(DUET_BAIT if state["cta_style"] == "duet_bait" else CALL_TO_COMMENT)


def generate_script(state):
    if state["hook_style"] == "A":
        script = build_style_a(state)
    else:
        script = build_style_b(state)

    wc = word_count(script)
    attempts = 0
    while wc < MIN_WORDS - 20 and attempts < 5:
        # extremely unlikely fallback: pad with a generic closing line
        script = script[:-1] + " That's just how it goes."
        wc = word_count(script)
        attempts += 1

    return script, wc


if __name__ == "__main__":
    if not STATE_FILE.exists():
        print("ERROR: run pick_animal.py first", file=sys.stderr)
        sys.exit(1)
    state = json.loads(STATE_FILE.read_text())
    script, wc = generate_script(state)
    SCRIPT_FILE.write_text(script)
    print(script)
    print(f"\n[{wc} words]", file=sys.stderr)

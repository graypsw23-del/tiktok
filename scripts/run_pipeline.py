#!/usr/bin/env python3
"""Daily orchestrator: pick animal -> script -> captions -> footage -> voiceover -> assemble.

Usage:
    python3 scripts/run_pipeline.py [--animal Fox] [--output-dir ~/tiktok-daily/output]

Exits 0 on success, 1 on failure. Always appends a result line to logs/pipeline.log.
Reads PEXELS_API_KEY from the environment (or a .env file in the repo root).
"""
import argparse
import json
import os
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

import pick_animal          # noqa: E402
import generate_script       # noqa: E402
import generate_captions     # noqa: E402
import fetch_footage         # noqa: E402
import generate_voiceover    # noqa: E402
import assemble_video        # noqa: E402

LOG_FILE = BASE_DIR / "logs" / "pipeline.log"
WORK_ROOT = BASE_DIR / "work"
DEFAULT_OUTPUT_DIR = Path(os.environ.get("TIKTOK_OUTPUT_DIR", "~/tiktok-daily/output")).expanduser()


def load_dotenv():
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def log_result(status, detail):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} [{status}] {detail}\n")


def run(output_dir, force_animal=None, keep_work_dir=False):
    load_dotenv()

    state = pick_animal.pick_animal(force_animal=force_animal)
    animal = state["animal"]
    print(f"Today's animal: {animal} (hook style {state['hook_style']}, cta {state['cta_style']})")

    script, word_count = generate_script.generate_script(state)
    generate_script.SCRIPT_FILE.write_text(script)
    print(f"Script ({word_count} words):\n{script}\n")

    output_dir = Path(output_dir).expanduser()
    part, caption_files = generate_captions.generate_captions(output_dir)
    print(f"Part {part}. Captions: {caption_files}")

    work_dir = WORK_ROOT / f"{state['date']}-{animal.lower()}"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    clips = fetch_footage.fetch_footage(work_dir)
    generate_voiceover.generate_voiceover(work_dir)

    slug = generate_captions.slugify(animal)
    final_video_path = output_dir / f"{state['date']}-{slug}.mp4"
    assemble_video.assemble_video(
        work_dir, clips,
        work_dir / "voiceover.mp3",
        work_dir / "word_timings.json",
        final_video_path,
    )

    pick_animal.mark_used(state)

    if not keep_work_dir:
        shutil.rmtree(work_dir, ignore_errors=True)

    return {"animal": animal, "part": part, "video": str(final_video_path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--animal", default=None, help="Force a specific animal instead of random pick")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--keep-work-dir", action="store_true", help="Don't delete temp clips/audio after success (debugging)")
    args = parser.parse_args()

    try:
        result = run(args.output_dir, force_animal=args.animal, keep_work_dir=args.keep_work_dir)
        log_result("SUCCESS", f"animal={result['animal']} part={result['part']} video={result['video']}")
        print(f"\nSUCCESS: {result['video']}")
        sys.exit(0)
    except Exception as exc:
        err_trace = traceback.format_exc()
        log_result("FAILURE", f"{exc}\n{err_trace}")
        print(f"\nFAILURE: {exc}", file=sys.stderr)
        print(err_trace, file=sys.stderr)
        sys.exit(1)

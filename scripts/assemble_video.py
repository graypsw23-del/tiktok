#!/usr/bin/env python3
"""Assemble the final 9:16 vertical video with ffmpeg.

Steps:
  1. Concatenate the downloaded stock clips (looping/trimming as needed) to
     at least cover the voiceover duration, cropped/scaled to 1080x1920.
  2. Mix in the voiceover audio track.
  3. Burn in animated (word-by-word highlight) captions using the
     word_timings.json produced by generate_voiceover.py.

Requires ffmpeg + ffprobe on PATH.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

TARGET_W, TARGET_H = 1080, 1920
FONT_SIZE = 72
WORDS_PER_CAPTION_CHUNK = 4  # group words into short on-screen phrases


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result


def ffprobe_duration(path):
    result = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    return float(result.stdout.strip())


def build_background(clips, target_duration, work_dir):
    """Concat clips (looping if needed) and crop/scale to 1080x1920, trimmed to target_duration."""
    work_dir = Path(work_dir)
    normalized = []
    for i, clip in enumerate(clips):
        out = work_dir / f"norm_{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-i", str(clip),
            "-vf",
            f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
            f"crop={TARGET_W}:{TARGET_H},fps=30",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            str(out),
        ])
        normalized.append(out)

    # Loop the normalized clip list until we cover target_duration.
    concat_list_path = work_dir / "concat_list.txt"
    total = 0.0
    lines = []
    idx = 0
    while total < target_duration:
        clip = normalized[idx % len(normalized)]
        lines.append(f"file '{clip.resolve()}'")
        total += ffprobe_duration(clip)
        idx += 1
    concat_list_path.write_text("\n".join(lines))

    background = work_dir / "background_full.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list_path),
        "-c", "copy", str(background),
    ])

    trimmed = work_dir / "background_trimmed.mp4"
    run([
        "ffmpeg", "-y", "-i", str(background), "-t", str(target_duration),
        "-c", "copy", str(trimmed),
    ])
    return trimmed


def escape_drawtext(text):
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’")


def build_caption_filters(word_timings):
    """Group words into short chunks and build ffmpeg drawtext filters, one per chunk."""
    chunks = []
    for i in range(0, len(word_timings), WORDS_PER_CAPTION_CHUNK):
        group = word_timings[i:i + WORDS_PER_CAPTION_CHUNK]
        text = " ".join(w["word"] for w in group)
        chunks.append({"text": text, "start": group[0]["start"], "end": group[-1]["end"]})

    filters = []
    for chunk in chunks:
        text = escape_drawtext(chunk["text"].upper())
        start, end = chunk["start"], chunk["end"]
        filters.append(
            "drawtext=font='sans-serif\\:style=Bold':"
            f"text='{text}':fontcolor=white:fontsize={FONT_SIZE}:"
            "borderw=6:bordercolor=black:x=(w-text_w)/2:y=h*0.72:"
            f"enable='between(t,{start:.3f},{end:.3f})'"
        )
    return ",".join(filters)


def assemble_video(work_dir, clips, voiceover_path, timings_path, output_path):
    work_dir = Path(work_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("ERROR: ffmpeg/ffprobe not found on PATH", file=sys.stderr)
        sys.exit(1)

    voice_duration = ffprobe_duration(voiceover_path)
    target_duration = voice_duration + 0.5  # small tail so audio never gets cut off

    background = build_background(clips, target_duration, work_dir)

    word_timings = json.loads(Path(timings_path).read_text())
    caption_filter = build_caption_filters(word_timings)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(background),
        "-i", str(voiceover_path),
        "-vf", caption_filter,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]
    run(cmd)
    print(f"Final video written: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("work_dir")
    parser.add_argument("output_path")
    parser.add_argument("--clips-manifest", default=None)
    args = parser.parse_args()

    work_dir = Path(args.work_dir)
    manifest_path = Path(args.clips_manifest) if args.clips_manifest else work_dir / "clips_manifest.json"
    clips = json.loads(manifest_path.read_text())
    voiceover_path = work_dir / "voiceover.mp3"
    timings_path = work_dir / "word_timings.json"

    assemble_video(work_dir, clips, voiceover_path, timings_path, args.output_path)

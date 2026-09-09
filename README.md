# Which Animal Are You? — daily TikTok video generator

Fully automated daily pipeline for the "Which Animal Are You?" short-form
video series: picks an animal (no repeats in 30 days), writes a punchy
100-150 word personality script, generates TikTok/Shorts/Reels captions,
pulls free stock footage from Pexels, generates a free TTS voiceover, and
assembles a finished 9:16 video with burned-in animated captions.

## Important: run this on a machine you keep running, not a cloud sandbox

This repo was built in a Claude Code cloud session, which is an ephemeral
container - it gets reclaimed and has a locked-down network policy (it
could not reach `api.pexels.com` or the TTS service at all). None of that
applies to a normal computer or server. **Clone this repo to your own
machine (laptop, desktop, or a server you control) to actually run the
daily pipeline** - that's also where `scripts/setup_cron.sh` needs to run,
since cron jobs only persist on a machine that stays on.

## What was tested where

Built and verified inside the cloud sandbox:
- Animal picker + 30-day no-repeat log (`scripts/pick_animal.py`)
- Script generator, both hook styles, word count 100-150 (`scripts/generate_script.py`)
- TikTok/Shorts/Reels caption generator (`scripts/generate_captions.py`)
- ffmpeg assembly: 9:16 crop, voiceover sync, burned word-by-word captions
  (`scripts/assemble_video.py`) - tested end-to-end with synthetic clips/audio
- Full pipeline orchestration/logging (`scripts/run_pipeline.py`) - tested
  with the network calls mocked out

Written but **not** live-tested (sandbox network policy blocked both hosts
with a 403 - not a code issue, confirmed via direct curl to each host):
- `scripts/fetch_footage.py` (Pexels API)
- `scripts/generate_voiceover.py` (edge-tts, hits `speech.platform.bing.com`)

Run `scripts/verify_setup.sh` on your own machine first - it directly
tests both of these (plus ffmpeg, deps, and the `claude` CLI) before you
turn on the cron job.

## One-time setup on your machine

```bash
git clone <this repo> tiktok && cd tiktok
pip3 install -r requirements.txt
sudo apt install ffmpeg   # or: brew install ffmpeg

cp .env.example .env
# edit .env and paste in your Pexels API key (free, from pexels.com/api)

scripts/verify_setup.sh          # confirms ffmpeg, edge-tts, and Pexels all work
python3 scripts/run_pipeline.py  # generates one real video by hand, end to end
```

Check the output: `~/tiktok-daily/output/<date>-<animal>.mp4` plus three
caption files (`-tiktok.txt`, `-shorts.txt`, `-reels.txt`) next to it. Watch
the video, read the captions, make sure it's what you want before automating.

Once that looks right:

```bash
scripts/setup_cron.sh   # installs a crontab entry for 8:00am daily
```

The cron job calls `scripts/run_daily.sh`, which runs Claude Code headless
(`claude -p`, per `prompts/daily_pipeline_prompt.md`) so it can retry once
on a transient network hiccup or missing dependency, then logs a plain
success/failure line either way.

## Daily output

Every morning by 8am, `~/tiktok-daily/output/` gets:
- `YYYY-MM-DD-animal.mp4` — finished vertical video, ready to post
- `YYYY-MM-DD-animal-tiktok.txt` — TikTok caption (part number + 5 hashtags)
- `YYYY-MM-DD-animal-shorts.txt` — YouTube Shorts caption (2-3 hashtags)
- `YYYY-MM-DD-animal-reels.txt` — Instagram Reels caption (2-3 hashtags)

Your job: open the folder, grab the video + matching captions, post to
TikTok/Shorts/Reels yourself.

## Checking whether a day's run succeeded

```bash
tail -20 logs/pipeline.log      # one line per run: SUCCESS or FAILURE + why
tail -50 logs/claude_cron.log   # full claude -p transcript for the latest run
```

## How the pieces fit together

| File | Role |
|---|---|
| `scripts/animals.json` | 55 animals, each with traits/quirks/"theory" seeds/hashtags/Pexels query |
| `scripts/pick_animal.py` | Picks today's animal + hook style (A/B) + CTA style, dedup'd against `data/used_animals.log` |
| `scripts/generate_script.py` | Template engine (no LLM call needed) mixing traits/quirks into a 100-150 word script |
| `scripts/generate_captions.py` | Writes the 3 platform captions + increments the running part-number counter |
| `scripts/fetch_footage.py` | Downloads ~5 vertical-friendly stock clips from Pexels |
| `scripts/generate_voiceover.py` | Free TTS via `edge-tts`, captures word-level timing for animated captions |
| `scripts/assemble_video.py` | ffmpeg: crop/loop clips to 9:16, sync voiceover, burn word-by-word captions |
| `scripts/run_pipeline.py` | Orchestrates all of the above, writes `logs/pipeline.log` |
| `scripts/run_daily.sh` / `setup_cron.sh` | The actual cron entry point + one-time installer |
| `prompts/daily_pipeline_prompt.md` | What the headless `claude -p` run is told to do (run pipeline, retry transient failures, never silently patch the generation logic) |

## Notes / things you might want to tweak

- **Hook style split**: currently a random 50/50 between style A (straight
  personality breakdown) and style B (unhinged "theory" hook), per your spec.
- **CTA split**: ~1 in 5 videos get the duet/stitch-bait line, matching your spec.
- **Voice**: defaults to `en-US-GuyNeural`. Change with
  `python3 scripts/run_pipeline.py` — edit `DEFAULT_VOICE` in
  `scripts/generate_voiceover.py`, or list other free voices with `edge-tts --list-voices`.
- **Script generation is a template engine, not an LLM call** — it's free,
  fast, and fully testable, but if you'd rather have genuinely fresh
  copywriting each day (at the cost of an API call), swap
  `generate_script.py`'s output for a Claude-generated script instead —
  happy to wire that up if you want it.

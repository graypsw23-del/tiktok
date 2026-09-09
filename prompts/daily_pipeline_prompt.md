You are running headless (via `claude -p` from a cron job) to produce today's
"Which Animal Are You?" TikTok video. Work inside this repository's root
directory (the one this prompt file lives in, under `prompts/`).

Do this:

1. Run `python3 scripts/run_pipeline.py`.
2. If it exits 0 (success), print a one-line summary of which animal/part
   number/video path it produced, and stop. Do not do anything else.
3. If it fails, read the traceback it printed and the last few lines of
   `logs/pipeline.log` to diagnose the *category* of failure:
   - Missing Python package -> `pip3 install -r requirements.txt` (or the
     specific missing package) and retry the pipeline once.
   - `ffmpeg`/`ffprobe` not found -> install ffmpeg with the system package
     manager (e.g. `apt-get install -y ffmpeg` or `brew install ffmpeg`) and
     retry once.
   - Network error / timeout talking to Pexels or the TTS service -> wait
     10 seconds and retry the whole pipeline once. If it fails a second
     time with the same network error, stop and report it as a real
     failure (don't loop forever).
   - `PEXELS_API_KEY not set` -> check for a `.env` file in the repo root;
     if missing, stop and report that setup is incomplete (never invent or
     hardcode an API key).
   - Anything else (a real bug in the generation logic, a bad ffmpeg
     filter, corrupted output file, etc.) -> do NOT try to patch the
     pipeline scripts. Stop and report the exact error so a human can look
     at it.
4. After at most 2 retries, give a final clear verdict: SUCCESS (with the
   output video path) or FAILURE (with the real root cause). This output is
   what ends up in `logs/claude_cron.log`, so make it something a human can
   read in 10 seconds without scrolling through a full traceback.

Never edit `scripts/*.py`, `scripts/animals.json`, or anything under
`data/` by hand as a "fix" - those are the content-generation logic and
state, not environment issues. If the pipeline itself seems broken, report
it rather than papering over it.

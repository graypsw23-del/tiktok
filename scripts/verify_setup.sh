#!/usr/bin/env bash
# One-time local sanity check before you trust the daily cron job.
# Run this on the machine that will actually run the pipeline.
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"
FAIL=0

echo "== ffmpeg =="
if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
    echo "OK: $(ffmpeg -version | head -1)"
else
    echo "MISSING: install ffmpeg (e.g. 'apt install ffmpeg' / 'brew install ffmpeg')"
    FAIL=1
fi

echo
echo "== python deps =="
if python3 -c "import gtts" 2>/dev/null; then
    echo "OK: gTTS importable"
else
    echo "MISSING: run 'pip3 install -r requirements.txt'"
    FAIL=1
fi

echo
echo "== Pexels API key =="
if [ -f .env ]; then
    set -a; source .env; set +a
fi
if [ -z "${PEXELS_API_KEY:-}" ]; then
    echo "MISSING: set PEXELS_API_KEY in .env (see .env.example)"
    FAIL=1
else
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: $PEXELS_API_KEY" \
        "https://api.pexels.com/videos/search?query=fox&per_page=1")
    if [ "$STATUS" = "200" ]; then
        echo "OK: Pexels API reachable and key valid"
    else
        echo "FAILED: Pexels API returned HTTP $STATUS (bad key, or network/firewall blocking api.pexels.com)"
        FAIL=1
    fi
fi

echo
echo "== gTTS (free TTS) =="
if python3 -c "
from gtts import gTTS
gTTS(text='Testing.', lang='en', tld='us').save('/tmp/gtts_test.mp3')
" >/tmp/gtts_test.log 2>&1; then
    if [ -s /tmp/gtts_test.mp3 ]; then
        echo "OK: gTTS produced audio"
        rm -f /tmp/gtts_test.mp3
    else
        echo "FAILED: gTTS ran but produced no audio, see /tmp/gtts_test.log"
        FAIL=1
    fi
else
    echo "FAILED: gTTS could not reach Google Translate's TTS endpoint, see /tmp/gtts_test.log"
    echo "        (this needs outbound HTTPS access to translate.google.com)"
    FAIL=1
fi

echo
echo "== claude CLI (for the cron automation) =="
if command -v claude >/dev/null 2>&1; then
    echo "OK: $(claude --version 2>&1 | head -1)"
else
    echo "MISSING: install Claude Code (https://docs.claude.com/en/docs/claude-code)"
    FAIL=1
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "All checks passed. You can now run: scripts/setup_cron.sh"
else
    echo "Some checks failed - fix those before installing the cron job."
fi
exit $FAIL

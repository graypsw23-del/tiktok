#!/usr/bin/env bash
# Run this ONCE on the machine that will actually generate videos every day
# (your own computer or a server you keep running - NOT the Claude Code
# cloud sandbox, which is ephemeral and can't host a persistent cron job).
#
# Installs a crontab entry that runs scripts/run_daily.sh at 8:00am every day.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_SCRIPT="$REPO_DIR/scripts/run_daily.sh"
CRON_LINE="0 8 * * * $RUN_SCRIPT"

chmod +x "$RUN_SCRIPT"

if ! command -v claude >/dev/null 2>&1; then
    echo "WARNING: 'claude' CLI not found on PATH. Install Claude Code first:" >&2
    echo "  https://docs.claude.com/en/docs/claude-code" >&2
fi

if ! command -v crontab >/dev/null 2>&1; then
    echo "ERROR: 'crontab' not found. Install cron (e.g. 'apt install cron' / 'brew install cron') first." >&2
    exit 1
fi

existing_crontab="$(crontab -l 2>/dev/null || true)"
if echo "$existing_crontab" | grep -qF "$RUN_SCRIPT"; then
    echo "Cron entry already installed for $RUN_SCRIPT, leaving it as-is."
else
    { echo "$existing_crontab"; echo "$CRON_LINE"; } | crontab -
    echo "Installed cron job: $CRON_LINE"
fi

echo
echo "Verify with: crontab -l"
echo "Logs will land in: $REPO_DIR/logs/claude_cron.log and $REPO_DIR/logs/pipeline.log"

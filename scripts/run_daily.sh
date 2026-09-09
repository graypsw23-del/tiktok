#!/usr/bin/env bash
# Entry point for the daily cron job. Invokes Claude Code in headless mode
# (claude -p) to run the pipeline and self-diagnose common failures.
#
# Installed into crontab by scripts/setup_cron.sh - not meant to be run
# manually except for testing.
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

mkdir -p logs
{
    echo "===== $(date -u +%Y-%m-%dT%H:%M:%SZ) starting daily run ====="
    claude -p "$(cat prompts/daily_pipeline_prompt.md)" \
        --allowedTools "Bash" \
        --permission-mode acceptEdits
    echo "===== $(date -u +%Y-%m-%dT%H:%M:%SZ) finished (exit $?) ====="
} >> logs/claude_cron.log 2>&1

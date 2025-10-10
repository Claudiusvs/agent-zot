#!/bin/bash
# Auto-restart watchdog for zotero-mcp indexing
# This script monitors the indexing process and automatically restarts it when it crashes

LOG_FILE="/tmp/zotero-final-clean.log"
TMUX_SESSION="agent-zot-indexing"
VENV_PATH="$HOME/toolboxes/zotero-mcp-env"
CHECK_INTERVAL=60  # Check every 60 seconds

echo "Starting auto-restart watchdog for zotero-mcp indexing..."
echo "Log file: $LOG_FILE"
echo "Tmux session: $TMUX_SESSION"
echo "Check interval: ${CHECK_INTERVAL}s"
echo "---"

while true; do
    # Check if the actual indexing process (not just tmux) is running
    if pgrep -f "zotero-mcp update-db --fulltext" > /dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Process running OK"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - CRASH DETECTED! Restarting..."

        # Kill old tmux session if it exists
        tmux kill-session -t "$TMUX_SESSION" 2>/dev/null

        # Start new tmux session with indexing
        tmux new-session -d -s "$TMUX_SESSION" \
            "source $VENV_PATH/bin/activate && zotero-mcp update-db --fulltext 2>&1 | tee -a $LOG_FILE"

        echo "$(date '+%Y-%m-%d %H:%M:%S') - Restarted in tmux session: $TMUX_SESSION"

        # Wait a bit longer after restart to let it initialize
        sleep 30
    fi

    sleep "$CHECK_INTERVAL"
done

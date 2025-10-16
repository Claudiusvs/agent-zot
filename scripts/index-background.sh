#!/usr/bin/env bash
# Agent-Zot Background Indexing Helper
# Creates a persistent tmux session for long-running indexing jobs

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"
AGENT_ZOT="$PROJECT_DIR/.venv/bin/agent-zot"
LOG_DIR="/tmp"
SESSION_PREFIX="agent-zot"

# Print usage
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Start Agent-Zot indexing in a persistent tmux session that survives:
- Terminal closure
- Shell exit
- Laptop sleep/wake
- SSH disconnection

OPTIONS:
    -f, --full          Full rebuild with fulltext extraction (default)
    -m, --metadata      Metadata-only indexing (fast, no PDF parsing)
    -l, --limit N       Process only first N items (for testing)
    -s, --session NAME  Custom tmux session name (default: agent-zot-index-TIMESTAMP)
    -a, --attach        Attach to session immediately after creation
    -h, --help          Show this help message

EXAMPLES:
    # Full rebuild (10-40 hours for large libraries)
    $(basename "$0") --full

    # Test with first 10 items
    $(basename "$0") --limit 10

    # Metadata-only update (fast)
    $(basename "$0") --metadata

    # Full rebuild with custom session name
    $(basename "$0") --full --session my-index --attach

TMUX COMMANDS:
    # List active sessions
    tmux ls

    # Attach to session
    tmux attach -t agent-zot-index-20251016_140530

    # Detach from session (keeps running)
    Ctrl+B then D

    # Kill session
    tmux kill-session -t agent-zot-index-20251016_140530

MONITORING:
    Logs are saved to: /tmp/agent-zot-index-TIMESTAMP.log
    Watch live: tail -f /tmp/agent-zot-index-TIMESTAMP.log
    Check Qdrant: curl -s http://localhost:6333/collections/zotero_library_qdrant

EOF
    exit 0
}

# Print error and exit
error() {
    echo -e "${RED}ERROR:${NC} $1" >&2
    exit 1
}

# Print info
info() {
    echo -e "${BLUE}INFO:${NC} $1"
}

# Print success
success() {
    echo -e "${GREEN}SUCCESS:${NC} $1"
}

# Print warning
warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

# Check prerequisites
check_prereqs() {
    # Check tmux
    if ! command -v tmux &> /dev/null; then
        error "tmux not found. Install with: brew install tmux"
    fi

    # Check virtual environment
    if [[ ! -f "$AGENT_ZOT" ]]; then
        error "agent-zot not found at: $AGENT_ZOT\nRun: pip install -e . from project root"
    fi

    # Check Qdrant
    if ! curl -sf http://localhost:6333/collections &> /dev/null; then
        warning "Qdrant not responding at http://localhost:6333"
        echo "Start Qdrant with:"
        echo "  docker run -d -p 6333:6333 -v agent-zot-qdrant-data:/qdrant/storage \\"
        echo "    --name agent-zot-qdrant --restart unless-stopped qdrant/qdrant"
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Parse arguments
MODE="full"
LIMIT=""
SESSION_NAME=""
AUTO_ATTACH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--full)
            MODE="full"
            shift
            ;;
        -m|--metadata)
            MODE="metadata"
            shift
            ;;
        -l|--limit)
            LIMIT="$2"
            shift 2
            ;;
        -s|--session)
            SESSION_NAME="$2"
            shift 2
            ;;
        -a|--attach)
            AUTO_ATTACH=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            error "Unknown option: $1\nUse --help for usage information"
            ;;
    esac
done

# Generate session name if not provided
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if [[ -z "$SESSION_NAME" ]]; then
    SESSION_NAME="agent-zot-index-$TIMESTAMP"
fi

# Check if session already exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    error "Session '$SESSION_NAME' already exists.\nAttach with: tmux attach -t $SESSION_NAME\nOr kill with: tmux kill-session -t $SESSION_NAME"
fi

# Build command
CMD="$AGENT_ZOT update-db --force-rebuild"

if [[ "$MODE" == "full" ]]; then
    CMD="$CMD --fulltext"
    MODE_DESC="full rebuild with PDF parsing"
else
    MODE_DESC="metadata-only indexing"
fi

if [[ -n "$LIMIT" ]]; then
    CMD="$CMD --limit $LIMIT"
    MODE_DESC="$MODE_DESC (limit: $LIMIT items)"
fi

# Log file
LOG_FILE="$LOG_DIR/agent-zot-index-$TIMESTAMP.log"

# Build tmux command with completion notification
TMUX_CMD="$CMD 2>&1 | tee $LOG_FILE; echo ''; echo '=== INDEXING COMPLETED AT:' \$(date) '==='; echo 'Session: $SESSION_NAME'; echo 'Log file: $LOG_FILE'; read -p 'Press ENTER to close this session...'"

# Run prerequisites check
check_prereqs

# Print summary
echo ""
info "Creating persistent tmux session for Agent-Zot indexing"
echo ""
echo "  Session name: $SESSION_NAME"
echo "  Mode:         $MODE_DESC"
echo "  Command:      $CMD"
echo "  Log file:     $LOG_FILE"
echo ""

# Create tmux session
info "Starting tmux session..."
if tmux new-session -d -s "$SESSION_NAME" "$TMUX_CMD"; then
    success "Session created successfully!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  📦 Indexing running in background"
    echo ""
    echo "  🔗 Session:    $SESSION_NAME"
    echo "  📄 Log file:   $LOG_FILE"
    echo ""
    echo "  📋 Quick Commands:"
    echo ""
    echo "    # Attach to session (monitor progress)"
    echo "    tmux attach -t $SESSION_NAME"
    echo ""
    echo "    # Detach from session (Ctrl+B then D)"
    echo "    # Session keeps running after detach"
    echo ""
    echo "    # Watch log file"
    echo "    tail -f $LOG_FILE"
    echo ""
    echo "    # Check Qdrant point count"
    echo "    curl -s http://localhost:6333/collections/zotero_library_qdrant | \\"
    echo "      python3 -c \"import sys, json; print(f'Points: {json.load(sys.stdin)[\\\"result\\\"][\\\"points_count\\\"]:,}')\""
    echo ""
    echo "    # Kill session (stops indexing)"
    echo "    tmux kill-session -t $SESSION_NAME"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if [[ "$AUTO_ATTACH" == true ]]; then
        info "Attaching to session..."
        echo ""
        tmux attach -t "$SESSION_NAME"
    fi
else
    error "Failed to create tmux session"
fi

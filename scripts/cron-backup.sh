#!/bin/bash
#
# Automated backup script for cron scheduling (OPTIONAL - commented out for manual use)
#
# NOTE: Currently using manual backups. To enable automation, uncomment the crontab line below.
#
# Schedule examples:
#   Daily at 2 AM:     0 2 * * * /path/to/cron-backup.sh
#   Every 6 hours:     0 */6 * * * /path/to/cron-backup.sh
#   Weekly (Sun 3 AM): 0 3 * * 0 /path/to/cron-backup.sh
#
# To add to cron (OPTIONAL):
#   crontab -e
#   # Add line (COMMENTED OUT BY DEFAULT):
#   # 0 2 * * * /Users/claudiusv.schroder/toolboxes/agent-zot/scripts/cron-backup.sh >> /tmp/agent-zot-backup.log 2>&1
#
# For now, run backups manually:
#   cd /Users/claudiusv.schroder/toolboxes/agent-zot
#   .venv/bin/python scripts/backup.py backup-all

set -e

# Navigate to project directory
cd "$(dirname "$0")/.."

# Activate virtualenv (use .venv, not agent-zot-env)
source .venv/bin/activate

# Timestamp
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting automated backup..."

# Run backup
python scripts/backup.py backup-all --keep-last 5

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup completed"

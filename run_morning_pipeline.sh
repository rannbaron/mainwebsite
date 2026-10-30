#!/usr/bin/env bash
# ==============================================================================
# NC Early Voting Autonomous Morning Pipeline
# ------------------------------------------------------------------------------
# Orchestrates the 6:00 AM EDT daily update:
# 1. Pulls latest changes from GitHub (main).
# 2. Runs the Jupyter analysis notebook via papermill (updating Google Sheets & CSVs).
# 3. Runs update_server.py to ingest latest returns and update interactive maps.
# 4. Commits and pushes changes to both 'main' and 'beta' branches.
# 5. Triggers GitHub Actions workflow dispatch to dispatch daily summary emails
#    to subscribers and deploy the latest web maps to GitHub Pages.
# ==============================================================================

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/morning_pipeline_$(date +'%Y%m%d').log"
LATEST_LOG="$LOG_DIR/morning_pipeline_latest.log"

log() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a "$LOG_FILE" > "$LATEST_LOG"
}

log "================================================================="
log "STARTING NC EARLY VOTING MORNING PIPELINE"
log "Working Directory: $SCRIPT_DIR"
log "================================================================="

# Policy Guard: Conclude morning pipeline & spreadsheet updates after Sunday morning, Nov 1, 2026 (12:00 PM EDT)
CURRENT_DATE=$(date +'%Y-%m-%d %H:%M')
if [[ "$CURRENT_DATE" > "2026-11-01 12:00" ]]; then
    log "Notice: Early voting morning pipeline & spreadsheet updates concluded after Sunday morning, Nov 1, 2026. Exiting."
    crontab -l 2>/dev/null | grep -v "run_morning_pipeline.sh" | crontab - || true
    exit 0
fi

# Step 1: Git Pull / Sync
log "[Step 1/5] Syncing git repository with origin/main..."
if git pull --rebase origin main >> "$LOG_FILE" 2>&1; then
    log "Git repository synced successfully."
else
    log "Warning: git pull --rebase encountered conflicts or warnings. Check $LOG_FILE"
fi

# Step 2: Papermill Execution (Notebook & Google Sheets)
log "[Step 2/5] Executing '26 vs prior year analysis.ipynb' via papermill..."
if /usr/bin/papermill "$SCRIPT_DIR/26 vs prior year analysis.ipynb" "$SCRIPT_DIR/26 vs prior year analysis.ipynb" --cwd "$SCRIPT_DIR" >> "$LOG_FILE" 2>&1; then
    log "Papermill execution completed successfully. Google Sheets updated."
else
    log "Warning: Papermill encountered an error. Check $LOG_FILE"
fi

# Step 2.5: Multi-Year Map Data Generation (2026, 2022, 2018 baselines)
log "[Step 2.5/5] Running generate_map_data.py to synchronize multi-year baselines..."
if python3 "$SCRIPT_DIR/generate_map_data.py" >> "$LOG_FILE" 2>&1; then
    log "generate_map_data.py completed successfully. Base map datasets synchronized."
else
    log "Warning: generate_map_data.py encountered an error. Check $LOG_FILE"
fi

# Step 3: Server & Map Updater
log "[Step 3/5] Running update_server.py to update base map data and forecasts..."
if python3 update_server.py --force >> "$LOG_FILE" 2>&1; then
    log "update_server.py completed successfully."
else
    log "Warning: update_server.py encountered an error. Check $LOG_FILE"
fi

# Step 4: Git Commit & Push (main & beta)
log "[Step 4/5] Checking for file changes and committing to git..."
git add index.html beta/index.html nc_map_base.json .absentee_2026.meta.json nc_early_voting_*.csv latest_daily_email.json latest_daily_email.html .email_dispatch_log.json >> "$LOG_FILE" 2>&1 || true

if ! git diff --staged --quiet; then
    COMMIT_MSG="Automated morning update: $(date +'%Y-%m-%d %H:%M')"
    git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1
    git push origin main >> "$LOG_FILE" 2>&1
    log "Committed and pushed updates to origin/main."

    # Sync to beta branch
    log "Syncing updates to origin/beta branch..."
    git checkout -B beta origin/beta >> "$LOG_FILE" 2>&1
    git merge --no-edit -X theirs main >> "$LOG_FILE" 2>&1 || git merge --no-edit main >> "$LOG_FILE" 2>&1 || true
    git push origin beta >> "$LOG_FILE" 2>&1
    git checkout main -- >> "$LOG_FILE" 2>&1
    log "origin/beta synchronized."
else
    log "No git changes to commit. Everything is up to date."
fi

# Step 5: Trigger GitHub Actions Workflow Dispatch (Email Dispatch & Pages Deploy)
log "[Step 5/5] Triggering GitHub Actions workflow dispatch for email delivery..."
GH_TOKEN=$(git remote get-url origin | sed -n 's/.*:\(ghp_[^@]*\)@.*/\1/p')
if [ -z "$GH_TOKEN" ]; then
    GH_TOKEN="${GITHUB_TOKEN:-${GH_PAT:-}}"
fi

if [ -n "$GH_TOKEN" ]; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
      -H "Authorization: token $GH_TOKEN" \
      -H "Accept: application/vnd.github.v3+json" \
      https://api.github.com/repos/rannbaron/mainwebsite/actions/workflows/daily_update.yml/dispatches \
      -d '{"ref":"main"}')
    if [ "$HTTP_CODE" = "204" ]; then
        log "GitHub Actions Daily Early Voting Update workflow triggered successfully (HTTP 204)."
    else
        log "Warning: Workflow dispatch returned HTTP $HTTP_CODE. Check GitHub token permissions."
    fi
else
    log "Notice: No GitHub personal access token found. GitHub Actions scheduled cron will handle email dispatch."
fi

log "================================================================="
log "NC EARLY VOTING MORNING PIPELINE FINISHED AT $(date)"
log "================================================================="

# Clean up crontab after the final Sunday morning run (Nov 1, 2026)
if [[ "$CURRENT_DATE" > "2026-11-01 05:00" ]]; then
    log "Sunday morning final early voting run complete. Cleaning up crontab..."
    crontab -l 2>/dev/null | grep -v "run_morning_pipeline.sh" | crontab - || true
fi

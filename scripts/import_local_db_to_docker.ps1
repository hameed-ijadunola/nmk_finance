# ──────────────────────────────────────────────
# Import local SQLite DB into the running Docker container
# Usage: .\scripts\import_local_db_to_docker.ps1
# ──────────────────────────────────────────────

$ErrorActionPreference = "Stop"

$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot
$LOCAL_DB     = Join-Path $PROJECT_ROOT "db.sqlite3"
$CONTAINER    = "nmk-finance-app"
$REMOTE_DB    = "/app/data/db.sqlite3"

# 1. Verify local DB exists
if (-not (Test-Path $LOCAL_DB)) {
    Write-Error "Local database not found at: $LOCAL_DB"
    exit 1
}

# 2. Verify container is running
$running = docker ps --filter "name=$CONTAINER" --filter "status=running" -q
if (-not $running) {
    Write-Error "Container '$CONTAINER' is not running. Start it with: docker compose up -d"
    exit 1
}

# 3. Backup existing container DB
Write-Host "Backing up container database..." -ForegroundColor Cyan
docker exec $CONTAINER cp $REMOTE_DB "${REMOTE_DB}.bak" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Backup saved to ${REMOTE_DB}.bak" -ForegroundColor Green
} else {
    Write-Host "  No existing database to back up (OK)" -ForegroundColor Yellow
}

# 4. Copy local DB into container
Write-Host "Copying local database to container..." -ForegroundColor Cyan
docker cp $LOCAL_DB "${CONTAINER}:${REMOTE_DB}"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to copy database to container."
    exit 1
}
Write-Host "  Done." -ForegroundColor Green

# 5. Restart app container
Write-Host "Restarting container..." -ForegroundColor Cyan
docker restart $CONTAINER | Out-Null
Write-Host "  Done." -ForegroundColor Green

# 6. Verify record counts
Write-Host "Verifying data..." -ForegroundColor Cyan
$result = docker exec $CONTAINER python manage.py shell -c `
    "from finance.models import Member, Contribution, Expense; print(f'Members: {Member.objects.count()}, Contributions: {Contribution.objects.count()}, Expenses: {Expense.objects.count()}')"
Write-Host "  $result" -ForegroundColor Green

Write-Host "`nImport complete!" -ForegroundColor Green

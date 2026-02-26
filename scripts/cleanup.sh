#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
#  cleanup.sh  —  Weekly Docker & system cleanup cron
#  Runs: Every Sunday at 02:00 via /etc/cron.d/docker-cleanup
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "═══ Weekly cleanup started ═══"

# ── Stopped containers ────────────────────────────────────────────────────────
log "Removing stopped containers..."
CONTAINERS=$(docker container prune -f 2>&1)
log "  ${CONTAINERS}"

# ── Unused images (older than 7 days) ────────────────────────────────────────
log "Removing unused images older than 7 days..."
IMAGES=$(docker image prune -a -f --filter "until=168h" 2>&1)
log "  ${IMAGES}"

# ── Dangling volumes (NOT named volumes) ─────────────────────────────────────
log "Removing anonymous dangling volumes..."
VOLUMES=$(docker volume prune -f 2>&1)
log "  ${VOLUMES}"

# ── Unused networks ───────────────────────────────────────────────────────────
log "Removing unused networks..."
NETWORKS=$(docker network prune -f 2>&1)
log "  ${NETWORKS}"

# ── System journal (keep 7 days) ─────────────────────────────────────────────
log "Trimming system journal to 7 days..."
journalctl --vacuum-time=7d 2>/dev/null || true

# ── Truncate large log files (> 100MB) ───────────────────────────────────────
log "Truncating oversized log files in /var/log/..."
find /var/log -name "*.log" -size +100M -exec truncate -s 50M {} \; 2>/dev/null || true

# ── Disk usage report ─────────────────────────────────────────────────────────
log "Disk usage after cleanup:"
df -h / | tail -1 | awk '{log "[disk] " $3 " used / " $2 " total (" $5 " full)"}'

log "═══ Cleanup complete ═══"

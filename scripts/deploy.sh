#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
#  deploy.sh  —  Zero-downtime deploy with automated rollback
#  Usage: bash /opt/app/scripts/deploy.sh [IMAGE_TAG]
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} [$(date '+%H:%M:%S')] $*"; }
info() { echo -e "${BLUE}[i]${NC} [$(date '+%H:%M:%S')] $*"; }
warn() { echo -e "${YELLOW}[!]${NC} [$(date '+%H:%M:%S')] $*"; }
die()  { echo -e "${RED}[✗]${NC} [$(date '+%H:%M:%S')] $*" >&2; exit 1; }

# ── Config ────────────────────────────────────────────────────────────────────
APP_DIR="/opt/app"
COMPOSE="docker compose -f ${APP_DIR}/docker-compose.yml"
HEALTH_URL="https://asilbekabdurahmonov.uz"
MAX_RETRIES=12
RETRY_DELAY=5

cd "${APP_DIR}"

echo -e "\n${BOLD}── Deploy: $(date) ──────────────────────────────────────────${NC}"

# ── Capture current container ID for rollback ─────────────────────────────────
CURRENT_CONTAINER=$(${COMPOSE} ps -q web 2>/dev/null | head -1 || echo "")
CURRENT_IMAGE=""
if [[ -n "${CURRENT_CONTAINER}" ]]; then
    CURRENT_IMAGE=$(docker inspect --format='{{.Config.Image}}' "${CURRENT_CONTAINER}" 2>/dev/null || echo "")
    info "Current image: ${CURRENT_IMAGE:-unknown}"
fi

# ── Update image tag if passed ────────────────────────────────────────────────
if [[ -n "${1:-}" ]]; then
    log "Overriding IMAGE_NAME tag to: $1"
    # shellcheck disable=SC2016
    sed -i "s|IMAGE_NAME=.*|IMAGE_NAME=$1|" "${APP_DIR}/.env"
fi

# ── Pull new image ────────────────────────────────────────────────────────────
log "Pulling latest image..."
${COMPOSE} pull web || die "Failed to pull image. Aborting."

# ── Deploy (replace web container only, zero downtime) ───────────────────────
log "Deploying new container..."
${COMPOSE} up -d --no-deps --remove-orphans web

# ── Health check loop ─────────────────────────────────────────────────────────
log "Running health checks (${MAX_RETRIES} attempts × ${RETRY_DELAY}s)..."
HEALTHY=false
for i in $(seq 1 ${MAX_RETRIES}); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 "${HEALTH_URL}" 2>/dev/null || echo "000")
    if [[ "${HTTP_CODE}" =~ ^(200|301|302)$ ]]; then
        log "Health check PASSED (HTTP ${HTTP_CODE}) on attempt ${i}/${MAX_RETRIES}"
        HEALTHY=true
        break
    fi
    warn "Attempt ${i}/${MAX_RETRIES}: HTTP ${HTTP_CODE} — waiting ${RETRY_DELAY}s..."
    sleep ${RETRY_DELAY}
done

# ── Rollback on failure ───────────────────────────────────────────────────────
if [[ "${HEALTHY}" == "false" ]]; then
    warn "Health check failed after ${MAX_RETRIES} attempts."
    if [[ -n "${CURRENT_IMAGE}" ]]; then
        warn "Rolling back to: ${CURRENT_IMAGE}"
        # Update .env to previous image, then redeploy
        sed -i "s|IMAGE_NAME=.*|IMAGE_NAME=${CURRENT_IMAGE}|" "${APP_DIR}/.env"
        ${COMPOSE} up -d --no-deps web
        sleep 10
        # Verify rollback
        RB_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 "${HEALTH_URL}" 2>/dev/null || echo "000")
        if [[ "${RB_CODE}" =~ ^(200|301|302)$ ]]; then
            warn "ROLLBACK SUCCESSFUL — site restored to previous version."
        else
            die "ROLLBACK ALSO FAILED (HTTP ${RB_CODE}). Manual intervention required!"
        fi
    else
        die "No previous image to roll back to. Manual intervention required!"
    fi
    exit 1
fi

# ── Reload Nginx (pick up any config changes) ─────────────────────────────────
log "Reloading Nginx..."
${COMPOSE} exec nginx nginx -s reload || warn "Nginx reload failed (non-fatal)."

# ── Cleanup dangling images ───────────────────────────────────────────────────
log "Pruning dangling images..."
docker image prune -f --filter "until=24h" > /dev/null 2>&1 || true

echo ""
echo -e "${GREEN}${BOLD}  Deployment complete! ✓${NC}"
echo -e "  Site: ${HEALTH_URL}"
echo ""

#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
#  setup-server.sh  —  Idempotent production server bootstrapper
#  Target: Ubuntu 24.04 LTS | 109.199.110.218
#  Run as: root
#  Safe to re-run: YES (every step checks before acting)
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $*"; }
info() { echo -e "${BLUE}[i]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
die()  { echo -e "${RED}[✗] FATAL: $*${NC}" >&2; exit 1; }
step() { echo -e "\n${BOLD}━━━ $* ━━━${NC}"; }

# ── Configuration ─────────────────────────────────────────────────────────────
APP_DIR="/opt/app"
DOMAIN="asilbekabdurahmonov.uz"
LOG_DOMAIN="logs.asilbekabdurahmonov.uz"
EMAIL="admin@${DOMAIN}"
CREDS_FILE="${APP_DIR}/.dozzle_creds"

# ── Sanity checks ─────────────────────────────────────────────────────────────
[[ $EUID -eq 0 ]] || die "This script must be run as root. Use: sudo bash setup-server.sh"
[[ -f /etc/os-release ]] && source /etc/os-release
[[ "${ID:-}" == "ubuntu" ]] || warn "Not Ubuntu — proceeding anyway, but untested."

echo -e "${BOLD}"
echo "══════════════════════════════════════════════════════════"
echo "  Editorial — Production Server Setup"
echo "  Domain: ${DOMAIN}"
echo "  Server: $(hostname -I | awk '{print $1}')"
echo "══════════════════════════════════════════════════════════"
echo -e "${NC}"

# ══ 1. System updates ══════════════════════════════════════════════════════════
step "Step 1/10 — System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    curl wget git unzip \
    apache2-utils \
    ca-certificates \
    gnupg lsb-release \
    openssl \
    fail2ban \
    logrotate
log "System packages up to date."

# ══ 2. UFW Firewall ═══════════════════════════════════════════════════════════
step "Step 2/10 — UFW Firewall"
if ! command -v ufw &>/dev/null; then
    apt-get install -y ufw
fi
ufw --force reset     > /dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    comment 'SSH'
ufw allow 80/tcp    comment 'HTTP'
ufw allow 443/tcp   comment 'HTTPS'
ufw --force enable
log "UFW configured: SSH, HTTP, HTTPS allowed — all else denied."

# ══ 3. Docker ═════════════════════════════════════════════════════════════════
step "Step 3/10 — Docker Engine"
if command -v docker &>/dev/null; then
    info "Docker already installed: $(docker --version)"
else
    log "Installing Docker Engine..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
    log "Docker installed: $(docker --version)"
fi

# ══ 4. Certbot ════════════════════════════════════════════════════════════════
step "Step 4/10 — Certbot"
if command -v certbot &>/dev/null; then
    info "Certbot already installed: $(certbot --version 2>&1)"
else
    log "Installing Certbot..."
    apt-get install -y certbot
    log "Certbot installed."
fi

# ══ 5. App directory structure ════════════════════════════════════════════════
step "Step 5/10 — Directory structure"
mkdir -p "${APP_DIR}"/{nginx,scripts,data}
mkdir -p /var/www/certbot
log "App directory: ${APP_DIR}/"

# ══ 6. Generate Dozzle credentials ════════════════════════════════════════════
step "Step 6/10 — Dozzle credentials"
if [[ -f "${CREDS_FILE}" ]]; then
    info "Using existing credentials from ${CREDS_FILE}"
else
    log "Generating new secure Dozzle credentials..."
    # Use python3 to avoid SIGPIPE from tr|head under set -euo pipefail
    DOZZLE_USERNAME=$(python3 -c "import secrets,string; print(secrets.token_urlsafe(6)[:8])")
    DOZZLE_PASSWORD=$(python3 -c "import secrets,string; print(secrets.token_urlsafe(18)[:24])")
    {
        echo "DOZZLE_USERNAME=${DOZZLE_USERNAME}"
        echo "DOZZLE_PASSWORD=${DOZZLE_PASSWORD}"
    } > "${CREDS_FILE}"
    chmod 600 "${CREDS_FILE}"
    log "Credentials saved to ${CREDS_FILE} (chmod 600)"
fi
# shellcheck disable=SC1090
source "${CREDS_FILE}"

# Create htpasswd for Nginx Basic Auth
log "Generating htpasswd file..."
htpasswd -cb "${APP_DIR}/nginx/.htpasswd_logs" \
    "${DOZZLE_USERNAME}" "${DOZZLE_PASSWORD}"
chmod 644 "${APP_DIR}/nginx/.htpasswd_logs"   # Must be world-readable by nginx user inside container

# ══ 7. Diffie-Hellman parameters ══════════════════════════════════════════════
step "Step 7/10 — DH parameters (2048-bit)"
DH_FILE="${APP_DIR}/nginx/dhparam.pem"
if [[ -f "${DH_FILE}" ]]; then
    info "DH params already exist — skipping (this takes ~2min to generate)."
else
    log "Generating DH parameters (please wait ~2 minutes)..."
    openssl dhparam -out "${DH_FILE}" 2048
    log "DH params generated."
fi

# ══ 8. SSL Certificate (Let's Encrypt) ═══════════════════════════════════════
step "Step 8/10 — SSL Certificate"
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
if [[ -d "${CERT_DIR}" ]]; then
    info "SSL certificates already exist — skipping."
else
    log "Obtaining Let's Encrypt SSL certificates..."
    log "Starting temporary HTTP server for ACME challenge..."

    # Write temp Nginx config
    cat > /tmp/temp-nginx.conf <<'NGINX_TEMP'
server {
    listen 80 default_server;
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    location / { return 200 "setup-in-progress"; add_header Content-Type text/plain; }
}
NGINX_TEMP

    # Start temporary Nginx container
    docker run -d --name temp-certbot-nginx \
        -p 80:80 \
        -v /var/www/certbot:/var/www/certbot:ro \
        -v /tmp/temp-nginx.conf:/etc/nginx/conf.d/default.conf:ro \
        nginx:alpine
    sleep 3

    # Obtain certificate
    certbot certonly --webroot \
        --webroot-path=/var/www/certbot \
        --email "${EMAIL}" \
        --agree-tos \
        --no-eff-email \
        -d "${DOMAIN}" \
        -d "www.${DOMAIN}" \
        -d "${LOG_DOMAIN}"

    # Stop temp container
    docker stop temp-certbot-nginx
    docker rm  temp-certbot-nginx
    log "SSL certificates obtained."
fi

# ══ 9. Cron jobs ══════════════════════════════════════════════════════════════
step "Step 9/10 — Cron jobs"

# Certbot auto-renewal (twice daily, as recommended)
RENEW_CRON="0 3,15 * * * root certbot renew --quiet --post-hook 'docker compose -f ${APP_DIR}/docker-compose.yml exec nginx nginx -s reload'"
if ! grep -qF "certbot renew" /etc/cron.d/certbot-renew 2>/dev/null; then
    echo "${RENEW_CRON}" > /etc/cron.d/certbot-renew
    chmod 644 /etc/cron.d/certbot-renew
    log "Certbot renewal cron: daily at 03:00 & 15:00."
else
    info "Certbot renewal cron already configured."
fi

# Weekly Docker cleanup (Sunday 02:00)
CLEANUP_CRON="0 2 * * 0 root /opt/app/scripts/cleanup.sh >> /var/log/docker-cleanup.log 2>&1"
if ! grep -qF "cleanup.sh" /etc/cron.d/docker-cleanup 2>/dev/null; then
    echo "${CLEANUP_CRON}" > /etc/cron.d/docker-cleanup
    chmod 644 /etc/cron.d/docker-cleanup
    log "Weekly cleanup cron: every Sunday at 02:00."
else
    info "Cleanup cron already configured."
fi

# ══ 10. Final summary ═════════════════════════════════════════════════════════
step "Step 10/10 — Summary"
source "${CREDS_FILE}"

echo ""
echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  SERVER SETUP COMPLETE${NC}"
echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Site:${NC}        https://${DOMAIN}"
echo -e "  ${BOLD}Logs:${NC}        https://${LOG_DOMAIN}"
echo ""
echo -e "  ${BOLD}╔═ Dozzle Monitor Credentials (SAVE THESE) ══════════╗${NC}"
echo -e "  ${BOLD}║${NC}  Username : ${GREEN}${DOZZLE_USERNAME}${NC}"
echo -e "  ${BOLD}║${NC}  Password : ${GREEN}${DOZZLE_PASSWORD}${NC}"
echo -e "  ${BOLD}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Next steps:"
echo "  ─────────────────────────────────────────────────────"
echo "  1. Ensure DNS A records point to $(curl -s https://checkip.amazonaws.com):"
echo "        ${DOMAIN}         → $(curl -s https://checkip.amazonaws.com)"
echo "        www.${DOMAIN}     → $(curl -s https://checkip.amazonaws.com)"
echo "        ${LOG_DOMAIN}     → $(curl -s https://checkip.amazonaws.com)"
echo ""
echo "  2. Copy deployment files to ${APP_DIR}/:"
echo "       scp -r nginx/ scripts/ docker-compose.yml root@$(curl -s https://checkip.amazonaws.com):${APP_DIR}/"
echo ""
echo "  3. Create .env from .env.example:"
echo "       cp .env.example .env && nano .env"
echo ""
echo "  4. Launch the stack:"
echo "       cd ${APP_DIR} && docker compose pull && docker compose up -d"
echo ""
echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"

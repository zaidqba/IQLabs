#!/usr/bin/env bash
# ─── IQ-RAD Server Setup Script ───────────────────────────────────────────────
# Run this ONCE on iqlabsserver1 (100.116.165.41) as root or sudo user.
# Sets up Docker, clones the repo, applies the database schema, and starts
# the IQ-RAD containers.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/zaidqba/IQLabs/claude/build-iq-rad-system-TV4BK/deploy/setup-server.sh | bash
# OR copy this file to the server and run:
#   chmod +x setup-server.sh && sudo bash setup-server.sh

set -euo pipefail

REPO_URL="https://github.com/zaidqba/IQLabs.git"
BRANCH="claude/build-iq-rad-system-TV4BK"
INSTALL_DIR="/opt/iq-rad"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

log()  { echo -e "${GREEN}[IQ-RAD]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
die()  { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── 1. OS check ────────────────────────────────────────────────────────────────
log "Checking OS..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    log "Detected: $NAME $VERSION_ID"
else
    warn "Could not detect OS — assuming Debian/Ubuntu compatible"
fi

# ── 2. Install Docker if missing ───────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    log "Installing Docker..."
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg lsb-release
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable --now docker
    log "Docker installed: $(docker --version)"
else
    log "Docker already installed: $(docker --version)"
fi

# ── 3. Clone or update repo ────────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    log "Updating existing repo at $INSTALL_DIR..."
    git -C "$INSTALL_DIR" fetch origin
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git -C "$INSTALL_DIR" pull origin "$BRANCH"
else
    log "Cloning repo to $INSTALL_DIR..."
    git clone -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR/deploy"

# ── 4. Create .env if missing ──────────────────────────────────────────────────
if [ ! -f .env ]; then
    log "Creating .env from template..."
    cp .env.production .env

    # Auto-generate secrets
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || \
                 openssl rand -hex 32)
    HMAC_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || \
                  openssl rand -hex 32)

    sed -i "s|CHANGE_ME_TO_RANDOM_64_CHAR_STRING_BEFORE_LAUNCH_111111111111111|$JWT_SECRET|" .env
    sed -i "s|CHANGE_ME_TO_RANDOM_64_CHAR_STRING_BEFORE_LAUNCH_222222222222222|$HMAC_SECRET|" .env

    warn "IMPORTANT: Edit $INSTALL_DIR/deploy/.env and set:"
    warn "  DATABASE_URL — point to Ionetix3/SQLEXPRESS with correct credentials"
    warn "  ROTEM_STACK_HOST / ROTEM_DPU3_HOST — verify device IPs"
    echo ""
    echo "Press ENTER when .env is configured, or Ctrl+C to exit and edit manually."
    read -r
fi

# ── 5. Apply database schema ───────────────────────────────────────────────────
log "Applying database schema to Ionetix3/SQLEXPRESS..."
log "Checking if sqlcmd is available..."
if command -v sqlcmd &>/dev/null || command -v /opt/mssql-tools18/bin/sqlcmd &>/dev/null; then
    SQLCMD=$(command -v sqlcmd 2>/dev/null || echo "/opt/mssql-tools18/bin/sqlcmd")
    source .env
    DB_SERVER=$(echo "$DATABASE_URL" | grep -oP '(?<=@)[^/]+')
    DB_USER=$(echo "$DATABASE_URL" | grep -oP '(?<=//)[^:]+')
    DB_PASS=$(echo "$DATABASE_URL" | grep -oP '(?<=:)[^@]+(?=@)')

    log "Creating IQ_RAD database..."
    $SQLCMD -S "$DB_SERVER" -U "$DB_USER" -P "$DB_PASS" -C \
        -Q "IF NOT EXISTS (SELECT name FROM sys.databases WHERE name='IQ_RAD') CREATE DATABASE IQ_RAD" \
        2>/dev/null || warn "Could not create DB — may already exist or check credentials"

    log "Running schema scripts..."
    for f in "$INSTALL_DIR"/database/schema/0*.sql; do
        log "  Running $(basename $f)..."
        $SQLCMD -S "$DB_SERVER" -U "$DB_USER" -P "$DB_PASS" -C -d IQ_RAD -i "$f" 2>&1 || \
            warn "  $(basename $f) had errors (may be safe if objects already exist)"
    done
else
    warn "sqlcmd not found — skipping automatic schema setup."
    warn "Run the SQL scripts manually from database/schema/ against Ionetix3/SQLEXPRESS."
fi

# ── 6. Build and start containers ──────────────────────────────────────────────
log "Building and starting IQ-RAD containers..."
docker compose -f "$INSTALL_DIR/deploy/docker-compose.prod.yml" \
    --env-file "$INSTALL_DIR/deploy/.env" \
    up --build -d

log "Waiting for backend health check..."
sleep 10
docker compose -f "$INSTALL_DIR/deploy/docker-compose.prod.yml" ps

# ── 7. Done ────────────────────────────────────────────────────────────────────
echo ""
log "═══════════════════════════════════════════════════════"
log " IQ-RAD is running at: http://100.116.165.41"
log " API health:           http://100.116.165.41/health"
log " Logs: docker compose -f $INSTALL_DIR/deploy/docker-compose.prod.yml logs -f"
log "═══════════════════════════════════════════════════════"

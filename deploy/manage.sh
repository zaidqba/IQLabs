#!/usr/bin/env bash
# ─── IQ-RAD Management Script ─────────────────────────────────────────────────
# Usage: bash manage.sh [start|stop|restart|status|logs|update|backup]
set -euo pipefail
cd "$(dirname "$0")"

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env"

case "${1:-status}" in
  start)
    echo "Starting IQ-RAD..."
    $COMPOSE up -d
    ;;
  stop)
    echo "Stopping IQ-RAD..."
    $COMPOSE down
    ;;
  restart)
    echo "Restarting IQ-RAD..."
    $COMPOSE restart
    ;;
  rebuild)
    echo "Rebuilding and restarting IQ-RAD..."
    $COMPOSE up --build -d
    ;;
  status)
    $COMPOSE ps
    echo ""
    echo "Health: $(curl -sf http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo 'backend not responding')"
    ;;
  logs)
    $COMPOSE logs -f --tail=100 "${2:-}"
    ;;
  update)
    echo "Pulling latest code..."
    git -C /opt/iq-rad pull origin claude/build-iq-rad-system-TV4BK
    echo "Rebuilding containers..."
    $COMPOSE up --build -d
    ;;
  backup)
    STAMP=$(date +%Y%m%d_%H%M%S)
    echo "Backing up reports volume..."
    docker run --rm \
      -v iq-rad_reports_data:/data \
      -v "$(pwd)/backups":/backup \
      alpine tar czf "/backup/reports_$STAMP.tar.gz" /data
    echo "Backup saved: backups/reports_$STAMP.tar.gz"
    ;;
  *)
    echo "Usage: $0 [start|stop|restart|rebuild|status|logs|update|backup]"
    exit 1
    ;;
esac

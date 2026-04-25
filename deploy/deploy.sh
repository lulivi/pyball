#!/bin/sh
set -eu

VERSION="${VERSION:?VERSION env var is required}"
APP_DIR="${APP_DIR:-$HOME/apps/pyball}"

ENV_FILE="$APP_DIR/tg_notify.env"
[ -f "$ENV_FILE" ] && . "$ENV_FILE"

notify() {
    [ -z "${TELEGRAM_TOKEN:-}" ] && return 0
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
        --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
        --data-urlencode "text=$1" > /dev/null || true
}

notify "Desplegando pyball v${VERSION}..."

cd "$APP_DIR"
sed -i "s/^TAG=.*/TAG=${VERSION}/" .env
docker compose pull
docker compose up -d

sleep 5
if docker compose ps | grep -q " Up "; then
    notify "pyball v${VERSION} desplegado correctamente"
else
    notify "ERROR: pyball v${VERSION} no arranco correctamente"
    exit 1
fi

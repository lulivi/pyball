#!/bin/sh
set -eu

VERSION="${VERSION:?VERSION env var is required}"
SCAPED_VERSION=" \[\`v${VERSION}\`\] "
APP_DIR="${APP_DIR:?APP_DIR env var is required}"

ENV_FILE="$HOME/envs/tg_notify.env"
[ -f "$ENV_FILE" ] && . "$ENV_FILE"

notify() {
    [ -z "${TELEGRAM_TOKEN:-}" ] && return 0
    curl --silent --request POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
        --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
        --data-urlencode 'parse_mode=MarkdownV2' \
        --data-urlencode "text=$1" 1>/dev/null | true
}

notify "Desplegando pyball ${SCAPED_VERSION} \.\.\."

cd "$APP_DIR"
sed -i "s/^TAG=.*/TAG=${VERSION}/" .env
docker compose pull
docker compose up -d

sleep 5
if docker compose ps | grep -qE "running| Up "; then
    notify "🚀 \#version ${SCAPED_VERSION} desplegada 🚀"
else
    notify "💥 ERROR ${SCAPED_VERSION} no arrancó correctamente 💥"
    exit 1
fi

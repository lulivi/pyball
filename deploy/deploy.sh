#!/bin/sh
set -eu

VERSION="${VERSION:?VERSION env var is required}"
APP_DIR="${APP_DIR:?APP_DIR env var is required}"
HEALTH_MODE="${HEALTH_MODE:-http}"
APP_NAME="$(basename "$APP_DIR")"
SCAPED_VERSION_STR=" \[\`${APP_NAME}:v${VERSION}\`\] "

ENV_FILE="$HOME/pyball/cfg/notify/tg_notify.env"
[ -f "$ENV_FILE" ] && . "$ENV_FILE"

notify() {
    [ -z "${TELEGRAM_TOKEN:-}" ] && return 0
    set -- --data-urlencode "chat_id=${TELEGRAM_CHAT_ID:-}" \
           --data-urlencode 'parse_mode=MarkdownV2' \
           --data-urlencode "text=$1"
    if [ -n "${TELEGRAM_MESSAGE_THREAD_ID:-}" ]; then
        set -- "$@" --data-urlencode "message_thread_id=${TELEGRAM_MESSAGE_THREAD_ID}"
    fi
    curl --silent --request POST \
        "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
        "$@" 1>/dev/null | true
}

health_http() {
    port="$(sed -n 's/^PORT=//p' .env)"
    [ -z "$port" ] && return 1
    for _ in $(seq 1 12); do
        if curl --fail --silent --show-error "http://127.0.0.1:${port}/" >/dev/null 2>&1; then
            return 0
        fi
        sleep 5
    done
    return 1
}

health_caddy() {
    docker compose exec -T caddy caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1 \
        && docker compose ps | grep -qE "running| Up "
}

rollback() {
    [ -z "$PREVIOUS_TAG" ] && return 0
    sed -i "s/^TAG=.*/TAG=${PREVIOUS_TAG}/" .env
    docker compose up -d || true
}

notify "Desplegando pyball ${SCAPED_VERSION_STR} \.\.\."

cd "$APP_DIR"
PREVIOUS_TAG="$(sed -n 's/^TAG=//p' .env)"
sed -i "s/^TAG=.*/TAG=${VERSION}/" .env
docker compose pull
docker compose up -d

if [ "$HEALTH_MODE" = "caddy" ]; then
    health_check=health_caddy
else
    health_check=health_http
fi

if $health_check; then
    notify "🚀 \#version ${SCAPED_VERSION_STR} desplegada 🚀"
else
    notify "💥 ERROR ${SCAPED_VERSION_STR} no pasó el health check, revirtiendo a v${PREVIOUS_TAG} 💥"
    rollback
    exit 1
fi

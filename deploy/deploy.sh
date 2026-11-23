#!/bin/sh
# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Deploys every directory given as an argument: writes $COMPOSE into it as
# compose.yaml, moves its .env TAG to $VERSION, starts it and health-checks it.
# A directory that fails is rolled back on its own, the rest still deploy, and
# the script exits non-zero at the end.
#
# Runs over SSH with deploy_input.sh's output on stdin, which sets COMPOSE and
# the optional DEPLOY_NOTIFY_TOKEN, DEPLOY_NOTIFY_CHAT_ID and
# DEPLOY_NOTIFY_THREAD_ID before this script.
set -eu

main() {
    VERSION="${VERSION:?VERSION env var is required}"
    : "${COMPOSE:?COMPOSE must be set before this script}"
    [ $# -gt 0 ] || { echo "Usage: sh -s -- DIR..." >&2; exit 1; }
    failed=0
    for dir in "$@"; do
        (deploy "${dir%/}") || failed=1
    done
    exit "$failed"
}

# Runs in a subshell from an `||` list, where `set -e` is off: every step
# checks its own result.
deploy() {
    label=" \[\`$(basename "$1"):v${VERSION}\`\] "
    notify "Desplegando pyball ${label} \.\.\."
    cd "$1" || return 1
    previous_tag="$(sed -n 's/^TAG=//p' .env)"
    if printf '%s\n' "$COMPOSE" > compose.yaml \
        && sed -i "s/^TAG=.*/TAG=${VERSION}/" .env \
        && docker compose pull \
        && docker compose up -d --remove-orphans \
        && health; then
        notify "🚀 \#version ${label} desplegada 🚀"
        return 0
    fi
    notify "💥 ERROR ${label} no pasó el health check, revirtiendo a v${previous_tag} 💥"
    rollback "$previous_tag"
    return 1
}

notify() {
    [ -z "${DEPLOY_NOTIFY_TOKEN:-}" ] && return 0
    set -- --data-urlencode "chat_id=${DEPLOY_NOTIFY_CHAT_ID:-}" \
           --data-urlencode 'parse_mode=MarkdownV2' \
           --data-urlencode "text=$1"
    if [ -n "${DEPLOY_NOTIFY_THREAD_ID:-}" ]; then
        set -- "$@" --data-urlencode "message_thread_id=${DEPLOY_NOTIFY_THREAD_ID}"
    fi
    curl --silent --request POST \
        "https://api.telegram.org/bot${DEPLOY_NOTIFY_TOKEN}/sendMessage" \
        "$@" >/dev/null || true
}

health() {
    if [ "${HEALTH_MODE:-http}" = "caddy" ]; then health_caddy; else health_http; fi
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
    [ -z "$1" ] && return 0
    sed -i "s/^TAG=.*/TAG=$1/" .env
    docker compose up -d --remove-orphans || true
}

# Called last, so no command can read the rest of this script from stdin.
main "$@"

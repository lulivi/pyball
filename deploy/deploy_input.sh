#!/bin/sh
# Prints deploy.sh's stdin: shell assignments for COMPOSE (the contents of the
# compose file given as $1) and the DEPLOY_NOTIFY_* variables, then deploy.sh.
# Secrets travel through the SSH session's stdin, never on a command line.
set -eu

COMPOSE_FILE="${1:?Usage: $0 COMPOSE_FILE}"

main() {
    printf 'DEPLOY_NOTIFY_TOKEN=%s\n' "$(quote "${DEPLOY_NOTIFY_TOKEN:-}")"
    printf 'DEPLOY_NOTIFY_CHAT_ID=%s\n' "$(quote "${DEPLOY_NOTIFY_CHAT_ID:-}")"
    printf 'DEPLOY_NOTIFY_THREAD_ID=%s\n' "$(quote "${DEPLOY_NOTIFY_THREAD_ID:-}")"
    printf 'COMPOSE=%s\n' "$(quote "$(cat "$COMPOSE_FILE")")"
    cat "$(dirname "$0")/deploy.sh"
}

quote() {
    printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

main

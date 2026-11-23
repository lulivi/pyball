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

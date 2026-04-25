#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

"${SCRIPT_DIR}/docker_build.sh"

VERSION="$("${SCRIPT_DIR}/get_app_version.sh")"
echo "-- Running pyball ${VERSION} locally..."
TAG="${VERSION}" docker compose -f "${ROOT_DIR}/compose.yaml" run --remove-orphans bot

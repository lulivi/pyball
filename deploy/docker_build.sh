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

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GET_VERSION_SCRIPT="${SCRIPT_DIR}/get_app_version.sh"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

IMAGE="${PYBALL_DOCKER_IMAGE:-lulivi/pyball}"
PUSH=false
RELEASE=false

usage() {
    echo "Usage: $0 [--push] [--release] [--image NAME]" >&2
    exit 1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --push) PUSH=true; shift ;;
        --release) RELEASE=true; shift ;;
        --image) IMAGE="$2"; shift 2 ;;
        *) usage ;;
    esac
done

if $RELEASE && ! $PUSH; then
    echo "Error: --release requires --push" >&2
    exit 1
fi

if [ ! -f "$GET_VERSION_SCRIPT" ]; then
    echo "Error: could not find '${GET_VERSION_SCRIPT}' script" >&2
    exit 1
fi

VERSION="$($GET_VERSION_SCRIPT)"
IMAGE_TAG="${IMAGE}:${VERSION}"
IMAGE_LATEST="${IMAGE}:latest"

echo "Building ${IMAGE_TAG}..."
docker build \
    --build-arg VERSION="${VERSION}" \
    --target pyball \
    -t "${IMAGE_TAG}" \
    -f "${ROOT_DIR}/docker/Dockerfile" \
    "${ROOT_DIR}"

if $PUSH; then
    docker push "${IMAGE_TAG}"
    if $RELEASE; then
        docker tag "${IMAGE_TAG}" "${IMAGE_LATEST}"
        docker push "${IMAGE_LATEST}"
    fi
fi

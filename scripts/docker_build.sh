#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

IMAGE="${PYBALL_DOCKER_IMAGE:-lulivi/pyball}"
PUSH=false
RELEASE=false

usage() {
    echo "Usage: $0 [--push] [--release] [--image NAME]" >&2
    exit 1
}

while [[ $# -gt 0 ]]; do
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

get_version() {
    local tag
    if ! tag=$(git describe --tags --abbrev=0 2>/dev/null); then
        echo "Warning: no git tags found, using 0.0.1.dev0" >&2
        echo "0.0.1.dev0"
        return
    fi
    local tag_clean="${tag#v}"
    local commits
    commits=$(git rev-list "${tag}..HEAD" --count)
    if [ "$commits" -eq 0 ]; then
        echo "$tag_clean"
    else
        local patch
        patch=$(echo "$tag_clean" | cut -d. -f3)
        local prefix
        prefix=$(echo "$tag_clean" | cut -d. -f1-2)
        echo "${prefix}.$((patch + 1)).dev${commits}"
    fi
}

VERSION="$(get_version)"
IMAGE_TAG="${IMAGE}:${VERSION}"
IMAGE_LATEST="${IMAGE}:latest"

echo "Building ${IMAGE_TAG}..."
docker build \
    --build-arg VERSION="${VERSION}" \
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

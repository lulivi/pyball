# Docker Release Improvement Design

**Date:** 2026-04-18

## Goal

Eliminate the need for `uv` and `hatch` installed locally to build the Docker image, and replace
the Python build script with a bash script that computes the image version directly from git tags.

## Approach

**Multi-stage Dockerfile + bash build script with git-based versioning.**

The bash script computes the version from `git describe`, passes it to `docker build` as
`--build-arg VERSION`, and the builder stage exposes it as `HATCH_VCS_PRETEND_VERSION` so `uv build`
picks it up without needing git history in the build context.

## Version Scheme

Follows PEP 440 dev release convention:

- On an exact tag (`v4.0.0`, 0 commits): `4.0.0`
- Past a tag (7 commits since `v4.0.0`): `4.0.1.dev7` (patch bumped, `.devN` appended)
- No tags found: `0.0.1.dev0`

This matches the behavior of `hatch-vcs`/`setuptools_scm` and makes it explicit that commits
after a release are development towards the *next* version.

## Components

### 1. `scripts/docker_build.sh` (replaces `scripts/docker_build.py`)

Interface identical to the current Python script:

```
./scripts/docker_build.sh [--push] [--release] [--image NAME]
```

- `--push`: push the versioned image after building
- `--release`: also tag and push `:latest` (requires `--push`)
- `--image`: image name, defaults to `PYBALL_DOCKER_IMAGE` env var or `lulivi/pyball`

**Flow:**
1. Parse arguments
2. `get_version()` → compute version from git tags
3. `docker build --build-arg VERSION=<version> -t <image>:<version> -f docker/Dockerfile .`
4. If `--push`: `docker push <image>:<version>`
5. If `--push --release`: `docker tag <image>:<version> <image>:latest && docker push <image>:latest`

**`get_version()` logic:**
```bash
get_version() {
    local tag
    tag=$(git describe --tags --abbrev=0 2>/dev/null) || { echo "0.0.1.dev0"; return; }
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
```

### 2. `docker/Dockerfile` (multi-stage)

**Builder stage:**
- Base: `python:3.12.13-slim-trixie`
- Installs `uv` via pip (`hatchling` and `hatch-vcs` are pulled automatically by `uv build` from `[build-system] requires`)
- Receives `ARG VERSION`, sets `HATCH_VCS_PRETEND_VERSION=${VERSION}`
- Copies full source, runs `uv build --wheel --out-dir /dist`

**Final stage:**
- Base: `python:3.12.13-slim-trixie` (same as now)
- Sets up locale and venv (same as now)
- Copies `*.whl` from builder stage via `COPY --from=builder /dist/*.whl .`
- Installs wheel, runs `playwright install chromium --with-deps`

### 3. `scripts/docker_build.py` — deleted

No longer needed.

### 4. `noxfile.py` — updated

`dbuild` and `dpublish` sessions currently call `python scripts/docker_build.py`. Update them to
call `bash scripts/docker_build.sh` (and `bash scripts/docker_build.sh --push` respectively) via
`session.run_always("bash", ..., external=True)`.

### 5. `Makefile` — no change needed

`make build` → `nox -e dbuild` and `make publish` → `nox -e dpublish` remain valid.

## Error Handling

- Script exits with non-zero if any command fails (`set -euo pipefail`)
- `--release` without `--push` prints an error and exits 1
- Missing git tags fall back to `0.0.1.dev0` with a warning to stderr

## Testing

No automated tests for the shell script. Verify manually:
- On a clean tag: version is `X.Y.Z`
- With commits since tag: version is `X.Y.(Z+1).devN`
- `--release` without `--push` errors out
- Built image runs `pyball` entrypoint correctly

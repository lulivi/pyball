# Docker Release Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Python Docker build script with a bash script that computes the image version from git tags, and convert the Dockerfile to a multi-stage build so `uv` and `hatch` are no longer required locally.

**Architecture:** A bash script (`scripts/docker_build.sh`) computes the version via `git describe`, passes it as `--build-arg VERSION` to Docker, and the new multi-stage Dockerfile uses it as `HATCH_VCS_PRETEND_VERSION` so `uv build` can build the wheel without git history in the build context.

**Tech Stack:** bash, Docker multi-stage builds, `uv build`, `hatch-vcs` (`HATCH_VCS_PRETEND_VERSION`), nox.

---

## File Map

| Action | Path |
|--------|------|
| Create | `scripts/docker_build.sh` |
| Create | `.dockerignore` |
| Modify | `docker/Dockerfile` |
| Modify | `noxfile.py` (lines 96–114) |
| Delete | `scripts/docker_build.py` |

---

### Task 1: Create `scripts/docker_build.sh`

**Files:**
- Create: `scripts/docker_build.sh`

- [ ] **Step 1: Create the script**

```bash
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
```

Save to `scripts/docker_build.sh`.

- [ ] **Step 2: Make it executable**

```bash
chmod +x scripts/docker_build.sh
```

- [ ] **Step 3: Verify `get_version()` output manually**

Current branch has commits after `v4.0.0`. Run:

```bash
bash -c '
set -euo pipefail
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
get_version
'
```

Expected output: `4.0.1.devN` (where N is the number of commits since `v4.0.0`).

- [ ] **Step 4: Verify `--release` without `--push` exits 1**

```bash
bash scripts/docker_build.sh --release; echo "exit: $?"
```

Expected: prints `Error: --release requires --push` and `exit: 1`.

- [ ] **Step 5: Commit**

```bash
git add scripts/docker_build.sh
git commit -m "feat(scripts): add bash docker build script with git-based versioning"
```

---

### Task 2: Create `.dockerignore`

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: Create `.dockerignore`**

```
.git
.nox
.venv
dist
__pycache__
*.pyc
*.egg-info
config.toml
test_data
docs
```

This prevents `.git` (unnecessary since version is passed as build-arg), local venvs, old dist artifacts, and sensitive config from entering the build context.

- [ ] **Step 2: Commit**

```bash
git add .dockerignore
git commit -m "chore: add .dockerignore for multi-stage docker build"
```

---

### Task 3: Convert `docker/Dockerfile` to multi-stage

**Files:**
- Modify: `docker/Dockerfile`

- [ ] **Step 1: Replace the Dockerfile content**

```dockerfile
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

FROM python:3.12.13-slim-trixie AS builder

ARG VERSION
ENV HATCH_VCS_PRETEND_VERSION=${VERSION}

RUN pip install uv --no-cache-dir

WORKDIR /src
COPY . .
RUN uv build --wheel --out-dir /dist


FROM python:3.12.13-slim-trixie

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:${PATH}

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y locales \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 \
    && localedef -i es_ES -c -f UTF-8 -A /usr/share/locale/locale.alias es_ES.UTF-8 \
    && /usr/local/bin/python3 -m venv $VIRTUAL_ENV \
    && $VIRTUAL_ENV/bin/python3 -m pip install -U pip wheel

WORKDIR /builder
COPY --from=builder /dist/*.whl .

RUN $VIRTUAL_ENV/bin/python3 -m pip install --no-cache *.whl \
    && rm -rf /builder \
    && playwright install chromium --with-deps

WORKDIR /pyball

ENTRYPOINT ["pyball"]
```

- [ ] **Step 2: Do a test build to confirm it works end-to-end**

```bash
VERSION="$(bash -c '
get_version() {
    local tag
    if ! tag=$(git describe --tags --abbrev=0 2>/dev/null); then
        echo "0.0.1.dev0"; return
    fi
    local tag_clean="${tag#v}"
    local commits
    commits=$(git rev-list "${tag}..HEAD" --count)
    if [ "$commits" -eq 0 ]; then
        echo "$tag_clean"
    else
        local patch; patch=$(echo "$tag_clean" | cut -d. -f3)
        local prefix; prefix=$(echo "$tag_clean" | cut -d. -f1-2)
        echo "${prefix}.$((patch + 1)).dev${commits}"
    fi
}
get_version
')"
docker build --build-arg VERSION="${VERSION}" -t "lulivi/pyball:${VERSION}" -f docker/Dockerfile .
```

Expected: build completes successfully with both stages. The wheel version inside the image should match `VERSION`.

- [ ] **Step 3: Verify the image exists and entrypoint is reachable**

```bash
docker images lulivi/pyball
```

Confirm the image with the correct version tag is listed. Then:

```bash
docker run --rm lulivi/pyball:$(docker images lulivi/pyball --format "{{.Tag}}" | head -1) --help 2>&1 || true
```

Expected: `pyball` CLI help output or a known startup error (e.g. missing `config.toml`) — not "executable not found".

- [ ] **Step 4: Commit**

```bash
git add docker/Dockerfile
git commit -m "feat(docker): convert to multi-stage build, wheel built inside builder stage"
```

---

### Task 4: Update `noxfile.py` and delete `scripts/docker_build.py`

**Files:**
- Modify: `noxfile.py` (lines 96–114)
- Delete: `scripts/docker_build.py`

- [ ] **Step 1: Update the `dbuild` and `dpublish` nox sessions**

Replace lines 96–114 in `noxfile.py`:

```python
@nox.session(name="dbuild", venv_backend=None)
def docker_build(session: nox.Session) -> None:
    """Build the Docker image."""
    session.run_always(
        "bash",
        str(ROOT_DIRECTORY / "scripts" / "docker_build.sh"),
        *session.posargs,
        external=True,
    )


@nox.session(name="dpublish", venv_backend=None)
def docker_publish(session: nox.Session) -> None:
    """Publish the Docker image."""
    session.run_always(
        "bash",
        str(ROOT_DIRECTORY / "scripts" / "docker_build.sh"),
        "--push",
        *session.posargs,
        external=True,
    )
```

`*session.posargs` lets callers pass `--release` or `--image` through nox, e.g. `nox -e dpublish -- --release`.

- [ ] **Step 2: Delete the old Python script**

```bash
git rm scripts/docker_build.py
```

- [ ] **Step 3: Run `nox -e dbuild` to confirm the full chain works**

```bash
nox -e dbuild
```

Expected: nox calls `bash scripts/docker_build.sh`, which computes the version from git and runs `docker build`. No errors.

- [ ] **Step 4: Commit**

```bash
git add noxfile.py
git commit -m "chore(nox): update dbuild/dpublish sessions to call bash script"
```

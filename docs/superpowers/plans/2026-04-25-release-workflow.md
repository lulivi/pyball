# Release Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the release workflow by consolidating all release scripts into `deploy/`, creating a server-side deploy script with Telegram notifications, and rewriting `.gitlab-ci.yml` with clean publish and deploy stages.

**Architecture:** Two scripts in `deploy/`: `docker_build.sh` (CI-side, builds and pushes the Docker image) and `deploy.sh` (server-side, updates `TAG` in `.env`, pulls the new image, restarts the service, and sends a Telegram notification). The CI syncs `compose.yaml` via `scp` then pipes `deploy.sh` to the server via SSH stdin. The server holds `tg_notify.env` with Telegram credentials — never committed to the repo.

**Tech Stack:** POSIX sh, Docker, Docker Compose v2, GitLab CI, Telegram Bot API (`curl`)

---

## File Map

| Action | File |
|--------|------|
| Modify (commit staged + unstaged) | `docker/Dockerfile` |
| Move from `scripts/` + fix | `deploy/docker_build.sh` |
| Replace | `compose.yaml` |
| Create | `deploy/deploy.sh` |
| Rewrite | `.gitlab-ci.yml` |
| Modify | `.gitignore` |

---

### Task 1: Commit existing Dockerfile improvements

The Dockerfile already has two sets of uncommitted changes: non-root user (staged) and copyright header (unstaged). Stage both and commit together.

**Files:**
- Modify: `docker/Dockerfile`

- [ ] **Step 1: Stage the unstaged Dockerfile changes**

```bash
git add docker/Dockerfile
```

- [ ] **Step 2: Verify the full diff looks correct**

```bash
git diff --cached docker/Dockerfile
```

Expected: diff shows both the copyright header at the top AND the non-root user additions (`groupadd`, `useradd`, `chown`, `USER pyballuser`).

- [ ] **Step 3: Commit**

```bash
git commit -m "docker: add non-root user and copyright header"
```

---

### Task 2: Move `docker_build.sh` to `deploy/` and fix the push bug

`scripts/docker_build.sh` is the only tracked file in `scripts/`. Move it to `deploy/`, fix the `echo docker push` bug that suppresses the actual image push, and discard the now-stale staged version.

**Files:**
- Move: `scripts/docker_build.sh` → `deploy/docker_build.sh`

- [ ] **Step 1: Unstage the current staged version and discard the working tree change**

```bash
git restore --staged scripts/docker_build.sh
git restore scripts/docker_build.sh
```

- [ ] **Step 2: Create `deploy/docker_build.sh` with the corrected content**

Write `deploy/docker_build.sh` with this exact content:

```sh
#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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

get_version() {
    tag=""
    if ! tag=$(git describe --tags --abbrev=0 2>/dev/null); then
        echo "Warning: no git tags found, using 0.0.1.dev0" >&2
        echo "0.0.1.dev0"
        return
    fi
    tag_clean="${tag#v}"
    commits=$(git rev-list "${tag}..HEAD" --count)

    if [ "$commits" -eq 0 ]; then
        echo "$tag_clean"
    else
        patch=$(echo "$tag_clean" | cut -d. -f3)
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

- [ ] **Step 3: Make executable and check syntax**

```bash
chmod +x deploy/docker_build.sh
sh -n deploy/docker_build.sh && echo "syntax OK"
```

Expected: `syntax OK`

- [ ] **Step 4: Remove the old tracked file and stage the new one**

```bash
git rm scripts/docker_build.sh
git add deploy/docker_build.sh
```

- [ ] **Step 5: Commit**

```bash
git commit -m "deploy: move docker_build.sh from scripts/ and fix docker push"
```

---

### Task 3: Update `compose.yaml`

The repo's `compose.yaml` is stale (wrong user format, mounts entire PWD, no ports, no restart). Replace it with the version running in production.

**Files:**
- Replace: `compose.yaml`

- [ ] **Step 1: Write the updated `compose.yaml`**

```yaml
services:
  bot:
    image: lulivi/pyball:${TAG:-latest}
    user: "${UID}:${GID}"
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - "./config.toml:/pyball/config.toml"
      - "./logs:/pyball/logs"
      - "./data:/pyball/data"
    restart: unless-stopped
```

- [ ] **Step 2: Validate YAML syntax**

```bash
python3 -c "import yaml; yaml.safe_load(open('compose.yaml')); print('YAML valid')"
```

If PyYAML is not available:

```bash
uv run python3 -c "import yaml; yaml.safe_load(open('compose.yaml')); print('YAML valid')"
```

Expected: `YAML valid`

- [ ] **Step 3: Commit**

```bash
git add compose.yaml
git commit -m "compose: sync with production version"
```

---

### Task 4: Create `deploy/deploy.sh`

The server-side deploy script. It is never installed on the server — the CI sends it via SSH stdin. It sources `tg_notify.env` if present (Telegram credentials), updates the `TAG` in `.env`, pulls the new image, restarts the service, and sends a Telegram notification.

**Files:**
- Create: `deploy/deploy.sh`

- [ ] **Step 1: Write `deploy/deploy.sh`**

```sh
#!/bin/sh
set -eu

VERSION="${VERSION:?VERSION env var is required}"
APP_DIR="${APP_DIR:-$HOME/apps/pyball}"

ENV_FILE="$APP_DIR/tg_notify.env"
[ -f "$ENV_FILE" ] && . "$ENV_FILE"

notify() {
    [ -z "${TELEGRAM_TOKEN:-}" ] && return 0
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
        --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
        --data-urlencode "text=$1" > /dev/null || true
}

notify "Desplegando pyball v${VERSION}..."

cd "$APP_DIR"
sed -i "s/^TAG=.*/TAG=${VERSION}/" .env
docker compose pull
docker compose up -d

sleep 5
if docker compose ps | grep -q " Up "; then
    notify "pyball v${VERSION} desplegado correctamente"
else
    notify "ERROR: pyball v${VERSION} no arranco correctamente"
    exit 1
fi
```

- [ ] **Step 2: Make executable and check syntax**

```bash
chmod +x deploy/deploy.sh
sh -n deploy/deploy.sh && echo "syntax OK"
```

Expected: `syntax OK`

- [ ] **Step 3: Commit**

```bash
git add deploy/deploy.sh
git commit -m "deploy: add server-side deploy script with Telegram notifications"
```

---

### Task 5: Rewrite `.gitlab-ci.yml`

The current file has staged and unstaged changes with bugs: wrong YAML key (`stage: deploy` instead of `deploy:`), empty SSH command, and `StrictHostKeyChecking no` instead of `ssh-keyscan`. Discard all current changes and write the final version from scratch.

**Files:**
- Rewrite: `.gitlab-ci.yml`

- [ ] **Step 1: Discard all current staged and unstaged changes**

```bash
git restore --staged .gitlab-ci.yml
git restore .gitlab-ci.yml
```

- [ ] **Step 2: Write the final `.gitlab-ci.yml`**

```yaml
stages:
  - publish
  - deploy

publish:
  stage: publish
  image: docker:latest
  services:
    - docker:dind
  variables:
    GIT_DEPTH: 0
  rules:
    - if: $CI_COMMIT_TAG
  before_script:
    - apk add --no-cache git
    - echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin
  script:
    - ./deploy/docker_build.sh --push --release

deploy:
  stage: deploy
  image: alpine:latest
  rules:
    - if: $CI_COMMIT_TAG
  needs:
    - publish
  before_script:
    - apk add --no-cache openssh-client
    - eval $(ssh-agent -s)
    - echo "$SSH_PRIVATE_KEY" | tr -d '\r' | ssh-add -
    - mkdir -p ~/.ssh
    - ssh-keyscan "$SERVER_IP" >> ~/.ssh/known_hosts
  script:
    - VERSION="${CI_COMMIT_TAG#v}"
    - scp compose.yaml "$SERVER_USER@$SERVER_IP:$SERVER_APP_DIR/compose.yaml"
    - ssh "$SERVER_USER@$SERVER_IP" "VERSION=$VERSION sh -s" < deploy/deploy.sh
```

- [ ] **Step 3: Validate YAML syntax**

```bash
python3 -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml')); print('YAML valid')"
```

Expected: `YAML valid`

- [ ] **Step 4: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "ci: rewrite release workflow with publish and deploy stages"
```

---

### Task 6: Update `.gitignore`

Add `tg_notify.env` so it can never be accidentally committed if someone copies it into the repo directory.

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Append to `.gitignore`**

Add the following line to the bottom of `.gitignore`, in the section near `config.toml`:

```
tg_notify.env
```

- [ ] **Step 2: Verify**

```bash
echo "tg_notify.env" > /tmp/tg_notify.env
cp /tmp/tg_notify.env tg_notify.env
git status
```

Expected: `tg_notify.env` does NOT appear in untracked files.

```bash
rm tg_notify.env
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "gitignore: add tg_notify.env"
```

---

### Task 7: Final verification

Confirm the branch is clean and all changes are committed.

- [ ] **Step 1: Check git status**

```bash
git status
```

Expected: `nothing to commit, working tree clean`

- [ ] **Step 2: Verify file layout**

```bash
ls deploy/
```

Expected: `deploy.sh  docker_build.sh`

- [ ] **Step 3: Confirm the old tracked file is gone**

```bash
git ls-files scripts/
```

Expected: empty output (no tracked files in `scripts/`)

- [ ] **Step 4: Syntax-check both scripts one final time**

```bash
sh -n deploy/docker_build.sh && echo "docker_build.sh OK"
sh -n deploy/deploy.sh && echo "deploy.sh OK"
```

Expected: both print `OK`. To do a full smoke-test of `docker_build.sh` (runs `docker build`, requires Docker): `./deploy/docker_build.sh`

- [ ] **Step 5: Check the branch log**

```bash
git log --oneline main..HEAD
```

Expected: 6 commits — one per task above.

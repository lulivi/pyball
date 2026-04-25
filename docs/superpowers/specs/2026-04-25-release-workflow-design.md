---
title: Release Workflow Design
date: 2026-04-25
status: approved
---

# Release Workflow

## Goal

Establish a clean, professional CI/CD release workflow for pyball using GitLab CI,
Docker Hub, and SSH-based deployment to a single VPS running Docker Compose.
All deployment logic lives in the repo and is versioned with the code.

## Principles

- `deploy/` contains all release-related scripts (build and deploy). Not app code.
- `compose.yaml` stays at the repo root (Docker Compose convention; tools expect it there).
- The CI does not run `docker compose` — that is the deploy script's responsibility.
- The server manages its own secrets (Telegram credentials); the CI only passes `VERSION`.
- The deploy script is self-contained and can be run manually on the server in emergencies.

## File Structure

```
compose.yaml           # Updated compose file, version-controlled, synced to server by CI
deploy/
  docker_build.sh      # Builds the Docker image and pushes it to Docker Hub (run by CI)
  deploy.sh            # Runs on the server via SSH stdin; updates image and restarts service
.gitlab-ci.yml         # Two-stage pipeline: publish → deploy
```

`scripts/` is removed. `docker_build.sh` moves to `deploy/`.

`tg_notify.env` lives only on the server at `$APP_DIR/tg_notify.env` and is never
committed to the repo. Add to `.gitignore`.

## `compose.yaml`

Replaces the stale repo version with the one currently running on the server:

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

Note: `user: "${UID}:${GID}"` overrides the Dockerfile's `USER pyballuser` so that
files written to the mounted volumes (`logs/`, `data/`) are owned by the server user.
This is intentional and correct for bind-mount setups.

## `deploy/docker_build.sh`

Moved from `scripts/docker_build.sh`. Two fixes needed:

1. Remove `echo` prefix from `docker push` and `docker tag` calls — they were added
   during debugging and suppress the actual push.
2. Keep the POSIX sh shebang and POSIX-compatible syntax (already done).

## `deploy/deploy.sh`

Runs on the server via `ssh "sh -s" < deploy/deploy.sh`. Steps:

1. Source `$APP_DIR/tg_notify.env` if present (Telegram credentials, never in repo).
2. Send "deploying..." Telegram notification.
3. `cd $APP_DIR`, update `TAG` in `.env`.
4. `docker compose pull` — fetches the new image.
5. `docker compose up -d` — recreates the container.
6. Wait 5 seconds, check container state via `docker compose ps`.
7. Send success or failure Telegram notification. Exit 1 on failure.

Telegram notification is best-effort (`|| true`) so a missing token or network
hiccup never blocks the deploy.

```sh
#!/bin/sh
set -eu

VERSION="${VERSION:?VERSION is required}"
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
if docker compose ps --format '{{.State}}' | grep -q "^running"; then
    notify "pyball v${VERSION} desplegado correctamente"
else
    notify "ERROR: pyball v${VERSION} no arranco correctamente"
    exit 1
fi
```

## `.gitlab-ci.yml`

Two stages. Each runs only on tag pushes (`$CI_COMMIT_TAG`). `deploy` depends on
`publish` via `needs`.

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

### Required GitLab CI variables

| Variable              | Description                              |
|-----------------------|------------------------------------------|
| `DOCKERHUB_USERNAME`  | Docker Hub username                      |
| `DOCKERHUB_TOKEN`     | Docker Hub access token                  |
| `SSH_PRIVATE_KEY`     | Private key for server SSH access        |
| `SERVER_IP`           | Server IP or hostname                    |
| `SERVER_USER`         | SSH user on the server                   |
| `SERVER_APP_DIR`      | Absolute path to the app dir on server   |

### Server-side files (not in repo)

| File                          | Contents                          |
|-------------------------------|-----------------------------------|
| `$APP_DIR/.env`               | `TAG=`, `UID=`, `GID=`            |
| `$APP_DIR/config.toml`        | App configuration                 |
| `$APP_DIR/tg_notify.env`      | `TELEGRAM_TOKEN=`, `TELEGRAM_CHAT_ID=` |

## What is NOT in scope

- Rollback: not automated. Manual recovery is `TAG=<prev> docker compose up -d`.
- Multiple environments (staging/prod): out of scope.
- Health endpoint: the deploy script checks container state, not HTTP health.

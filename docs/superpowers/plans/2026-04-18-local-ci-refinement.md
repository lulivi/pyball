# Local CI Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify local CI by consolidating dependency groups, fixing `nox -e test` argument passing, and extracting Docker build logic into a reusable Python script.

**Architecture:** Three independent changes: `pyproject.toml` dependency consolidation, `noxfile.py` session fixes, and a new `scripts/docker_build.py` that both nox and future GitLab CI can call.

**Tech Stack:** Python 3.12, Poetry, Nox, Docker, argparse, subprocess

---

## File Map

- Modify: `pyproject.toml` — merge `test` group into `dev`, remove `pylama`
- Modify: `noxfile.py` — fix `--only dev`, posargs, remove `build` session, thin wrappers for docker sessions
- Create: `scripts/docker_build.py` — standalone Docker build + publish script

---

### Task 1: Consolidate pyproject.toml dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Remove `pylama` from dev dependencies and merge test group into dev**

Open `pyproject.toml`. Replace the `[tool.poetry.group.dev.dependencies]` section and remove the entire `[tool.poetry.group.test]` block:

```toml
[tool.poetry.group.dev.dependencies]
black = "22.*"
isort = "5.*"
nox = "*"
mypy = "*"
pycodestyle = "*"
pydocstyle = "*"
pylint = "*"
coverage = "*"
pytest = "*"
pytest-asyncio = "*"
pytest-cov = "*"
pytest-emoji = "*"
pytest-timeout = "*"
Faker = "18.*"
freezegun = "*"
ddt = "^1.7.1"
```

Remove these sections entirely (they no longer exist):
```toml
[tool.poetry.group.test]
optional = true
[tool.poetry.group.test.dependencies]
coverage = "*"
pytest = "*"
pytest-asyncio = "*"
pytest-cov = "*"
pytest-emoji = "*"
pytest-timeout = "*"
```

- [ ] **Step 2: Verify poetry resolves the new group**

```bash
poetry install --only dev
```

Expected: installs without errors, all previous packages still available.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore(deps): merge test group into dev, remove unused pylama"
```

---

### Task 2: Create scripts/docker_build.py

**Files:**
- Create: `scripts/docker_build.py`

- [ ] **Step 1: Create the script**

```python
"""Build and optionally push the Docker image."""
import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()


def run(*args: str) -> str:
    """Run a command and return stripped stdout."""
    result = subprocess.run(list(args), check=True, capture_output=True, text=True)
    return result.stdout.strip()


def main() -> None:
    """Build the Docker image and optionally push it."""
    parser = argparse.ArgumentParser(description="Build and optionally push the Docker image.")
    parser.add_argument("--push", action="store_true", help="Push image after building.")
    parser.add_argument(
        "--image",
        default=os.environ.get("PYBALL_DOCKER_IMAGE", "lulivi/pyball"),
        help="Image name. Default: lulivi/pyball or PYBALL_DOCKER_IMAGE env var.",
    )
    args = parser.parse_args()

    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    run("poetry", "build", "-f", "wheel")

    version = run("poetry", "version", "--short")
    image_tag = f"{args.image}:{version}"
    image_latest = f"{args.image}:latest"

    run(
        "docker", "build",
        str(ROOT),
        "-t", image_tag,
        "-f", str(ROOT / "docker" / "Dockerfile"),
    )
    run("docker", "tag", image_tag, image_latest)

    if args.push:
        run("docker", "push", image_tag)
        run("docker", "push", image_latest)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the script is importable and help works**

```bash
poetry run python scripts/docker_build.py --help
```

Expected: prints usage with `--push` and `--image` options, no errors.

- [ ] **Step 3: Commit**

```bash
git add scripts/docker_build.py
git commit -m "feat(scripts): add docker_build.py to centralize Docker build and publish logic"
```

---

### Task 3: Update noxfile.py

**Files:**
- Modify: `noxfile.py`

- [ ] **Step 1: Update imports — remove unused `Tuple`**

Current line 23:
```python
from typing import Tuple
```

Remove it entirely. It was only used by the old `docker_build` return type.

- [ ] **Step 2: Fix `lint` session — replace `--with test` with `--only dev`**

Current:
```python
session.run("poetry", "install", "--with", "test", external=True)
```

Replace with:
```python
session.run("poetry", "install", "--only", "dev", external=True)
```

- [ ] **Step 3: Fix `test` session — replace `--with test` and fix posargs**

Replace the entire `test` session:

```python
@nox.session(python=["3.12"])
def test(session: nox.Session):
    """Test the code."""
    session.run("poetry", "install", "--only", "dev", external=True)

    target_dir = ROOT_DIRECTORY.joinpath("tests")
    cov_dir = ROOT_DIRECTORY.joinpath("pyball")
    cov_parameters = [
        "--cov-report=term-missing",
        f"--cov={cov_dir}",
    ]

    if session.posargs:
        session.run_always("pytest", *session.posargs)
    else:
        session.run_always("pytest", *cov_parameters, str(target_dir))
```

- [ ] **Step 4: Remove the `build` session entirely**

Delete the entire `build` function (lines ~103–107 in the original):

```python
@nox.session
def build(session: nox.Session) -> None:
    """Build the Python wheel."""
    session.run("rm", "-rf", str(ROOT_DIRECTORY.joinpath("dist")), external=True)
    session.run("poetry", "build", "-f", "wheel", external=True)
```

- [ ] **Step 5: Replace `docker_build` and `docker_publish` sessions with thin wrappers**

Replace both sessions with:

```python
@nox.session(name="dbuild", venv_backend=None)
def docker_build(session: nox.Session) -> None:
    """Build the Docker image."""
    session.run(
        "python",
        str(ROOT_DIRECTORY / "scripts" / "docker_build.py"),
        external=True,
    )


@nox.session(name="dpublish", venv_backend=None)
def docker_publish(session: nox.Session) -> None:
    """Publish the Docker image."""
    session.run(
        "python",
        str(ROOT_DIRECTORY / "scripts" / "docker_build.py"),
        "--push",
        external=True,
    )
```

- [ ] **Step 6: Verify lint session runs**

```bash
poetry run nox -e lint
```

Expected: all lint checks pass (or same failures as before — no new errors introduced).

- [ ] **Step 7: Verify test session runs without posargs**

```bash
poetry run nox -e test
```

Expected: full test suite runs with coverage report.

- [ ] **Step 8: Verify test session runs with posargs**

```bash
poetry run nox -e test -- tests/unit/domain/test_meetup.py -v
```

Expected: only `test_meetup.py` tests run, `-v` flag is respected (verbose output), no coverage report.

- [ ] **Step 9: Commit**

```bash
git add noxfile.py
git commit -m "fix(nox): use --only dev in all sessions, fix test posargs, extract docker sessions to script"
```

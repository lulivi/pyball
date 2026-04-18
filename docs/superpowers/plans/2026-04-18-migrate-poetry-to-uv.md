# Migrate Poetry to uv Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Poetry with uv as the package manager and build backend, preserving VCS-based dynamic versioning from git tags.

**Architecture:** `uv_build` replaces `poetry-core` + `poetry-dynamic-versioning`; `[project]` + `[dependency-groups]` (PEP 621/735) replace `[tool.poetry]` tables; nox sessions use `uv` as venv backend and `uv sync` for dep installation; `docker_build.py` calls `uv build`/`uv version` instead of Poetry.

**Tech Stack:** uv, uv_build (VCS versioning), PEP 621 `[project]`, PEP 735 `[dependency-groups]`, nox

---

## File Map

| File | Action |
|---|---|
| `pyproject.toml` | Full rewrite — build system, project metadata, dependency groups |
| `poetry.lock` | Delete |
| `uv.lock` | Generate via `uv sync` |
| `noxfile.py` | Change venv backend + replace install command in 3 sessions |
| `scripts/docker_build.py` | Replace 2 Poetry calls with uv equivalents |

---

### Task 1: Rewrite `pyproject.toml`

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace the entire file contents**

`pyproject.toml` must become exactly:

```toml
[build-system]
requires = ["uv_build"]
build-backend = "uv_build"

[tool.uv.build-backend]
version-source = "vcs"

[project]
name = "pyball"
dynamic = ["version"]
description = "Bot to play them all"
license = { text = "MIT" }
authors = [{ name = "Luis Liñán", email = "luislivilla@gmail.com" }]
readme = "README.md"
requires-python = ">=3.11,<4.0"
dependencies = [
    "python-telegram-bot>=22,<23",
    "pydantic>=2.0,<3",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "jinja2>=3.1,<4",
    "playwright>=1.44,<2",
]

[project.scripts]
pyball = "pyball.__main__:main"

[dependency-groups]
dev = [
    "black==22.*",
    "isort==5.*",
    "mypy",
    "pycodestyle",
    "pydocstyle",
    "pylint",
    "coverage",
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "pytest-emoji",
    "pytest-timeout",
    "faker==18.*",
    "freezegun",
    "ddt>=1.7.1,<2",
]

[tool.black]
line-length = 99
preview = true

[tool.isort]
profile = "black"
line_length = 99
lines_between_types = 1

[tool.mypy]
show_error_codes = true

[[tool.mypy.overrides]]
ignore_missing_imports = true
module = ["decouple", "event_bus", "playwright", "playwright.*"]

[tool.pydocstyle]
add-ignore = ["D105", "D107"]

[tool.pytest.ini_options]
asyncio_mode = "strict"
```

- [ ] **Step 2: Verify uv can parse the file**

```bash
uv sync --dry-run
```

Expected: no errors. If you see "no solution found", check constraint syntax in `[project.dependencies]` and `[dependency-groups]`.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: migrate pyproject.toml from Poetry to uv_build + PEP 621/735"
```

---

### Task 2: Replace `poetry.lock` with `uv.lock`

**Files:**
- Delete: `poetry.lock`
- Create: `uv.lock` (generated)

- [ ] **Step 1: Delete `poetry.lock`**

```bash
git rm poetry.lock
```

- [ ] **Step 2: Generate `uv.lock`**

```bash
uv sync --only-group dev
```

Expected: `uv.lock` is created in the project root, dev dependencies are installed into a `.venv`.

- [ ] **Step 3: Verify the lock file was created**

```bash
ls -la uv.lock
```

Expected: file exists and is non-empty.

- [ ] **Step 4: Commit**

```bash
git add uv.lock
git commit -m "chore: replace poetry.lock with uv.lock"
```

---

### Task 3: Update `noxfile.py`

**Files:**
- Modify: `noxfile.py`

- [ ] **Step 1: Change venv backend to uv**

In `noxfile.py`, replace:

```python
nox.options.default_venv_backend = "venv"
```

with:

```python
nox.options.default_venv_backend = "uv"
```

- [ ] **Step 2: Replace install commands in `lint` session**

Replace:

```python
    session.run("poetry", "install", "--only", "dev", external=True)
```

with:

```python
    session.run("uv", "sync", "--only-group", "dev", external=True)
```

(This is in the `lint` function body, the first line after the docstring.)

- [ ] **Step 3: Replace install commands in `test` session**

Replace (in the `test` function body):

```python
    session.run("poetry", "install", "--only", "dev", external=True)
```

with:

```python
    session.run("uv", "sync", "--only-group", "dev", external=True)
```

- [ ] **Step 4: Replace install commands in `format` session**

Replace (in the `format` function body):

```python
    session.run("poetry", "install", "--only", "dev", external=True)
```

with:

```python
    session.run("uv", "sync", "--only-group", "dev", external=True)
```

- [ ] **Step 5: Verify lint session runs**

```bash
nox -e lint
```

Expected: all lint checks pass (or fail only on code issues, not on install/setup errors).

- [ ] **Step 6: Verify test session runs**

```bash
nox -e test
```

Expected: test suite runs and passes.

- [ ] **Step 7: Commit**

```bash
git add noxfile.py
git commit -m "chore(nox): switch venv backend to uv, replace poetry install with uv sync"
```

---

### Task 4: Update `scripts/docker_build.py`

**Files:**
- Modify: `scripts/docker_build.py`

- [ ] **Step 1: Replace the build command**

In `docker_build.py`, replace:

```python
    run("poetry", "build", "-f", "wheel")
```

with:

```python
    run("uv", "build", "--wheel")
```

- [ ] **Step 2: Replace the version command**

Replace:

```python
    version = run("poetry", "version", "--short")
```

with:

```python
    version = run("hatch", "version")
```

Note: `hatch version` outputs just the version string (e.g. `"1.2.3"`), no extra parsing needed.

- [ ] **Step 3: Verify the script produces a wheel**

Run a dry build (no push, no Docker) to confirm uv builds the wheel and version is extracted:

```bash
python scripts/docker_build.py --help
```

Expected: help text shows without errors.

Then check uv build directly:

```bash
uv build --wheel
ls dist/
```

Expected: a `.whl` file like `pyball-1.2.3-py3-none-any.whl` is present.

Verify version extraction:

```bash
python -c "import subprocess; v = subprocess.run(['uv','version'], capture_output=True, text=True, check=True).stdout.strip(); print(repr(v)); print(v.split()[-1])"
```

Expected: last token is a semver-like version string (e.g. `"1.2.3"` or `"0.0.1.dev-5"`).

- [ ] **Step 4: Commit**

```bash
git add scripts/docker_build.py
git commit -m "chore(docker): replace poetry build/version calls with uv equivalents"
```

---

### Task 5: Final verification

**Files:** none (read-only verification)

- [ ] **Step 1: Run full lint suite**

```bash
nox -e lint
```

Expected: exits 0.

- [ ] **Step 2: Run full test suite**

```bash
nox -e test
```

Expected: all tests pass.

- [ ] **Step 3: Confirm Poetry is no longer referenced**

```bash
grep -r "poetry" pyproject.toml noxfile.py scripts/docker_build.py
```

Expected: no output (zero matches).

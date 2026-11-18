# Contributing to PyBall

🇬🇧 English | 🇪🇸 [Español](CONTRIBUTING.es.md)

How to build PyBall from source, run its checks, and get a change merged. For how the
code is organised, see [docs/development.md](docs/development.md).

## Setup

You need:

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) for dependency management
- [nox](https://nox.thea.codes/en/stable/) for automation

```bash
uv sync --all-extras            # install everything, including Telegram support and dev tools
```

## Run from source

```bash
uv run pyball --bootstrap       # first run only, generates config.toml
uv run pyball                   # /manage + /match, no Telegram; add /signup via
                                # enable_web_signup = true in config.toml

uv run pyball-telegram --bootstrap
uv run pyball-telegram          # /manage + /match + Telegram bot

make up                         # build the image from source and run it via Docker Compose
```

## Checks

CI runs the lint and test sessions on every pull request; run them before you push:

```bash
make test        # alias: make t — full test suite with coverage
make lint        # alias: make l — black, isort, pydocstyle, pycodestyle, mypy, pylint
make format      # alias: make f — format code (black + isort)

# A single test file, or any pytest flags
nox -e test -- tests/unit/domain/test_meetup.py -k test_name -v
```

Lint requires a line length of at most 99 characters and a pylint score of 10.00/10.

## Branches

Work for a GitHub issue goes on `<type>/gh-<n>[-<slug>]`, where `<type>` is `feature`,
`fix` or `docs` and `<n>` is the issue number (e.g. `feature/gh-4-github-conventions`).

## Commit messages

Commits follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
The optional scope names the area touched (e.g. `match`, `telegram`, `bootstrap`). The
last line of the body references the GitHub issue(s) the commit belongs to,
comma-separated when there are several:

```
type(scope): <description>

[optional body]

[optional footer(s)]
Refs: #<n>[, #<m>...]
```

The `release` job of the `ci` GitHub Actions workflow tags `main` from these types:

- `feat` → minor release
- `fix`, `perf` → patch release
- `BREAKING CHANGE:` footer or `!` after type/scope (e.g. `feat(match)!:`) → major release
- `build`, `chore`, `ci`, `docs`, `refactor`, `style`, `test` → no release

## Pull requests

Pull requests are squash-merged: the PR title becomes the commit subject on `main`, so it
must follow the commit format above, and the branch's commit messages become its body,
carrying their `Refs:` lines. The PR description includes `Closes #<n>` for each issue it
resolves, so GitHub closes them on merge.

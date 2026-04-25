# Local CI Refinement Design

## Summary

Simplify the local CI setup by consolidating dependency groups in `pyproject.toml`,
fixing argument passing in the `test` nox session, and extracting Docker build logic
into a reusable Python script that both nox and the future GitLab CI pipeline can call.

## pyproject.toml

The `test` optional group is removed and its dependencies are merged into `dev`. The
result is a single group for all development dependencies — linters, formatters, test
runners, and test helpers — installed with `poetry install --only dev`.

`pylama` is removed from `dev`. It is not referenced anywhere in `noxfile.py` and has
no effect on any session.

## noxfile.py

All sessions that call `poetry install` use `--only dev`. The previous `--with test`
in `lint` and `test` is no longer needed once the groups are consolidated.

The `test` session posargs handling changes so that any arguments after `--` are passed
directly to pytest:

```python
if session.posargs:
    session.run_always("pytest", *session.posargs)
else:
    session.run_always("pytest", *cov_parameters, str(target_dir))
```

This makes `nox -e test -- tests/unit/foo.py -v -k some_test` work correctly.

The `build` nox session (Python wheel) is removed as a public session. Wheel building
becomes an internal step inside `scripts/docker_build.py`.

`dbuild` and `dpublish` become thin wrappers:

```python
@nox.session(name="dbuild")
def docker_build(session: nox.Session) -> None:
    session.run("python", "scripts/docker_build.py", external=True)

@nox.session(name="dpublish")
def docker_publish(session: nox.Session) -> None:
    session.run("python", "scripts/docker_build.py", "--push", external=True)
```

No return values from nox sessions.

## scripts/docker_build.py

New Python script that owns the full Docker build and publish flow:

1. Cleans `dist/`, builds the Python wheel via `poetry build -f wheel`
2. Reads the version via `poetry version`
3. Runs `docker build` targeting `docker/Dockerfile`
4. Tags the image as both `<name>:<version>` and `<name>:latest`
5. With `--push`: pushes both tags

The image name defaults to `lulivi/pyball` but can be overridden via `--image` argument
or the `PYBALL_DOCKER_IMAGE` environment variable. This allows the same script to be used
with the GitLab Container Registry (`registry.gitlab.com/...`) without modification.

Usage:
```
python scripts/docker_build.py                          # build only
python scripts/docker_build.py --push                   # build + push
python scripts/docker_build.py --image registry.gitlab.com/lulivi/pyball --push
```

## Makefile

No changes. `poetry run nox -e <session>` remains the entry point. Argument passing
issues are resolved at the noxfile level, not here.

## Dockerfile

No changes.

## Testing

No new tests. Changes are to tooling only — no production code is affected. Manual
verification: `nox -e test -- tests/unit/domain/test_meetup.py -v` should run correctly
passing all arguments through to pytest.

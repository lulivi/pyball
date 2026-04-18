# Copyright (c) 2023 Luis Liñán
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

"""Package testing and deploying tasks."""
from pathlib import Path

import nox

ROOT_DIRECTORY = Path(__file__).parent.resolve()

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["test", "lint"]
nox.options.stop_on_first_error = False
nox.options.error_on_missing_interpreters = False


@nox.session
def lint(session: nox.Session):
    """Lint the code."""
    session.run("uv", "sync", "--group", "dev", external=True)

    targets = (
        str(ROOT_DIRECTORY.joinpath("pyball")),
        str(ROOT_DIRECTORY.joinpath("tests")),
    )

    commands = [
        ("black", "--check", "--diff", *targets),
        ("isort", "--check", "--diff", *targets),
        ("pydocstyle", *targets),
        ("pycodestyle", *targets, "--max-line-length", "99"),
        ("mypy", *targets, "--enable-incomplete-feature=Unpack"),
        ("pylint", *targets),
    ]

    failed = False
    for cmd in commands:
        try:
            session.run_always(*cmd)
        except Exception:
            failed = True

    if failed:
        session.error("Linting failed: one or more checks returned errors.")


@nox.session(python=["3.12"])
def test(session: nox.Session):
    """Test the code."""
    session.run("uv", "sync", "--group", "dev", external=True)

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


@nox.session
def format(session: nox.Session):
    """Format the code."""
    session.run("uv", "sync", "--group", "dev", external=True)

    session.run_always(
        "black", ROOT_DIRECTORY.joinpath("pyball"), ROOT_DIRECTORY.joinpath("tests")
    )
    session.run_always(
        "isort", ROOT_DIRECTORY.joinpath("pyball"), ROOT_DIRECTORY.joinpath("tests")
    )


@nox.session(name="dbuild", venv_backend=None)
def docker_build(session: nox.Session) -> None:
    """Build the Docker image."""
    session.run_always(
        "python",
        str(ROOT_DIRECTORY / "scripts" / "docker_build.py"),
        external=True,
    )


@nox.session(name="dpublish", venv_backend=None)
def docker_publish(session: nox.Session) -> None:
    """Publish the Docker image."""
    session.run_always(
        "python",
        str(ROOT_DIRECTORY / "scripts" / "docker_build.py"),
        "--push",
        external=True,
    )

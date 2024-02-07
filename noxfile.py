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
import nox
from pathlib import Path

ROOT_DIRECTORY = Path(__file__).parent.resolve()

nox.options.default_venv_backend = "venv"
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["test", "lint"]
nox.options.stop_on_first_error = False
nox.options.error_on_missing_interpreters = False


@nox.session
def lint(session):
    """Lint the code."""
    session.run("poetry", "install", external=True)

    session.run(
        "black",
        "--check",
        "--diff",
        ROOT_DIRECTORY.joinpath("pyball"),
        ROOT_DIRECTORY.joinpath("tests"),
    )
    session.run(
        "isort",
        "--check",
        "--diff",
        ROOT_DIRECTORY.joinpath("pyball"),
        ROOT_DIRECTORY.joinpath("tests"),
    )
    session.run(
        "pydocstyle",
        ROOT_DIRECTORY.joinpath("pyball"),
        ROOT_DIRECTORY.joinpath("tests"),
        "--add-ignore",
        "D104,D105,D107",
    )
    session.run(
        "pycodestyle",
        ROOT_DIRECTORY.joinpath("pyball"),
        ROOT_DIRECTORY.joinpath("tests"),
        "--max-line-length",
        "99",
        "--ignore",
        "W605,W503",
    )
    session.run(
        "mypy",
        ROOT_DIRECTORY.joinpath("pyball"),
        ROOT_DIRECTORY.joinpath("tests"),
        "--enable-incomplete-feature=Unpack",
    )
    session.run("pylint", ROOT_DIRECTORY.joinpath("pyball"), ROOT_DIRECTORY.joinpath("tests"))


@nox.session(python=["3.8"])
def test(session):
    """Test the code."""
    session.run("poetry", "install", "--with", "test", external=True)

    target_dir = ROOT_DIRECTORY.joinpath("tests")
    cov_dir = ROOT_DIRECTORY.joinpath("pyball")
    cov_parameters = [
        "--cov-report=term-missing",
        f"--cov={cov_dir}",
    ]

    if session.posargs:
        target_dir = session.posargs[0]
        cov_parameters = []

    session.run(
        "pytest",
        "-vvv",
        *cov_parameters,
        target_dir,
    )


@nox.session()
def format(session):
    """Format the code."""
    session.run("poetry", "install", "--only", "dev", external=True)

    session.run("black", ROOT_DIRECTORY.joinpath("pyball"), ROOT_DIRECTORY.joinpath("tests"))
    session.run("isort", ROOT_DIRECTORY.joinpath("pyball"), ROOT_DIRECTORY.joinpath("tests"))

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
from typing import Tuple

import nox

ROOT_DIRECTORY = Path(__file__).parent.resolve()

nox.options.default_venv_backend = "venv"
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["test", "lint"]
nox.options.stop_on_first_error = False
nox.options.error_on_missing_interpreters = False


@nox.session
def lint(session: nox.Session):
    """Lint the code."""
    session.run("poetry", "install", "--with", "test", external=True)

    session.run_always(
        "black",
        "--check",
        "--diff",
        ROOT_DIRECTORY.joinpath("pyball"),
        ROOT_DIRECTORY.joinpath("tests"),
    )
    session.run_always(
        "isort",
        "--check",
        "--diff",
        ROOT_DIRECTORY.joinpath("pyball"),
        ROOT_DIRECTORY.joinpath("tests"),
    )
    session.run_always(
        "pydocstyle",
        ROOT_DIRECTORY.joinpath("pyball"),
        ROOT_DIRECTORY.joinpath("tests"),
        "--add-ignore",
        "D104,D105,D107",
    )
    session.run_always(
        "pycodestyle",
        ROOT_DIRECTORY.joinpath("pyball"),
        ROOT_DIRECTORY.joinpath("tests"),
        "--max-line-length",
        "99",
        "--ignore",
        "W605,W503",
    )
    session.run_always(
        "mypy",
        ROOT_DIRECTORY.joinpath("pyball"),
        ROOT_DIRECTORY.joinpath("tests"),
        "--enable-incomplete-feature=Unpack",
    )
    session.run_always(
        "pylint",
        ROOT_DIRECTORY.joinpath("pyball"),
        ROOT_DIRECTORY.joinpath("tests"),
        "--disable=C0114,C0115,C0116,C1803,R0801,R0903,R0911,R0912,R0914,R0915,W0107,W0201,W0511,W0611,W0612,W0613,W0706,W0707,W0718,W1514,W2301",
    )


@nox.session(python=["3.12"])
def test(session: nox.Session):
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

    session.run_always(
        "pytest",
        "-vvv",
        *cov_parameters,
        target_dir,
    )


@nox.session
def format(session: nox.Session):
    """Format the code."""
    session.run("poetry", "install", "--only", "dev", external=True)

    session.run_always(
        "black", ROOT_DIRECTORY.joinpath("pyball"), ROOT_DIRECTORY.joinpath("tests")
    )
    session.run_always(
        "isort", ROOT_DIRECTORY.joinpath("pyball"), ROOT_DIRECTORY.joinpath("tests")
    )


@nox.session
def build(session: nox.Session) -> None:
    """Build the Python wheel."""
    session.run("rm", "-rf", str(ROOT_DIRECTORY.joinpath("dist")), external=True)
    session.run("poetry", "build", "-f", "wheel", external=True)


@nox.session(name="dbuild")
def docker_build(session: nox.Session) -> Tuple[str, str]:
    """Build the Docker image."""
    build(session=session)
    image_tag = (
        session.run_always(
            "poetry",
            "version",
            external=True,
            silent=True,
        )
        .split()[-1]
        .strip()
    )
    image_name = "lulivi/pyball"
    session.run_always(
        "docker",
        "build",
        ".",
        "-t",
        f"{image_name}:{image_tag}",
        "-f",
        str(ROOT_DIRECTORY.joinpath("docker", "Dockerfile")),
        external=True,
    )
    session.run_always(
        "docker", "tag", f"{image_name}:{image_tag}", f"{image_name}:latest", external=True
    )
    return image_name, image_tag


@nox.session(name="dpublish", venv_backend=None)
def docker_publish(session: nox.Session) -> None:
    """Publish the Docker image."""
    image_name, image_tag = docker_build(session=session)
    session.run_always("docker", "push", f"{image_name}:{image_tag}", external=True)
    session.run_always("docker", "push", f"{image_name}:latest", external=True)

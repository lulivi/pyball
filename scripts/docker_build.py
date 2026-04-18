#!/usr/bin/env python3
"""Build and optionally push the Docker image."""

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()


def main() -> None:
    """Main orchestrator: builds Docker image and optionally pushes it."""
    args = parse_arguments()

    clean_dist_directory()
    build_python_wheel()

    version = get_project_version()
    image_tag = f"{args.image}:{version}"
    image_latest = f"{args.image}:latest"

    build_docker_image(image_tag)

    if args.push:
        push_docker_image(image_tag)
        if args.release:
            tag_and_push_latest(image_tag, image_latest)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and optionally push the Docker image.")
    parser.add_argument("--push", action="store_true", help="Push image after building.")
    parser.add_argument(
        "--release", action="store_true", help="Push :latest tag (requires --push)."
    )
    parser.add_argument(
        "--image",
        default=os.environ.get("PYBALL_DOCKER_IMAGE", "lulivi/pyball"),
        help="Image name. Default: lulivi/pyball or PYBALL_DOCKER_IMAGE env var.",
    )
    args = parser.parse_args()

    if args.release and not args.push:
        parser.error("--release requires --push to be set.")

    return args


def clean_dist_directory() -> None:
    """Remove the dist directory to ensure a clean build."""
    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)


def build_python_wheel() -> None:
    """Build the Python wheel using uv."""
    _run_streamed(["uv", "build", "--wheel"])


def get_project_version() -> str:
    """Get the project version from hatch."""
    return _run_captured(["hatch", "version"])


def build_docker_image(image_tag: str) -> None:
    """Build the Docker image with the given tag."""
    _run_streamed(
        ["docker", "build", str(ROOT), "-t", image_tag, "-f", str(ROOT / "docker" / "Dockerfile")]
    )


def push_docker_image(image_tag: str) -> None:
    """Push the Docker image to the registry."""
    _run_streamed(["docker", "push", image_tag])


def tag_and_push_latest(image_tag: str, image_latest: str) -> None:
    """Tag the image as :latest and push it."""
    _run_captured(["docker", "tag", image_tag, image_latest])
    _run_streamed(["docker", "push", image_latest])


def _run_captured(cmd: list[str]) -> str:
    """Run a command silently and return stdout (for reading values)."""
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _run_streamed(cmd: list[str]) -> None:
    """Run a command and stream output directly to the console (CI/CD friendly)."""
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()

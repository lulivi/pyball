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
        "docker",
        "build",
        str(ROOT),
        "-t",
        image_tag,
        "-f",
        str(ROOT / "docker" / "Dockerfile"),
    )
    run("docker", "tag", image_tag, image_latest)

    if args.push:
        run("docker", "push", image_tag)
        run("docker", "push", image_latest)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build script for creating Debian package using Docker.

Works on Windows, macOS, and Linux.
Requires Docker to be installed and running.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"ERROR: {description} failed")
        return False
    return True


def check_docker() -> bool:
    """Check if Docker is available and running."""
    # Check if Docker is installed
    try:
        subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: Docker is not installed or not in PATH")
        print("Please install Docker from https://www.docker.com/products/docker-desktop")
        return False

    # Check if Docker daemon is running
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        print("ERROR: Docker daemon is not running")
        print("Please start Docker and try again")
        return False

    return True


def get_version_from_changelog(project_root: Path) -> str:
    """Extract version from debian/changelog."""
    changelog = project_root / "debian" / "changelog"
    if changelog.exists():
        with open(changelog, "r") as f:
            first_line = f.readline()
            # Format: keko-ts3 (3.13.7-1) trixie; urgency=medium
            import re
            match = re.search(r'\(([^)]+)\)', first_line)
            if match:
                return match.group(1)
    return "unknown"


def main() -> int:
    """Main entry point."""
    # Get project root (parent of scripts directory)
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent

    version = get_version_from_changelog(project_root)

    print("=" * 50)
    print("  TeamSpeak 3 Server - Debian Package Build")
    print(f"  Version: {version}")
    print("=" * 50)
    print()

    # Check Docker
    if not check_docker():
        return 1

    # Build Docker build environment
    print("[1/4] Building Docker build environment...")
    build_dockerfile = project_root / "docker" / "build.Dockerfile"

    if not run_command(
            [
                "docker", "build",
                "--platform=linux/amd64",
                "-t", "keko-ts3-builder",
                "-f", str(build_dockerfile),
                str(project_root),
            ],
            "Docker build environment",
    ):
        return 1

    # Create output directory
    print()
    print("[2/4] Creating output directory...")
    dist_dir = project_root / "dist"
    dist_dir.mkdir(exist_ok=True)

    # Build Debian package
    print()
    print("[3/4] Building Debian package...")

    if not run_command(
            [
                "docker", "run", "--rm",
                "-v", f"{dist_dir}:/output",
                "keko-ts3-builder",
                "/bin/bash", "-c",
                "dpkg-buildpackage -us -uc -b && cp ../*.deb /output/ 2>/dev/null || cp ../*.deb /output/",
            ],
            "Debian package build",
    ):
        return 1

    # Check output
    print()
    print("[4/4] Checking output...")
    deb_files = list(dist_dir.glob("*.deb"))
    if not deb_files:
        print("WARNING: No .deb file found in dist directory")
        print("The build may have failed - check Docker output above")
        return 1

    for deb_file in deb_files:
        print(f"  {deb_file.name}")

    print()
    print("=" * 50)
    print("  Build Complete!")
    print("=" * 50)
    print()
    print(f"Debian package(s) created in: {dist_dir}")
    print()
    print("To install on Debian:")
    print(f"  sudo dpkg -i dist/keko-ts3_{version}_amd64.deb")
    print("  sudo apt install -f  # Install any missing dependencies")
    print()
    print("To start the server:")
    print("  sudo systemctl start keko-ts3")
    print("  sudo systemctl enable keko-ts3  # Enable on boot")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

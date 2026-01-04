#!/usr/bin/env python3
"""Import legacy TeamSpeak 3 server data into keko-ts3.

This script imports data from a legacy TeamSpeak 3 installation backup
into the keko-ts3 Debian package installation.

Usage:
    sudo ./import_legacy.py <backup.tar.gz>

The backup should be a tar.gz archive containing a TeamSpeak 3 server
directory with files like ts3server.sqlitedb, licensekey.dat, files/, etc.
"""

import argparse
import os
import pwd
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


DATA_DIR = Path("/var/lib/teamspeak3")
SERVICE_NAME = "keko-ts3"

# Files to import from legacy backup
IMPORT_FILES = [
    # (source pattern, destination name, required)
    ("ts3server.sqlitedb", "ts3server.sqlitedb", True),
    ("ts3server.sqlitedb-wal", "ts3server.sqlitedb-wal", False),
    ("ts3server.sqlitedb-shm", "ts3server.sqlitedb-shm", False),
    ("licensekey.dat", "licensekey.dat", False),
    ("query_ip_whitelist.txt", "query_ip_allowlist.txt", False),  # Renamed in newer versions
    ("query_ip_allowlist.txt", "query_ip_allowlist.txt", False),
    ("query_ip_blacklist.txt", "query_ip_denylist.txt", False),  # Renamed in newer versions
    ("query_ip_denylist.txt", "query_ip_denylist.txt", False),
    ("ssh_host_rsa_key", "ssh_host_rsa_key", False),
    ("ts3server.ini", "ts3server.ini", False),
]

# Directories to import
IMPORT_DIRS = [
    ("files", "files"),
]


def check_root():
    """Check if running as root."""
    if os.geteuid() != 0:
        print("ERROR: This script must be run as root (sudo)")
        sys.exit(1)


def find_ts3_root(extract_dir: Path) -> Path | None:
    """Find the TeamSpeak 3 server root directory in extracted archive."""
    # Look for ts3server.sqlitedb to identify the TS3 directory
    for path in extract_dir.rglob("ts3server.sqlitedb"):
        return path.parent

    # Also check for the binary as fallback
    for path in extract_dir.rglob("ts3server"):
        if path.is_file():
            return path.parent

    return None


def validate_backup(backup_path: Path) -> bool:
    """Validate that the backup file exists and is a valid tar.gz."""
    if not backup_path.exists():
        print(f"ERROR: Backup file not found: {backup_path}")
        return False

    if not tarfile.is_tarfile(backup_path):
        print(f"ERROR: Not a valid tar archive: {backup_path}")
        return False

    return True


def stop_service():
    """Stop the keko-ts3 service."""
    print(f"Stopping {SERVICE_NAME} service...")
    result = subprocess.run(
        ["systemctl", "stop", SERVICE_NAME],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  Warning: Could not stop service (may not be running)")


def start_service():
    """Start the keko-ts3 service."""
    print(f"Starting {SERVICE_NAME} service...")
    result = subprocess.run(
        ["systemctl", "start", SERVICE_NAME],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  ERROR: Failed to start service")
        print(f"  {result.stderr}")
        return False
    return True


def get_teamspeak3_uid_gid() -> tuple[int, int]:
    """Get the UID and GID for the teamspeak3 user."""
    try:
        pw = pwd.getpwnam("teamspeak3")
        return pw.pw_uid, pw.pw_gid
    except KeyError:
        print("ERROR: teamspeak3 user not found. Is keko-ts3 installed?")
        sys.exit(1)


def import_file(src: Path, dest: Path, uid: int, gid: int):
    """Import a single file."""
    print(f"  Importing: {src.name} -> {dest.name}")
    shutil.copy2(src, dest)
    os.chown(dest, uid, gid)
    os.chmod(dest, 0o640)


def import_directory(src: Path, dest: Path, uid: int, gid: int):
    """Import a directory recursively."""
    print(f"  Importing directory: {src.name}/ -> {dest.name}/")

    if dest.exists():
        shutil.rmtree(dest)

    shutil.copytree(src, dest)

    # Fix ownership recursively
    for root, dirs, files in os.walk(dest):
        os.chown(root, uid, gid)
        for d in dirs:
            os.chown(os.path.join(root, d), uid, gid)
        for f in files:
            os.chown(os.path.join(root, f), uid, gid)


def main():
    parser = argparse.ArgumentParser(
        description="Import legacy TeamSpeak 3 server data into keko-ts3"
    )
    parser.add_argument(
        "backup",
        type=Path,
        help="Path to the legacy backup tar.gz file"
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    print("=" * 55)
    print("  keko-ts3 - Import Legacy TeamSpeak 3 Data")
    print("=" * 55)
    print()

    # Check root
    check_root()

    # Validate backup
    if not validate_backup(args.backup):
        sys.exit(1)

    # Get teamspeak3 user info
    uid, gid = get_teamspeak3_uid_gid()

    # Extract to temp directory
    print(f"Extracting backup: {args.backup}")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        with tarfile.open(args.backup, "r:gz") as tar:
            tar.extractall(tmpdir)

        # Find TS3 root directory
        ts3_root = find_ts3_root(tmpdir)
        if not ts3_root:
            print("ERROR: Could not find TeamSpeak 3 data in backup")
            print("  (Looking for ts3server.sqlitedb)")
            sys.exit(1)

        print(f"Found TeamSpeak 3 data in: {ts3_root.relative_to(tmpdir)}")
        print()

        # List what will be imported
        print("Files to import:")
        files_to_import = []
        for src_name, dest_name, required in IMPORT_FILES:
            src_path = ts3_root / src_name
            if src_path.exists():
                files_to_import.append((src_path, DATA_DIR / dest_name))
                print(f"  [x] {src_name}" + (f" -> {dest_name}" if src_name != dest_name else ""))
            elif required:
                print(f"ERROR: Required file not found: {src_name}")
                sys.exit(1)
            else:
                print(f"  [ ] {src_name} (not found, skipping)")

        dirs_to_import = []
        for src_name, dest_name in IMPORT_DIRS:
            src_path = ts3_root / src_name
            if src_path.exists() and src_path.is_dir():
                dirs_to_import.append((src_path, DATA_DIR / dest_name))
                # Count files in directory
                file_count = sum(1 for _ in src_path.rglob("*") if _.is_file())
                print(f"  [x] {src_name}/ ({file_count} files)")
            else:
                print(f"  [ ] {src_name}/ (not found, skipping)")

        print()
        print(f"Destination: {DATA_DIR}")
        print()

        # Confirmation
        if not args.yes:
            print("WARNING: This will overwrite existing data in the destination!")
            response = input("Continue? [y/N] ")
            if response.lower() != "y":
                print("Aborted.")
                sys.exit(0)

        print()

        # Stop service
        stop_service()

        # Import files
        print("Importing files...")
        for src_path, dest_path in files_to_import:
            import_file(src_path, dest_path, uid, gid)

        # Import directories
        for src_path, dest_path in dirs_to_import:
            import_directory(src_path, dest_path, uid, gid)

        print()

    # Start service
    if start_service():
        print()
        print("=" * 55)
        print("  Import Complete!")
        print("=" * 55)
        print()
        print("Check service status:")
        print(f"  sudo systemctl status {SERVICE_NAME}")
        print()
        print("View logs:")
        print(f"  sudo journalctl -u {SERVICE_NAME} -f")
    else:
        print()
        print("Import completed but service failed to start.")
        print("Check the logs for errors:")
        print(f"  sudo journalctl -u {SERVICE_NAME} -n 50")
        sys.exit(1)


if __name__ == "__main__":
    main()

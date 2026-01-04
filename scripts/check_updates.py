#!/usr/bin/env python3
"""Check for TeamSpeak 3 server updates.

Checks the TeamSpeak downloads page for the latest version and compares
with the currently packaged version.
"""

import re
import ssl
import sys
import urllib.request
import urllib.error
from pathlib import Path


# TeamSpeak downloads page
TS3_DOWNLOADS_URL = "https://www.teamspeak.com/en/downloads/"


_SSL_CONTEXT: ssl.SSLContext | None = None


def get_ssl_context() -> ssl.SSLContext:
    """Get SSL context, trying system certs first, then fallback."""
    global _SSL_CONTEXT
    if _SSL_CONTEXT is not None:
        return _SSL_CONTEXT

    # Try certifi first (most reliable on macOS)
    try:
        import certifi
        _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
        return _SSL_CONTEXT
    except ImportError:
        pass

    # Try default context
    ctx = ssl.create_default_context()

    # Test if it works
    try:
        test_req = urllib.request.Request(
            "https://www.google.com",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        urllib.request.urlopen(test_req, timeout=5, context=ctx)
        _SSL_CONTEXT = ctx
        return _SSL_CONTEXT
    except Exception:
        pass

    # Last resort: unverified context
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    _SSL_CONTEXT = ctx
    return _SSL_CONTEXT


def get_current_version(project_root: Path) -> str | None:
    """Get the currently packaged version from debian/changelog."""
    changelog = project_root / "debian" / "changelog"
    if not changelog.exists():
        return None

    with open(changelog, "r") as f:
        first_line = f.readline()
        # Format: keko-ts3 (3.13.7-1) trixie; urgency=medium
        match = re.search(r'\((\d+\.\d+\.\d+)-\d+\)', first_line)
        if match:
            return match.group(1)
    return None


def fetch_latest_version() -> tuple[str | None, str | None]:
    """Fetch latest version from TeamSpeak downloads page.

    Returns tuple of (version, download_url) or (None, None) on error.
    """
    try:
        req = urllib.request.Request(
            TS3_DOWNLOADS_URL,
            headers={"User-Agent": "Mozilla/5.0 (compatible; keko-ts3-update-checker/1.0)"}
        )
        ssl_ctx = get_ssl_context()
        with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as response:
            html = response.read().decode("utf-8")

        # Look for the linux_amd64 download link
        # Pattern: teamspeak3-server_linux_amd64-VERSION.tar.bz2
        pattern = r'https://files\.teamspeak-services\.com/releases/server/(\d+\.\d+\.\d+)/teamspeak3-server_linux_amd64-\1\.tar\.bz2'
        match = re.search(pattern, html)

        if match:
            version = match.group(1)
            url = match.group(0)
            return version, url

        # Alternative: just find version numbers in server download URLs
        alt_pattern = r'/releases/server/(\d+\.\d+\.\d+)/'
        versions = re.findall(alt_pattern, html)
        if versions:
            version = versions[0]
            url = f"https://files.teamspeak-services.com/releases/server/{version}/teamspeak3-server_linux_amd64-{version}.tar.bz2"
            return version, url

        return None, None

    except urllib.error.URLError as e:
        print(f"ERROR: Failed to fetch downloads page: {e}")
        return None, None
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return None, None


def version_compare(v1: str, v2: str) -> int:
    """Compare two version strings. Returns -1, 0, or 1."""
    parts1 = [int(x) for x in v1.split(".")]
    parts2 = [int(x) for x in v2.split(".")]

    for p1, p2 in zip(parts1, parts2):
        if p1 < p2:
            return -1
        elif p1 > p2:
            return 1

    if len(parts1) < len(parts2):
        return -1
    elif len(parts1) > len(parts2):
        return 1

    return 0


def main() -> int:
    """Main entry point."""
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent

    print("=" * 50)
    print("  TeamSpeak 3 Server - Update Checker")
    print("=" * 50)
    print()

    # Get current version
    current = get_current_version(project_root)
    if current:
        print(f"Current packaged version: {current}")
    else:
        print("Current packaged version: unknown")
        print("  (Could not read debian/changelog)")

    print()
    print("Checking TeamSpeak downloads page...")
    print()

    # Fetch latest version
    latest, download_url = fetch_latest_version()
    if not latest:
        print("ERROR: Could not determine latest version")
        return 1

    print(f"Latest available version: {latest}")

    # Compare versions
    if current:
        cmp = version_compare(current, latest)
        print()
        if cmp == 0:
            print("Status: UP TO DATE")
        elif cmp < 0:
            print(f"Status: UPDATE AVAILABLE ({current} -> {latest})")
            print()
            print("To update, modify these files:")
            print("  1. debian/changelog - Add new version entry")
            print("  2. debian/rules - Update TS3_VERSION variable")
            print()
            print("Download URL:")
            print(f"  {download_url}")
        else:
            print(f"Status: Current version ({current}) is newer than available ({latest})?")
            print("  This might indicate a version parsing issue.")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

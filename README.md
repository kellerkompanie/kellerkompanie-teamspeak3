# kellerkompanie-teamspeak3

Debian package for TeamSpeak 3 Server (keko-ts3).

## Requirements

- Docker (for building the package)
- Python 3.10+ (for the build scripts)

## Building the Package

```bash
./scripts/build_deb.py
```

This will create a `.deb` package in the `dist/` directory.

## Checking for Updates

```bash
./scripts/check_updates.py
```

This will check the TeamSpeak file server for new versions.

## Installation

```bash
sudo dpkg -i dist/keko-ts3_*.deb
sudo apt install -f  # Install any missing dependencies
```

## Usage

```bash
# Start the server
sudo systemctl start keko-ts3

# Enable on boot
sudo systemctl enable keko-ts3

# Check status
sudo systemctl status keko-ts3

# View logs
sudo journalctl -u keko-ts3 -f
# or
tail -f /var/log/teamspeak3/ts3server_*.log
```

## File Locations

| Path | Description |
|------|-------------|
| `/opt/teamspeak3/` | Server binaries |
| `/var/lib/teamspeak3/` | Data directory (database, files, config) |
| `/var/log/teamspeak3/` | Log files |
| `/var/backups/keko-ts3/` | Backup archives |

## First Run

On first start, the server will create admin credentials. Check the logs:

```bash
sudo journalctl -u keko-ts3 | grep -A5 "token="
```

## License Key

A TeamSpeak 3 server without a license is limited to 1 virtual server with 32 slots. If you have a license, install it as follows:

```bash
# Copy your license file to the data directory
sudo cp licensekey.dat /var/lib/teamspeak3/

# Set correct ownership
sudo chown teamspeak3:teamspeak3 /var/lib/teamspeak3/licensekey.dat

# Restart the server to apply
sudo systemctl restart keko-ts3
```

Verify the license is active:

```bash
sudo journalctl -u keko-ts3 | grep -i license
```

The license file is stored in `/var/lib/teamspeak3/` so it persists across package upgrades.

## Backups

Automatic backups are configured via cron:

- **Yearly**: 2:00 AM on January 1st (kept forever)
- **Monthly**: 3:00 AM on the 1st of each month (last 6 kept)

### Backup location

Backups are stored in `/var/backups/keko-ts3/` as compressed tar archives:

```
/var/backups/keko-ts3/
├── keko-ts3_monthly_20260201_030000.tar.gz   # Monthly (rotated)
├── keko-ts3_monthly_20260301_030000.tar.gz
└── keko-ts3_yearly_20260101.tar.gz           # Yearly (kept forever)
```

### Manual backup

```bash
sudo keko-ts3-backup --monthly  # Create monthly backup (rotated)
sudo keko-ts3-backup --yearly   # Create yearly backup (kept forever)
sudo keko-ts3-backup --all      # Create both
sudo keko-ts3-backup --list     # List available backups
```

### Restore from backup

```bash
# List available backups
sudo keko-ts3-backup --list

# Restore from a backup (stops server, restores, starts server)
sudo keko-ts3-backup --restore keko-ts3_monthly_20260101_030000.tar.gz

# Or use full path
sudo keko-ts3-backup --restore /var/backups/keko-ts3/keko-ts3_yearly_20260101.tar.gz
```

The restore command will prompt for confirmation before proceeding.

### Retention

- **Monthly backups**: Last 6 are kept, older ones are automatically deleted
- **Yearly backups**: Created in January, kept forever (one per year)

## Updating to a New Version

### 1. Check for updates

```bash
./scripts/check_updates.py
```

If a new version is available (e.g., 3.13.8), proceed with the following steps.

### 2. Update `debian/rules`

Change the `TS3_VERSION` variable at the top:

```makefile
TS3_VERSION = 3.13.8
```

### 3. Update `debian/changelog`

Add a new entry at the **top** of the file (newest first):

```
keko-ts3 (3.13.8-1) trixie; urgency=medium

  * Update to TeamSpeak 3 Server version 3.13.8

 -- Schwaggot <schwaggot@kellerkompanie.com>  Mon, 05 Jan 2026 12:00:00 +0100
```

Note: The format is strict - the signature line must start with exactly one space.

### 4. Build the new package

```bash
./scripts/build_deb.py
```

This downloads the new TS3 version and creates `dist/keko-ts3_3.13.8-1_amd64.deb`.

### 5. Deploy to your server

Copy the `.deb` file to your server and install:

```bash
sudo systemctl stop keko-ts3
sudo dpkg -i keko-ts3_3.13.8-1_amd64.deb
sudo systemctl start keko-ts3
```

The upgrade preserves all data in `/var/lib/teamspeak3/` (database, uploaded files, config).

### 6. Verify

```bash
sudo systemctl status keko-ts3
```

Check the logs for the new version:

```bash
sudo journalctl -u keko-ts3 -n 50
```

## Uninstallation

```bash
# Remove package but keep data
sudo apt remove keko-ts3

# Remove package and all data
sudo apt purge keko-ts3
```

## License

The Debian packaging is MIT licensed.

TeamSpeak 3 Server is proprietary software by TeamSpeak Systems GmbH.

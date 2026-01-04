# Yearly backup of TeamSpeak 3 server data (kept forever)
# Runs at 2:00 AM on January 1st
0 2 1 1 * root /usr/sbin/keko-ts3-backup --yearly > /var/log/teamspeak3/backup.log 2>&1

# Monthly backup of TeamSpeak 3 server data (rotated, last 6 kept)
# Runs at 3:00 AM on the 1st of each month
0 3 1 * * root /usr/sbin/keko-ts3-backup --monthly >> /var/log/teamspeak3/backup.log 2>&1

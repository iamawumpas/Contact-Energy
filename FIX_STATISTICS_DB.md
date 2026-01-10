# Fix Contact Energy Statistics Database

The integration is encountering errors because the Home Assistant database contains corrupt Contact Energy statistics entries with invalid `mean_type` values.

## Problem

The database has existing entries with `mean_type: .` (invalid) and when the integration tries to update them, it causes UNIQUE constraint violations.

## Solution

Delete the corrupt database entries and let the integration recreate them correctly.

## Method 1: Using the Python Script (Recommended)

Home Assistant Core (venv) example:
```bash
# Stop HA Core
sudo systemctl stop home-assistant@homeassistant

# Activate venv if you prefer running from the HA user
# sudo -u homeassistant -H -s
# source /srv/homeassistant/bin/activate

# Run the cleanup script against your DB path (Core default shown)
python3 fix_statistics_db.py /home/homeassistant/.homeassistant/home-assistant_v2.db

# Start HA Core
sudo systemctl start home-assistant@homeassistant
```

Container/OS example:
```bash
# Stop HA, then run against /config DB
docker stop homeassistant
python3 fix_statistics_db.py /config/home-assistant_v2.db
docker start homeassistant
```

The integration will automatically recreate the statistics with correct metadata.

## Method 2: Manual SQL (Advanced)

If you prefer to run SQL directly (SQLite default shown):

1. Stop Home Assistant (Core: `sudo systemctl stop home-assistant@homeassistant`).
2. Backup your database:
   ```bash
   cp /home/homeassistant/.homeassistant/home-assistant_v2.db \
      /home/homeassistant/.homeassistant/home-assistant_v2.db.backup
   ```
3. Open the database:
   ```bash
   sqlite3 /home/homeassistant/.homeassistant/home-assistant_v2.db
   ```
4. Run these SQL commands:
   ```sql
   -- Find corrupt entries
   SELECT id, statistic_id, mean_type 
   FROM statistics_meta 
   WHERE source = 'contact_energy';

   -- Delete related data first
   DELETE FROM statistics WHERE metadata_id IN (
       SELECT id FROM statistics_meta WHERE source = 'contact_energy'
   );
   
   DELETE FROM statistics_short_term WHERE metadata_id IN (
       SELECT id FROM statistics_meta WHERE source = 'contact_energy'
   );
   
   -- Delete corrupt metadata
   DELETE FROM statistics_meta WHERE source = 'contact_energy';
   
   -- Exit
   .quit
   ```
5. Remove SQLite WAL/SHM if present (prevents resurrecting old pages):
   ```bash
   rm -f /home/homeassistant/.homeassistant/home-assistant_v2.db-wal \
         /home/homeassistant/.homeassistant/home-assistant_v2.db-shm
   ```
6. Restart Home Assistant.

External DBs (run equivalent SQL on MariaDB/PostgreSQL):
```sql
DELETE FROM statistics WHERE metadata_id IN (SELECT id FROM statistics_meta WHERE source = 'contact_energy');
DELETE FROM statistics_short_term WHERE metadata_id IN (SELECT id FROM statistics_meta WHERE source = 'contact_energy');
DELETE FROM statistics_meta WHERE source = 'contact_energy';
```

## Method 3: Using Home Assistant Developer Tools (Easiest)

1. Go to Developer Tools → Statistics
2. Search for "contact_energy"
3. Click "Fix issue" on each Contact Energy statistic
4. Restart Home Assistant

## Verification

After cleanup and restart, check the logs. You should see:
- No "Invalid mean type" errors
- No UNIQUE constraint errors
- Statistics importing successfully

The integration will automatically reimport all historical data with correct metadata.

## What Fixed the Code

Version 1.7.47 fixed the root cause by using dictionary unpacking to construct `StatisticMetaData`, ensuring the `mean_type` field is completely absent when `has_mean=False`. The database cleanup is only needed to remove the old corrupt entries created by previous versions.

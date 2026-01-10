# Complete Cleanup Instructions for Statistics Fix

This guide now includes specific steps for Home Assistant Core (Python venv) installs.

## The Problem
Even after updating to v1.7.47, old database rows and caches can resurrect invalid metadata, causing “Invalid mean type” and UNIQUE constraint errors. A clean stop-purge-start fixes this.

## Identify Your Setup
- Home Assistant Core (venv): typically installed as user `homeassistant` with config at `/home/homeassistant/.homeassistant`, service `home-assistant@homeassistant`.
- Container/OS/Supervised: config at `/config`, managed by Supervisor or Docker.

Set your config dir for commands below:
```bash
# For Core (venv)
CONFIG_DIR=/home/homeassistant/.homeassistant
# For Container/OS
# CONFIG_DIR=/config
```

## 1) Stop Home Assistant cleanly
```bash
# Core (venv) via systemd
sudo systemctl stop home-assistant@homeassistant

# If running manually in a terminal (no systemd), stop the process
# e.g., Ctrl+C in the running terminal or:
pkill -f "hass -c" || pkill -f homeassistant || true

# Container/OS (if applicable)
# docker stop homeassistant
```

Verify it’s stopped (no hass/homeassistant processes).

## 2) Confirm Recorder backend (SQLite vs external)
```bash
grep -n "^recorder:" -n ${CONFIG_DIR}/configuration.yaml || true
grep -n "db_url" ${CONFIG_DIR}/configuration.yaml || true
```
- No `db_url` set → default SQLite: `${CONFIG_DIR}/home-assistant_v2.db`
- If `db_url` is set (MariaDB/PostgreSQL), use the External DB steps below.

## 3) Purge Python caches for the integration
```bash
cd ${CONFIG_DIR}/custom_components/contact_energy
rm -rf __pycache__
find . -name "*.pyc" -delete

# Optional (if exists on your system):
if [ -d "${CONFIG_DIR}/deps/python" ]; then
  find "${CONFIG_DIR}/deps/python" -iname "*contact*energy*" -maxdepth 2 -print -exec rm -rf {} +
fi
```

## 4) Purge statistics data (SQLite)
Backup first, then either delete rows or remove the whole DB.

Option A — Targeted delete of Contact Energy rows:
```bash
cd ${CONFIG_DIR}
cp -a home-assistant_v2.db home-assistant_v2.db.bak-$(date +%F)

sqlite3 home-assistant_v2.db <<'SQL'
DELETE FROM statistics WHERE metadata_id IN (SELECT id FROM statistics_meta WHERE source = 'contact_energy');
DELETE FROM statistics_short_term WHERE metadata_id IN (SELECT id FROM statistics_meta WHERE source = 'contact_energy');
DELETE FROM statistics_meta WHERE source = 'contact_energy';
.quit
SQL

# Remove SQLite WAL/SHM to avoid resurrecting old pages
rm -f home-assistant_v2.db-wal home-assistant_v2.db-shm
```

Option B — Full DB reset (you will lose all history):
```bash
cd ${CONFIG_DIR}
cp -a home-assistant_v2.db home-assistant_v2.db.bak-$(date +%F)
rm -f home-assistant_v2.db home-assistant_v2.db-wal home-assistant_v2.db-shm
```

## 5) External DB (MariaDB/PostgreSQL)
Run equivalent DELETEs on your DB:

MariaDB/MySQL:
```sql
DELETE FROM statistics WHERE metadata_id IN (SELECT id FROM statistics_meta WHERE source = 'contact_energy');
DELETE FROM statistics_short_term WHERE metadata_id IN (SELECT id FROM statistics_meta WHERE source = 'contact_energy');
DELETE FROM statistics_meta WHERE source = 'contact_energy';
```

PostgreSQL:
```sql
DELETE FROM statistics WHERE metadata_id IN (SELECT id FROM statistics_meta WHERE source = 'contact_energy');
DELETE FROM statistics_short_term WHERE metadata_id IN (SELECT id FROM statistics_meta WHERE source = 'contact_energy');
DELETE FROM statistics_meta WHERE source = 'contact_energy';
```

## 6) Clear usage cache files
```bash
rm -f ${CONFIG_DIR}/usage_cache_*.json
```

## 7) Reset Energy preferences and stale references
- In UI: Settings → Dashboards → Energy → remove any sources referencing `contact_energy:*` stats.
- Optional last resort: backup `${CONFIG_DIR}/.storage/energy` and remove stale `contact_energy` references manually.
- If entities/devices linger: remove via UI Integrations/Entities; as last resort, edit `${CONFIG_DIR}/.storage/core.entity_registry` and related JSON (with HA stopped).

## 8) Start Home Assistant and verify
```bash
# Core (venv)
sudo systemctl start home-assistant@homeassistant

# Or start manually in venv
# sudo -u homeassistant -H -s
# source /srv/homeassistant/bin/activate
# hass -c ${CONFIG_DIR}

# Container/OS
# docker start homeassistant
```

Watch logs:
```bash
journalctl -u home-assistant@homeassistant -f
# or
tail -f ${CONFIG_DIR}/home-assistant.log | grep -i contact_energy
```

You should NOT see: "Invalid mean type" or UNIQUE constraint errors. You should see imports of historical statistics once the integration runs.

## Quick Commands (Core venv, SQLite, targeted purge)
```bash
CONFIG_DIR=/home/homeassistant/.homeassistant
sudo systemctl stop home-assistant@homeassistant

cd ${CONFIG_DIR}/custom_components/contact_energy && rm -rf __pycache__ && find . -name "*.pyc" -delete

cd ${CONFIG_DIR}
cp -a home-assistant_v2.db home-assistant_v2.db.bak-$(date +%F)
sqlite3 home-assistant_v2.db <<'SQL'
DELETE FROM statistics WHERE metadata_id IN (SELECT id FROM statistics_meta WHERE source = 'contact_energy');
DELETE FROM statistics_short_term WHERE metadata_id IN (SELECT id FROM statistics_meta WHERE source = 'contact_energy');
DELETE FROM statistics_meta WHERE source = 'contact_energy';
.quit
SQL
rm -f home-assistant_v2.db-wal home-assistant_v2.db-shm

rm -f ${CONFIG_DIR}/usage_cache_*.json

sudo systemctl start home-assistant@homeassistant
```

## Alternative: Full Reinstall
If the above doesn't work:

1. Remove the integration via UI (Settings → Devices & Services → Contact Energy → Delete).
2. Delete files:
   ```bash
   rm -rf ${CONFIG_DIR}/custom_components/contact_energy
   rm -f  ${CONFIG_DIR}/usage_cache_*.json
   ```
3. Start Home Assistant, reinstall v1.7.47 (HACS or manual), restart, and reconfigure.

## Still Not Working?
If errors persist:

1. Confirm you removed WAL/SHM files for SQLite or purged rows in your external DB.
2. Ensure Energy preferences no longer reference `contact_energy:*` statistics.
3. Restart the entire host to clear lingering file handles.

As an alternative to manual SQL, you can also use the helper in [fix_statistics_db.py](fix_statistics_db.py) to remove corrupt rows, then restart Home Assistant.

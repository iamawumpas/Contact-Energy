#!/usr/bin/env python3
"""
Fix Contact Energy statistics database entries with invalid mean_type.

This script deletes corrupt statistics_meta entries for Contact Energy
that have invalid mean_type values, allowing the integration to recreate
them with correct metadata.

Run this script, then restart Home Assistant.
"""

import sqlite3
import sys
from pathlib import Path


def fix_statistics_db(db_path: str):
    """Delete corrupt Contact Energy statistics metadata entries."""
    
    print(f"Opening database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Find Contact Energy statistic_ids with invalid mean_type
        print("\nSearching for corrupt Contact Energy statistics...")
        cursor.execute("""
            SELECT id, statistic_id, mean_type 
            FROM statistics_meta 
            WHERE source = 'contact_energy'
            AND (mean_type IS NOT NULL AND mean_type != '')
        """)
        
        corrupt_entries = cursor.fetchall()
        
        if not corrupt_entries:
            print("✓ No corrupt entries found!")
            return
        
        print(f"\nFound {len(corrupt_entries)} corrupt entries:")
        for row in corrupt_entries:
            print(f"  - ID {row[0]}: {row[1]} (mean_type: '{row[2]}')")
        
        # Get metadata IDs to delete
        metadata_ids = [row[0] for row in corrupt_entries]
        
        # Delete related statistics data first (foreign key constraint)
        print("\nDeleting related statistics data...")
        placeholders = ','.join('?' * len(metadata_ids))
        cursor.execute(f"""
            DELETE FROM statistics 
            WHERE metadata_id IN ({placeholders})
        """, metadata_ids)
        deleted_stats = cursor.rowcount
        print(f"  Deleted {deleted_stats} statistics records")
        
        # Delete related short_term_statistics data
        cursor.execute(f"""
            DELETE FROM statistics_short_term 
            WHERE metadata_id IN ({placeholders})
        """, metadata_ids)
        deleted_short_term = cursor.rowcount
        print(f"  Deleted {deleted_short_term} short-term statistics records")
        
        # Delete the corrupt metadata entries
        print("\nDeleting corrupt metadata entries...")
        cursor.execute(f"""
            DELETE FROM statistics_meta 
            WHERE id IN ({placeholders})
        """, metadata_ids)
        deleted_meta = cursor.rowcount
        print(f"  Deleted {deleted_meta} metadata entries")
        
        # Commit changes
        conn.commit()
        print("\n✓ Database cleanup complete!")
        print("\nNext steps:")
        print("1. Restart Home Assistant")
        print("2. The integration will recreate statistics with correct metadata")
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    # Default Home Assistant database path
    default_db = Path.home() / ".homeassistant" / "home-assistant_v2.db"
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    elif default_db.exists():
        db_path = str(default_db)
    else:
        print("Usage: python fix_statistics_db.py [path_to_home-assistant_v2.db]")
        print("\nCannot find default database at:", default_db)
        sys.exit(1)
    
    fix_statistics_db(db_path)

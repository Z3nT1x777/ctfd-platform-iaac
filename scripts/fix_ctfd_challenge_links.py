#!/usr/bin/env python3
"""
Quick fix: Update CTFd challenges with button links directly in database.
No API tokens, no complexity - just a simple DB update.

Usage:
    python fix_ctfd_challenge_links.py
"""

import os
import sys
from pathlib import Path

# MySQL connection via docker-compose orchestrator setup
CTFD_DB_HOST = "127.0.0.1"
CTFD_DB_USER = "ctfd"
CTFD_DB_PASSWORD = "CTFdPassword123!"
CTFD_DB_NAME = "ctfd"
INSTANCE_BASE_URL = "http://192.168.56.10"


def update_challenge_links():
    """Update all challenge connection_info with button links"""
    try:
        import mysqldb
    except ImportError:
        print("❌ mysqldb not available, trying pymysql...")
        import pymysql as mysqldb

    print(f"🔄 Connecting to CTFd database: {CTFD_DB_HOST}:{CTFD_DB_NAME}")
    
    conn = mysqldb.connect(
        host=CTFD_DB_HOST,
        user=CTFD_DB_USER,
        passwd=CTFD_DB_PASSWORD,
        db=CTFD_DB_NAME,
    )
    cursor = conn.cursor()

    try:
        # Get all challenges
        cursor.execute("SELECT id, name FROM challenges")
        challenges = cursor.fetchall()
        
        print(f"📋 Found {len(challenges)} challenges:")
        synced = 0
        
        for ch_id, ch_name in challenges:
            # Generate direct launch URL.
            button_url = f"{INSTANCE_BASE_URL}/plugins/orchestrator/launch?challenge_id={ch_id}"
            
            # Update connection_info
            cursor.execute(
                "UPDATE challenges SET connection_info = %s WHERE id = %s",
                (button_url, ch_id),
            )
            print(f"   ✅ {ch_name} → {button_url}")
            synced += 1
        
        conn.commit()
        print(f"\n✅ Success! Updated {synced} challenges with launch links")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        return False

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    success = update_challenge_links()
    sys.exit(0 if success else 1)

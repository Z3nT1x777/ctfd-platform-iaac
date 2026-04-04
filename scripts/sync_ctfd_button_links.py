#!/usr/bin/env python3
"""
Sync CTFd challenge connection_info with launch button links.
Uses the ORCHESTRATOR_SIGNING_SECRET for authentication.
No API token needed!

Usage:
    python sync_ctfd_button_links.py http://192.168.56.10
    
Environment:
    ORCHESTRATOR_SIGNING_SECRET - Shared secret (default: ChangeMe-Orchestrator-Signing-Secret)
"""

import sys
import os
import json
import requests

def sync_button_links(ctfd_url: str, secret: str = "") -> bool:
    """
    Call the /sync endpoint to update button links.
    
    Args:
        ctfd_url: Base CTFd URL (e.g., http://192.168.56.10)
        secret: ORCHESTRATOR_SIGNING_SECRET for auth
        
    Returns:
        True if successful, False otherwise
    """
    if not secret:
        secret = os.getenv(
            "ORCHESTRATOR_SIGNING_SECRET",
            "ChangeMe-Orchestrator-Signing-Secret"
        )
    
    url = f"{ctfd_url.rstrip('/')}/plugins/orchestrator/sync"
    
    print(f"🔄 Syncing CTFd challenges with launch button links...")
    print(f"   URL: {url}")
    print(f"   Secret: {secret[:10]}...")
    
    try:
        response = requests.post(
            url,
            headers={
                "X-Orchestrator-Secret": secret,
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        
        data = response.json()
        print(f"\n📋 Response:")
        print(json.dumps(data, indent=2))
        
        if data.get("ok"):
            print(f"\n✅ Sync completed successfully!")
            print(f"   Updated {data.get('synced', 0)}/{data.get('total', 0)} challenges")
            return True
        else:
            print(f"\n❌ Sync failed: {data.get('error', 'unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sync_ctfd_button_links.py <ctfd_url>")
        print("Example: python sync_ctfd_button_links.py http://192.168.56.10")
        sys.exit(1)
    
    ctfd_url = sys.argv[1]
    secret = sys.argv[2] if len(sys.argv) > 2 else ""
    
    success = sync_button_links(ctfd_url, secret)
    sys.exit(0 if success else 1)

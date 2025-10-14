#!/usr/bin/env python3
"""
Quick test script to check Contact Energy API response structure.
Run this in Home Assistant's Python environment to see what we actually get.
"""

import asyncio
import aiohttp
import json
import os

async def test_api():
    # You'll need to replace these with your actual credentials
    email = "YOUR_EMAIL"  # Replace with your Contact Energy email
    password = "YOUR_PASSWORD"  # Replace with your Contact Energy password
    
    async with aiohttp.ClientSession() as session:
        # Login first
        login_data = {"username": email, "password": password}
        async with session.post("https://api.contact-digital-prod.net/auth/v1/login", json=login_data) as resp:
            if resp.status == 200:
                login_result = await resp.json()
                token = login_result.get("access_token")
                print(f"Login successful, token: {token[:20]}...")
                
                # Get account details
                headers = {"Authorization": f"Bearer {token}"}
                async with session.get("https://api.contact-digital-prod.net/accounts/v2", headers=headers) as account_resp:
                    if account_resp.status == 200:
                        account_data = await account_resp.json()
                        print("\n=== ACCOUNT DATA STRUCTURE ===")
                        print(json.dumps(account_data, indent=2))
                        
                        # Show top-level keys
                        print(f"\nTop-level keys: {list(account_data.keys())}")
                        
                        # Look for common fields
                        if 'accountDetail' in account_data:
                            print(f"accountDetail keys: {list(account_data['accountDetail'].keys())}")
                        if 'account' in account_data:
                            print(f"account keys: {list(account_data['account'].keys())}")
                        
                    else:
                        print(f"Account request failed: {account_resp.status}")
                        print(await account_resp.text())
            else:
                print(f"Login failed: {resp.status}")
                print(await resp.text())

if __name__ == "__main__":
    asyncio.run(test_api())
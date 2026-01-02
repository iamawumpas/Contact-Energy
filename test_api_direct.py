#!/usr/bin/env python3
"""Direct API testing script to diagnose Contact Energy API issues."""

import asyncio
import aiohttp
import json
from datetime import date, timedelta

# API Configuration
BASE_URL = "https://api.contact-digital-prod.net"
API_KEY = "kbIthASA7e1M3NmpMdGrn2Yqe0yHcCjL4QNPSUij"

# Test Credentials
EMAIL = "mike.and.elspeth@gmail.com"
PASSWORD = "maGellan8021"

# Store auth data for use in other tests
auth_data = {}


async def test_authentication():
    """Test 1: Authenticate and get token."""
    print("\n" + "="*60)
    print("TEST 1: AUTHENTICATION (/login/v2)")
    print("="*60)
    
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "username": EMAIL,
        "password": PASSWORD
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BASE_URL}/login/v2",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                print(f"Status: {resp.status}")
                data = await resp.json()
                print(f"Response keys: {list(data.keys())}")
                print(json.dumps(data, indent=2))
                
                if resp.status == 200:
                    global auth_data
                    auth_data = data
                    print("\n✅ Authentication successful!")
                    print(f"   Token: {data.get('token')[:20]}...")
                    print(f"   Segment: {data.get('segment')}")
                    print(f"   BP (Business Partner): {data.get('bp')}")
                    return True
                else:
                    print(f"\n❌ Authentication failed with status {resp.status}")
                    return False
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False


async def test_accounts_without_ba():
    """Test 2: Get accounts WITHOUT ba parameter."""
    print("\n" + "="*60)
    print("TEST 2: GET ACCOUNTS (without 'ba' parameter)")
    print("="*60)
    
    if not auth_data.get("token"):
        print("❌ Skipping - no token from authentication")
        return None
    
    headers = {
        "x-api-key": API_KEY,
        "session": auth_data["token"],
        "authorization": auth_data["token"],
    }
    
    try:
        url = f"{BASE_URL}/accounts/v2"
        print(f"URL: {url}")
        print(f"Headers: x-api-key, session, authorization")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                print(f"Status: {resp.status}")
                
                if resp.status in [200, 400, 401, 403, 404, 502]:
                    try:
                        data = await resp.json()
                        print(f"Response structure:")
                        if isinstance(data, dict):
                            print(f"  Keys: {list(data.keys())}")
                        print(json.dumps(data, indent=2)[:500] + "...")
                        
                        if resp.status == 200:
                            print("\n✅ Request successful (without ba)")
                            # Extract contract info for later tests
                            if "accountDetail" in data and "contracts" in data["accountDetail"]:
                                contracts = data["accountDetail"]["contracts"]
                                if contracts:
                                    print(f"\n📋 Found {len(contracts)} contract(s):")
                                    for i, contract in enumerate(contracts):
                                        print(f"   Contract {i}: ID={contract.get('id')}, Status={contract.get('status')}")
                            return data
                        else:
                            print(f"\n❌ Request failed with status {resp.status}")
                            return None
                    except Exception as je:
                        print(f"Could not parse JSON: {je}")
                        text = await resp.text()
                        print(f"Response text: {text[:200]}")
                        return None
                else:
                    print(f"Unexpected status: {resp.status}")
                    return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_accounts_with_ba():
    """Test 3: Get accounts WITH ba parameter."""
    print("\n" + "="*60)
    print("TEST 3: GET ACCOUNTS (with 'ba' parameter)")
    print("="*60)
    
    if not auth_data.get("token"):
        print("❌ Skipping - no token from authentication")
        return None
    
    if not auth_data.get("bp"):
        print("❌ Skipping - no BP from authentication")
        return None
    
    headers = {
        "x-api-key": API_KEY,
        "session": auth_data["token"],
        "authorization": auth_data["token"],
    }
    
    try:
        # Try with bp as ba parameter
        url = f"{BASE_URL}/accounts/v2?ba={auth_data['bp']}"
        print(f"URL: {url}")
        print(f"Headers: x-api-key, session, authorization")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                print(f"Status: {resp.status}")
                
                if resp.status in [200, 400, 401, 403, 404, 502]:
                    try:
                        data = await resp.json()
                        print(f"Response status: {resp.status}")
                        if isinstance(data, dict):
                            print(f"Response keys: {list(data.keys())}")
                        
                        if resp.status == 200:
                            print("\n✅ Request successful (with ba)")
                            return data
                        else:
                            print(f"\n⚠️ Request returned status {resp.status} (with ba)")
                            print(json.dumps(data, indent=2)[:300])
                            return None
                    except Exception as je:
                        print(f"Could not parse JSON: {je}")
                        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_usage_endpoint(contract_id, account_id):
    """Test 4: Get usage data."""
    print("\n" + "="*60)
    print(f"TEST 4: GET USAGE DATA")
    print(f"Contract ID: {contract_id}")
    print(f"Account ID (ba): {account_id}")
    print("="*60)
    
    if not auth_data.get("token"):
        print("❌ Skipping - no token from authentication")
        return False
    
    headers = {
        "x-api-key": API_KEY,
        "session": auth_data["token"],
        "authorization": auth_data["token"],
        "Content-Type": "application/json",
    }
    
    # Test with dates in last 9 days (for hourly data)
    today = date.today()
    from_date = today - timedelta(days=1)  # Yesterday
    to_date = today  # Today
    
    # Test all three intervals
    for interval in ["hourly", "daily", "monthly"]:
        print(f"\n--- Testing {interval.upper()} interval ---")
        
        # Try WITHOUT ba parameter first
        url = f"{BASE_URL}/usage/v2/{contract_id}?interval={interval}&from={from_date}&to={to_date}"
        print(f"URL (without ba): {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    print(f"  Status (without ba): {resp.status}")
                    
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"  ✅ Success! Got {len(data) if isinstance(data, list) else 'data'} records")
                    elif resp.status == 404:
                        print(f"  ❌ 404 Not Found (contract may not exist or wrong ID)")
                    elif resp.status == 502:
                        print(f"  ❌ 502 Bad Gateway (server error)")
                    else:
                        print(f"  ⚠️ Status {resp.status}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Try WITH ba parameter
        url_with_ba = f"{BASE_URL}/usage/v2/{contract_id}?ba={account_id}&interval={interval}&from={from_date}&to={to_date}"
        print(f"URL (with ba):    {url_with_ba}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url_with_ba,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    print(f"  Status (with ba):    {resp.status}")
                    
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"  ✅ Success! Got {len(data) if isinstance(data, list) else 'data'} records")
                    elif resp.status == 404:
                        print(f"  ❌ 404 Not Found")
                    elif resp.status == 502:
                        print(f"  ❌ 502 Bad Gateway")
                    else:
                        print(f"  ⚠️ Status {resp.status}")
        except Exception as e:
            print(f"  Error: {e}")


async def main():
    """Run all tests."""
    print("\n\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  CONTACT ENERGY API - DIRECT TESTING".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    # Test 1: Authentication
    auth_ok = await test_authentication()
    if not auth_ok:
        print("\n❌ Authentication failed. Cannot proceed with other tests.")
        return
    
    # Test 2: Accounts without ba
    accounts_data = await test_accounts_without_ba()
    
    # Test 3: Accounts with ba
    accounts_with_ba = await test_accounts_with_ba()
    
    # Test 4: Usage endpoint (if we got account data)
    if accounts_data and isinstance(accounts_data, dict):
        try:
            if "accountDetail" in accounts_data and "contracts" in accounts_data["accountDetail"]:
                contracts = accounts_data["accountDetail"]["contracts"]
                if contracts:
                    contract = contracts[0]  # Use first contract
                    contract_id = contract.get("id")
                    
                    # Get account ID from accountSummary or accountDetail
                    account_id = accounts_data.get("accountDetail", {}).get("id")
                    
                    if contract_id and account_id:
                        print(f"\nUsing Contract ID: {contract_id}")
                        print(f"Using Account ID (ba): {account_id}")
                        await test_usage_endpoint(contract_id, account_id)
                    else:
                        print(f"Could not extract contract/account IDs")
        except Exception as e:
            print(f"Error extracting contract info: {e}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

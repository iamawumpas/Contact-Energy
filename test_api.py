#!/usr/bin/env python3
"""
Test script to directly interrogate Contact Energy API
"""
import asyncio
import aiohttp
from datetime import datetime, timedelta
import json

# Credentials
EMAIL = "mike.and.elspeth@gmail.com"
PASSWORD = "##maGellan8021##"

# API Configuration
URL_BASE = "https://api.contact-digital-prod.net"
API_KEY = "z840P4lQCH9TqcjC9L2pP157DZcZJMcr5tVQCvyx"


async def login(session):
    """Login and get API token"""
    url = f"{URL_BASE}/login/v2"
    headers = {"x-api-key": API_KEY}
    data = {"username": EMAIL, "password": PASSWORD}
    
    print(f"🔐 Logging in as {EMAIL}...")
    async with session.post(url, json=data, headers=headers) as resp:
        print(f"   Status: {resp.status}")
        result = await resp.json()
        if resp.status == 200 and result.get("token"):
            print(f"   ✅ Login successful")
            return result["token"]
        else:
            print(f"   ❌ Login failed: {result}")
            return None


async def get_account_details(session, token):
    """Get account details to find contract_id and ICP"""
    url = f"{URL_BASE}/accounts/v2"
    headers = {"x-api-key": API_KEY, "session": token}
    
    print(f"\n📋 Fetching account details...")
    async with session.get(url, headers=headers) as resp:
        print(f"   Status: {resp.status}")
        data = await resp.json()
        
        if resp.status == 200:
            # Save full response for inspection
            with open("/tmp/account_details.json", "w") as f:
                json.dump(data, f, indent=2)
            print(f"   ✅ Full response saved to /tmp/account_details.json")
            
            # Extract key info
            account_detail = data.get("accountDetail", {})
            account_id = account_detail.get("id")
            print(f"\n   Account ID: {account_id}")
            
            contracts = account_detail.get("contracts", [])
            print(f"   Found {len(contracts)} contract(s):")
            
            for i, contract in enumerate(contracts):
                contract_id = contract.get("id")
                icp = contract.get("icp")
                contract_type = contract.get("contractTypeLabel")
                print(f"     [{i}] Contract ID: {contract_id}")
                print(f"         ICP: {icp}")
                print(f"         Type: {contract_type}")
            
            return account_id, contracts
        else:
            print(f"   ❌ Failed: {data}")
            return None, []


async def get_usage_data(session, token, account_id, contract_id, target_date):
    """Get usage data for a specific date"""
    date_str = target_date.strftime("%Y-%m-%d")
    url = f"{URL_BASE}/usage/v2/{contract_id}?ba={account_id}&interval=hourly&from={date_str}&to={date_str}"
    headers = {"x-api-key": API_KEY, "session": token}
    
    print(f"\n📊 Fetching usage data for {date_str}...")
    print(f"   URL: {url}")
    
    async with session.post(url, headers=headers) as resp:
        print(f"   Status: {resp.status}")
        
        if resp.status == 200:
            data = await resp.json()
            
            # Save sample response
            filename = f"/tmp/usage_{date_str}.json"
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            print(f"   ✅ Response saved to {filename}")
            
            if isinstance(data, list):
                print(f"   📦 Received {len(data)} hourly data points")
                
                if len(data) > 0:
                    # Show first data point as sample
                    sample = data[0]
                    print(f"\n   Sample data point:")
                    print(f"     Date: {sample.get('date')}")
                    print(f"     Value (kWh): {sample.get('value')}")
                    print(f"     Dollar Value: {sample.get('dollarValue')}")
                    print(f"     Offpeak Value: {sample.get('offpeakValue')}")
                    print(f"     Currency: {sample.get('currency')}")
                    
                    # Calculate totals
                    total_kwh = sum(float(p.get('value', 0)) for p in data)
                    total_cost = sum(float(p.get('dollarValue', 0)) for p in data)
                    paid_kwh = sum(float(p.get('value', 0)) for p in data if str(p.get('offpeakValue', '0.00')) == '0.00')
                    free_kwh = sum(float(p.get('value', 0)) for p in data if str(p.get('offpeakValue', '0.00')) != '0.00')
                    
                    print(f"\n   📈 Daily Totals:")
                    print(f"     Total Usage: {total_kwh:.2f} kWh")
                    print(f"     Total Cost: ${total_cost:.2f}")
                    print(f"     Paid Usage: {paid_kwh:.2f} kWh")
                    print(f"     Free Usage: {free_kwh:.2f} kWh")
                
                return data
            else:
                print(f"   ⚠️  Unexpected response format: {type(data)}")
                return None
        else:
            text = await resp.text()
            print(f"   ❌ Failed: {resp.status} - {text}")
            return None


async def main():
    """Main test function"""
    print("=" * 60)
    print("Contact Energy API Test")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Login
        token = await login(session)
        if not token:
            print("\n❌ Cannot proceed without valid token")
            return
        
        # Step 2: Get account details
        account_id, contracts = await get_account_details(session, token)
        if not account_id or not contracts:
            print("\n❌ Cannot proceed without account details")
            return
        
        # Use first contract for testing
        contract = contracts[0]
        contract_id = contract.get("id")
        icp = contract.get("icp")
        
        print(f"\n🎯 Testing with Contract ID: {contract_id}, ICP: {icp}")
        
        # Step 3: Test usage data for multiple dates
        test_dates = [
            datetime.now().date() - timedelta(days=1),  # Yesterday
            datetime.now().date() - timedelta(days=7),  # 1 week ago
            datetime.now().date() - timedelta(days=30), # 1 month ago
        ]
        
        for test_date in test_dates:
            await get_usage_data(session, token, account_id, contract_id, test_date)
            await asyncio.sleep(0.5)  # Be nice to API
        
        print("\n" + "=" * 60)
        print("✅ Test completed!")
        print("=" * 60)
        print("\nReview the saved JSON files in /tmp/ for detailed API responses:")
        print("  - /tmp/account_details.json")
        print("  - /tmp/usage_*.json")


if __name__ == "__main__":
    asyncio.run(main())

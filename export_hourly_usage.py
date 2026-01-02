#!/usr/bin/env python3
"""
Export hourly usage (paid and free/unpaid) for the last 10 days to .hourly_data.md.

Notes:
- Uses the Contact Energy HTTP API directly (no Home Assistant context required).
- Dependencies: requests (pip install requests)
- Credentials and API key are embedded per user request. Do not commit this script with credentials in a shared repo.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from typing import Any, Dict, List

import requests

BASE_URL = "https://api.contact-digital-prod.net"
API_KEY = "kbIthASA7e1M3NmpMdGrn2Yqe0yHcCjL4QNPSUij"
EMAIL = "mike.and.elspeth@gmail.com"
PASSWORD = "##maGellan8021##"
OUTPUT_FILE = ".hourly_data.md"
DAY_WINDOW = 10  # last 10 days (inclusive of today)


def _auth_headers(token: str | None = None) -> Dict[str, str]:
    headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
    if token:
        headers.update({"session": token, "authorization": token})
    return headers


def authenticate() -> Dict[str, str]:
    resp = requests.post(
        f"{BASE_URL}/login/v2",
        headers=_auth_headers(),
        json={"username": EMAIL, "password": PASSWORD},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("token")
    if not token:
        raise RuntimeError("No token received from auth")
    return {"token": token, "segment": data.get("segment"), "bp": data.get("bp")}


def fetch_accounts(token: str) -> Dict[str, Any]:
    resp = requests.get(
        f"{BASE_URL}/accounts/v2",
        headers=_auth_headers(token),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def pick_account_contract(accounts: Dict[str, Any]) -> tuple[str, str]:
    summaries = accounts.get("accountsSummary") or []
    if not summaries:
        raise RuntimeError("No accountsSummary returned")
    account = summaries[0]
    account_id = account.get("id")
    contracts = account.get("contracts") or []
    if not account_id or not contracts:
        raise RuntimeError("Missing account_id or contracts in account summary")
    contract_id = contracts[0].get("contractId") or contracts[0].get("id")
    if not contract_id:
        raise RuntimeError("No contractId found in first contract")
    return account_id, contract_id


def fetch_usage(token: str, account_id: str, contract_id: str, start: dt.date, end: dt.date) -> List[Dict[str, Any]]:
    from urllib.parse import urlencode
    params = {
        "ba": account_id,
        "interval": "hourly",
        "from": start.strftime("%Y-%m-%d"),
        "to": end.strftime("%Y-%m-%d"),
    }
    query_string = urlencode(params)
    url = f"{BASE_URL}/usage/v2/{contract_id}?{query_string}"
    resp = requests.post(url, headers=_auth_headers(token), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        return data.get("usage", []) or []
    if isinstance(data, list):
        return data
    raise RuntimeError(f"Unexpected usage response type: {type(data)}")


def parse_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    parsed: List[Dict[str, Any]] = []
    for rec in records:
        try:
            ts = rec.get("date") or rec.get("timestamp")
            total = float(rec.get("value", 0) or 0)
            offpeak = float(rec.get("offpeakValue", 0) or 0)
            uncharged = float(rec.get("unchargedValue", 0) or 0)
            free = offpeak + uncharged
            paid = max(total - free, 0)
            parsed.append(
                {
                    "timestamp": ts,
                    "total_kwh": total,
                    "paid_kwh": paid,
                    "free_kwh": free,
                }
            )
        except Exception:
            # Skip malformed records but continue parsing the rest
            continue
    parsed.sort(key=lambda r: r.get("timestamp", ""))
    return parsed


def write_markdown(records: List[Dict[str, Any]], start: dt.date, end: dt.date) -> None:
    lines = []
    lines.append(f"# Hourly Usage (Last 10 Days)\n")
    lines.append(f"Range: {start} to {end}\n")
    lines.append(f"Total records: {len(records)}\n")
    lines.append("")
    lines.append("| Timestamp | Paid kWh | Free kWh | Total kWh |")
    lines.append("|---|---:|---:|---:|")
    for rec in records:
        lines.append(
            f"| {rec['timestamp']} | {rec['paid_kwh']:.3f} | {rec['free_kwh']:.3f} | {rec['total_kwh']:.3f} |"
        )
    content = "\n".join(lines) + "\n"
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def main() -> None:
    # Dynamic date range: last 10 days (today - 10 to today)
    today = dt.date.today()
    start = today - dt.timedelta(days=10)
    end = today

    auth = authenticate()
    token = auth["token"]
    accounts = fetch_accounts(token)
    account_id, contract_id = pick_account_contract(accounts)
    
    # Fetch in 1-day chunks (10 separate requests)
    all_usage = []
    current = start
    while current <= end:
        print(f"Fetching {current}...")
        usage = fetch_usage(token, account_id, contract_id, current, current)
        all_usage.extend(usage)
        current = current + dt.timedelta(days=1)
    
    parsed = parse_records(all_usage)
    write_markdown(parsed, start, end)
    print(f"Wrote {len(parsed)} records to {OUTPUT_FILE} for {account_id}/{contract_id}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

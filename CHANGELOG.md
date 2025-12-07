# Changelog

## 0.0.1

### Changes

#### Assets
  - Updated ApexCharts card configuration examples
  - Modified 4 asset files

#### Documentation
  - Added comprehensive ApexCharts Card Examples section
  - Added documentation for multiple properties and accounts support
  - Documented sensor naming with ICP suffixes for multi-instance setups

#### Visual Assets
  - Updated integration screenshots and visual assets

#### Metadata
  - Added cloud_polling IoT class designation


All notable changes to this project will be documented in this file.

## [0.0.1] - 2025-12-07

### Complete API Research and Documentation

This release represents a comprehensive reset and research phase for the Contact Energy Home Assistant integration. The entire repository was archived (tag: archive-full-repo-0.6.2) and rebuilt from scratch with a focus on understanding and documenting the available API capabilities.

#### Research Objectives
- Identify all available data points from the Contact Energy API
- Compare library-based vs direct API access
- Document working and non-working endpoints
- Establish foundation for reliable integration development

#### Testing Methodology

**1. Library Analysis**
- Installed and tested `contact-energy-nz` library (v0.1.18621115660)
- Examined source code to understand API interaction patterns
- Identified authentication flow and required headers
- Discovered library bugs and limitations

**2. Direct API Exploration**
- Created comprehensive endpoint testing script (`.explore-api.py`)
- Tested 100+ potential endpoint variations
- Validated authentication mechanisms
- Mapped complete API surface area

**3. Comparative Validation**
- Created focused testing script (`.test-usage-endpoint.py`)
- Verified working endpoints with real data
- Compared library results vs direct API responses
- Documented data structure and field availability

#### Key Findings

**✅ Working Endpoints (3 total):**
1. `POST /login/v2` - Authentication (returns session token)
2. `GET /accounts/v2?ba=` - Complete account information
3. `POST /usage/v2/{contract_id}` - Usage data (hourly/daily/monthly intervals)

**❌ Non-Working Endpoints:**
- All other tested variations (billing, invoices, payments, contracts, etc.) return 403 Forbidden
- API has very limited public surface area
- Only 3 endpoints provide customer data access

**📊 Available Data Points:**

*Account Information (19 data points):*
- Account ID, nickname, contract ID, premise ID
- Service address, ICP number
- Payment method, billing frequency
- Current balance, amount due, payment due date
- Next bill date, days until overdue
- Product/plan name, contract status
- Account type flags (direct debit, prepay, etc.)

*Usage Data (10 data points per interval):*
- Energy consumption (kWh)
- Cost (NZD)
- Off-peak usage and costs
- Free/uncharged usage
- Date/time with timezone
- Percentage indicators

#### Library Issues Discovered

**Critical Bugs:**
1. `account_summary()` - Returns None (parsing bug)
2. `get_latest_usage()` - Date handling issue causes failures
3. Missing data exposure - Library retrieves account data but doesn't expose most fields

**Missing Features:**
- Daily usage interval not exposed
- Account balance information not accessible
- Invoice details not exposed
- Contract information not available

#### Results and Recommendations

**✅ Recommended Approach: Use Direct API Calls**

**Reasons:**
1. **Complete Data Access** - Direct API provides all 19 account data points vs library's limited exposure
2. **Reliability** - Avoid library bugs (account_summary returns None)
3. **Flexibility** - Access to daily usage interval not available in library
4. **Control** - Better error handling and token management
5. **Maintainability** - No dependency on third-party library bug fixes

**Authentication Pattern:**
```
POST /login/v2 with x-api-key header
→ Receive token
→ Use token in both "session" and "authorization" headers
```

**Update Frequency Recommendations:**
- Account data: Every 6 hours (slow-changing)
- Daily/monthly usage: Every 1-4 hours  
- Hourly usage: Every 30-60 minutes

**Error Handling:**
- 401/403: Re-authenticate
- 500: Exponential backoff retry
- Store token and re-use until failure

#### Documentation Added

**Wiki Pages:**
- **API Data Reference** - Complete endpoint documentation with:
  - Request/response examples
  - All available data fields
  - Library vs direct API comparison
  - Testing script with credential prompts
  - Integration recommendations

**Repository Files:**
- `.API-COMPREHENSIVE.md` - Full API documentation
- `.explore-api.py` - Comprehensive endpoint testing script
- `.test-usage-endpoint.py` - Focused validation script
- `.API-data.md` - Library testing results

#### Development Status

**Completed:**
- ✅ API research and endpoint mapping
- ✅ Data availability documentation
- ✅ Library evaluation and bug identification
- ✅ Direct API validation
- ✅ Wiki documentation

**Next Steps:**
- Implement API client with direct HTTP calls
- Create coordinator for data management
- Build sensor entities for account and usage data
- Implement configuration flow
- Add historical data as sensor attributes
- Create proper error handling and re-authentication

#### Technical Notes

- API Base URL: `https://api.contact-digital-prod.net`
- API Key: Embedded in library (public)
- Authentication: Token-based with dual header requirement
- Timezone: Pacific/Auckland (NZ)
- Currency: NZD
- Usage Unit: kWh
- Date Format: YYYY-MM-DD

#### Files Structure

```
custom_components/contact_energy/
├── __init__.py          (placeholder)
├── manifest.json        (v0.0.1)
├── const.py            (placeholder)
├── config_flow.py      (placeholder)
├── coordinator.py      (placeholder)
├── sensor.py           (placeholder)
├── api.py              (placeholder)
└── strings.json        (placeholder)
```

**Note:** This release contains research and documentation only. Implementation of the working integration will follow in subsequent releases.

---

### Summary

Version 0.0.1 establishes the foundation for a reliable Contact Energy integration by:
- Documenting all available API capabilities
- Identifying the optimal implementation approach (direct API vs library)
- Creating comprehensive testing and validation scripts
- Providing clear recommendations for development

The research confirms that a fully-featured integration is possible with access to 19 account data points and comprehensive usage data across hourly, daily, and monthly intervals.



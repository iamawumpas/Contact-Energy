# FAQ & Limitations

Frequently asked questions and known limitations of the Contact Energy integration.

## General Questions

### Is this an official integration?

No, this is an unofficial custom integration. It is not affiliated with or endorsed by Contact Energy Limited. Use at your own risk.

### Does it work with prepay meters?

Yes, the integration works with prepay accounts. It includes sensors for prepay debt balance and prepay status.

### Which plans are supported?

All Contact Energy plans are supported, including:
- Standard plans
- Good Nights
- Prepay
- Broadband bundles
- Fixed-term contracts

The integration retrieves account information regardless of your plan type.

### Can I monitor business accounts?

Yes, if you have business accounts with Contact Energy, you can monitor them the same way as residential accounts. Use your business account credentials during setup.

### How much does it cost?

The integration is completely free and open-source. There are no subscription fees or charges.

---

## Data & Updates

### How often does data update?

**Once every 24 hours**, scheduled closest to 01:00 AM.

This is intentional to minimize API load and respect Contact Energy's systems. The data doesn't change frequently enough to warrant more frequent updates.

### Can I force a manual update?

Yes! Use the **`contact_energy.refresh_data`** service to manually trigger an immediate data refresh:

**Method 1: Developer Tools**
1. Go to Developer Tools → Actions
2. Select action: `contact_energy.refresh_data`
3. Click "Perform Action"

**Method 2: Automation/Script**
```yaml
service: contact_energy.refresh_data
```

**Method 3: Button Card**
```yaml
type: button
name: Refresh Contact Energy
tap_action:
  action: call-service
  service: contact_energy.refresh_data
icon: mdi:refresh
```

This service bypasses the normal 24-hour sync interval and forces immediate download of both account data and usage data.

You can also reload the integration:
- Settings → Integrations → Contact Energy → three dots → Reload

### Why is there a delay in usage data?

⚠️ **Usage sensors not yet implemented**

Contact Energy provides usage data with a 24-72 hour delay. This is normal and applies to:
- Their website
- Their mobile app
- This integration

This is not a limitation of the integration but of Contact Energy's data processing.

### Is the data real-time?

No. Account and billing data is updated by Contact Energy periodically. The integration retrieves the same data you would see on Contact Energy's website.

### What time zone is used?

All dates and times are in **New Zealand Standard Time (NZST) / New Zealand Daylight Time (NZDT)**, matching Contact Energy's systems.

---

## Features & Limitations

### What data is available?

Currently available (24 sensors):
- ✅ Account balance and refund information
- ✅ Billing and invoice details
- ✅ Payment due dates and countdowns
- ✅ Next bill predictions
- ✅ Contract and product information
- ✅ Account settings and preferences
- ✅ Payment plan indicators

Not yet implemented:
- ❌ Detailed usage data (daily/hourly/monthly kWh)
- ❌ Cost breakdown
- ❌ Rate information (peak/off-peak)
- ❌ Free hours tracking
- ❌ Historical usage trends
- ❌ Real-time usage monitoring

### Will usage sensors be added?

Usage sensors are planned for future releases but require additional API endpoint implementation. The Contact Energy API supports usage data, but it requires:
- Separate API calls per time period
- Historical data processing
- Rate calculation logic

These features are on the roadmap but not yet implemented.

### Can I see hourly usage?

⚠️ Not yet implemented. Hourly usage sensors are planned for a future release.

### Can I track free hours?

⚠️ Not yet implemented. Free hours data is available in the API but not yet exposed as sensors.

### Does it work with solar panels?

The integration retrieves account information regardless of whether you have solar panels. However:
- ✅ Account balance reflects any solar credits
- ❌ Solar generation data is not available (Contact Energy doesn't provide this via their API)

### Can I make payments through Home Assistant?

**No.** This integration is read-only. You cannot:
- Make payments
- Change account settings
- Update payment methods
- Modify contracts

All account management must be done through Contact Energy's website or app.

---

## Troubleshooting

### Sensors show "Unknown" or "Unavailable"

**Common causes:**

1. **Just installed** - Wait for first scheduled update (01:00 AM) or restart Home Assistant
2. **No data available** - Some sensors may not have data depending on your account type
3. **API error** - Check Home Assistant logs: Settings → System → Logs
4. **Authentication failed** - Token may have expired, try reloading the integration

**Solutions:**
- Wait for next automatic update
- Restart Home Assistant
- Reload the integration
- Check logs for specific errors

### Authentication Errors

**Error:** "Invalid credentials" or "Authentication failed"

**Solutions:**
1. Verify email and password are correct
2. Try logging into [Contact Energy's website](https://www.contact.co.nz/)
3. Check for account suspension or issues
4. Remove and re-add the integration
5. Clear any special characters from password if possible

### Token Expired Errors

**Error:** API returns 401 or "Token expired"

**Solution:**
The integration should automatically refresh expired tokens. If it doesn't:
1. Reload the integration (Settings → Integrations → Contact Energy → Reload)
2. If problem persists, remove and re-add the integration
3. Ensure your password is still stored (check integration configuration)

### No Accounts Found During Setup

**Error:** "No accounts found for this email"

**Possible causes:**
1. Email address doesn't have any active contracts
2. All accounts already configured (duplicates prevented)
3. API temporarily unavailable

**Solutions:**
- Verify you have active contracts on Contact Energy's website
- Check if accounts are already added (Settings → Devices & Services)
- Wait a few minutes and try again

### Integration Won't Load

**Error:** Integration fails to load or shows errors in logs

**Solutions:**
1. Check Home Assistant logs for specific errors
2. Verify Home Assistant version is 2023.1 or later
3. Ensure `contact_energy` folder is in `custom_components`
4. Restart Home Assistant
5. Reinstall the integration

### Duplicate Entity IDs

**Error:** "Entity ID already exists"

**Cause:** This shouldn't normally happen as each property has unique ICP

**Solution:**
- Check if you accidentally added the same account twice
- Remove duplicate integrations (Settings → Devices & Services)
- Restart Home Assistant

### Multiple Accounts Not Showing

**Problem:** Only one property shows during setup, but I have multiple

**Solutions:**
- Verify all properties are under the same Contact Energy login
- Check that all properties have active contracts
- Try removing and re-adding the integration
- Contact Contact Energy to verify account structure

---

## Technical Questions

### How does authentication work?

1. You provide email and password during setup
2. Integration authenticates with Contact Energy API
3. Receives authentication token and segment ID
4. Token is stored securely in Home Assistant
5. Token is automatically refreshed when needed
6. Password is stored to enable token refresh

### Is my password secure?

Yes. Your credentials are:
- Stored encrypted in Home Assistant's configuration
- Never transmitted to third parties
- Only used to authenticate with Contact Energy's official API
- Stored locally on your Home Assistant instance

### What API does it use?

The integration uses Contact Energy's official REST API:
- Base URL: `https://api.contact-digital-prod.net`
- Authentication: Token-based
- Endpoints: `/accounts/v2`, `/invoices/v2`, etc.

This is the same API used by Contact Energy's website and mobile app.

### Will this affect my Contact Energy account?

No. The integration is **read-only** and cannot:
- Make changes to your account
- Process payments
- Modify settings
- Delete data

It only retrieves information, similar to viewing your account on Contact Energy's website.

### How many API requests does it make?

Approximately **1 request per 24 hours** per configured account.

This is very light usage and should not impact Contact Energy's systems or your account in any way.

### Can Contact Energy detect this?

The integration uses their official API with standard authentication. From Contact Energy's perspective, it looks like you're using their website or app.

However, you are responsible for complying with Contact Energy's terms of service.

### Will it work if I move house?

If you move and transfer your Contact Energy account to a new address:
- The ICP will change
- You'll need to reconfigure the integration
- Remove the old property and add the new one

### What if Contact Energy changes their API?

If Contact Energy makes breaking changes to their API, the integration may stop working until updated. This is a risk with any unofficial integration.

- Watch the [GitHub repository](https://github.com/iamawumpas/Contact-Energy) for updates
- Report issues if the integration stops working
- Community updates will be provided as needed

---

## Privacy & Security

### What data is collected?

The integration only stores:
- Your email address
- Your password (encrypted)
- Authentication tokens
- Account configuration (ICP, address, account ID)

**No data is sent to third parties.** Everything stays on your Home Assistant instance.

### Can others see my data?

Only if they have access to your Home Assistant instance. Follow Home Assistant security best practices:
- Use strong passwords
- Enable two-factor authentication
- Don't expose Home Assistant to the internet without proper security
- Regularly update Home Assistant

### Is it GDPR compliant?

The integration processes your personal data locally on your Home Assistant instance. No data is sent to external servers except Contact Energy's official API for authentication and data retrieval.

---

## Contributing

### I found a bug!

Please [open an issue on GitHub](https://github.com/iamawumpas/Contact-Energy/issues) with:
- Description of the problem
- Steps to reproduce
- Home Assistant version
- Integration version
- Relevant logs (remove personal information)

### I have a feature request!

Feature requests are welcome! [Open an issue on GitHub](https://github.com/iamawumpas/Contact-Energy/issues) and describe:
- What feature you'd like
- Why it would be useful
- How you envision it working

### Can I contribute code?

Yes! Contributions are welcome:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## Still Need Help?

- Check the [Getting Started](Getting-Started) guide
- Review the [Sensors Reference](Sensors)
- Search [existing GitHub issues](https://github.com/iamawumpas/Contact-Energy/issues)
- [Open a new issue](https://github.com/iamawumpas/Contact-Energy/issues/new) if your problem isn't covered

---

**Disclaimer:** This integration is provided as-is with no warranties. It works for the developer's Home Assistant setup and is shared freely for community use. Contact Energy may change their API at any time, potentially breaking functionality.

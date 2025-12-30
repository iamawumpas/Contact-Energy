# Changelog

All notable changes to the Contact Energy integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [ 1.1.0 ]

### Added
- Account information sensor platform with 10 new sensors
- Current Account Balance sensor (NZD)
- Prepay Debt Balance sensor (NZD)
- Amount Due sensor (NZD)
- Amount Paid sensor (NZD)
- Payment Due Date sensor
- Days Until Overdue sensor
- Next Bill Date sensor
- Days Until Next Bill sensor
- Refund Eligible sensor
- Maximum Refund sensor
- Correspondence Preference sensor
- Payment Method sensor
- Billing Frequency sensor
- Data coordinator for efficient API usage (updates once per day at ~01:00 AM)
- Sensors follow naming pattern: sensor.{account_name}.{attribute_name}

## [ 1.0.0 ]

### Added
- Initial stable authentication and configuration flow established
- Full Contact Energy API integration with secure token-based authentication
- Multi-account and multi-ICP support with duplicate prevention
- Single and multiple account configuration handling
- Automatic account discovery and filtering
- Comprehensive error handling with user-friendly messages
- Account nickname and ICP display in configuration dialogs
- Previous email reuse option for seamless multi-account setup
- Release automation with changelog extraction

## [ 0.0.6 ]

### Fixed
- Config entry title now uses account nickname as fallback when address is not available from API
- Multiple account selection now displays account nickname if address field is missing
- Improved handling of incomplete address data from Contact Energy API

## [ 0.0.5 ]

### Fixed
- Single account confirmation dialog no longer displays as multi-account selection
- Form field for single account confirmation now uses proper text input instead of radio button
- Account ICP label changed from "Confirm" to "Account ICP" for clarity
- Single account form now properly defaults to the account ICP value

## [ 0.0.4 ]

### Fixed
- Account nickname display in single account confirmation dialog
- Description placeholders now properly show account name and ICP number
- Confirmation form field label for single account selection

### Changed
- Improved single account confirmation dialog UI with clearer account information display
- Updated form title to "Confirm Account" for better clarity

## [ 0.0.3 ]

### Added
- Single account confirmation dialog showing account nickname and ICP
- Multiple account selection with radio button list (ICP - Address format)
- Automatic filtering of already-configured accounts from selection list
- Smart credential handling with previous email reuse option
- Detection and prevention of duplicate account additions
- Detailed user instructions for each configuration scenario

### Changed
- Enhanced config flow to handle single vs. multiple accounts
- Improved account selection display with ICP and address
- Better error message for when all accounts are already configured
- Credential form now offers choice to reuse previous email or enter new credentials
- Config entry title now shows ICP and address for easy identification

### Fixed
- Incorrect ICP and address display in account selection (was showing contract ID instead of ICP)
- Account filtering logic to properly identify already-configured accounts

## [ 0.0.2 ]

### Added
- Complete authentication flow with Contact Energy API
- Multi-step configuration process with credential validation
- Automatic account discovery and ICP detection
- Account selection for users with multiple ICPs/accounts
- Secure credential handling and token-based authentication
- Comprehensive error handling with user-friendly messages
- New API client module for Contact Energy communication
- Detailed user instructions in English translation files

### Changed
- Enhanced config flow with two-step process (credentials, then account selection)
- Improved error messages with specific guidance for users
- Updated strings.json with new configuration step definitions

## [ 0.0.1 ]

### Added
- Initial release of Contact Energy integration for Home Assistant
- Configuration flow for setting up Contact Energy account credentials
- Support for Contact Energy API integration
- HACS installation support
- Basic Home Assistant integration structure with config entries

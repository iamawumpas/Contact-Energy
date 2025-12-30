# Changelog

All notable changes to the Contact Energy integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

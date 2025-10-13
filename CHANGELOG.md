# Changelog

## 0.1.10


**Note**: This release includes uncommitted changes from the working directory.


## 0.1.9


**Note**: This release includes uncommitted changes from the working directory.


## 0.1.8


**Note**: This release includes uncommitted changes from the working directory.


## 0.1.7

### Changes

• Updated config flow validation schema and UI selectors

### Modified Files:
• custom_components/contact_energy/config_flow.py

### Commits

• fix(config_flow): add explicit handler registration decorator for HA discovery (71e7c63)


## 0.1.6

### Changes

• Updated config flow validation schema and UI selectors
• Enhanced error handling and user-friendly error messages

### Modified Files:
• custom_components/contact_energy/config_flow.py

### Commits

• debug: add logging to trace config flow module loading (aab8572)
• fix(config_flow): use canonical ConfigFlow class name and add selector compatibility fallback (bd2545d)


## 0.1.5

### Changes

• Updated config flow validation schema and UI selectors
• Enhanced error handling and user-friendly error messages

### Modified Files:
• custom_components/contact_energy/config_flow.py

### Commits

• fix(config_flow): register handler correctly and move validation into class; set domain attribute (1fc037d)


## 0.1.4

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/const.py
• custom_components/contact_energy/manifest.json
• hacs.json

### Commits

• Release 0.1.4 (ea72b75)
• chore: rebuild changelog and release notes (1e234a0)


## 0.1.3

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/const.py
• custom_components/contact_energy/manifest.json
• hacs.json

### Commits

• Release 0.1.3 (6aff2eb)
• chore: rebuild changelog and release notes (3e659b8)


## 0.1.2

### Changes

• Fixed critical config flow registration bug (changed DOMAIN class attribute to domain)
• Removed duplicate import statements in config flow
• Enhanced error handling and user-friendly error messages
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/config_flow.py
• custom_components/contact_energy/manifest.json
• hacs.json

### Commits

• Release 0.1.2 (80a5e4e)
• chore: rebuild changelog and release notes (2825f9e)


## 0.1.1

### Changes

• Updated config flow validation schema and UI selectors
• Enhanced error handling and user-friendly error messages
• Implemented working Contact Energy usage data endpoint
• Added custom exception classes for better error handling
• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Implemented 8-hour polling DataUpdateCoordinator
• Enhanced integration setup and unload procedures
• Implemented proper coordinator and platform initialization
• Updated user interface strings and translations
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/__init__.py
• custom_components/contact_energy/api.py
• custom_components/contact_energy/config_flow.py
• custom_components/contact_energy/const.py
• custom_components/contact_energy/coordinator.py
• custom_components/contact_energy/manifest.json
• custom_components/contact_energy/sensor.py
• custom_components/contact_energy/strings.json
• custom_components/contact_energy/translations/en.json
• hacs.json

### Commits

• Release 0.1.1 (2e974b5)
• docs: improve 0.1.0 changelog with milestone details (a6c2caa)


## 0.1.0

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/manifest.json
• hacs.json

### Commits

• Release 0.1.0 (ffa2ee3)


## 0.0.4

### Changes

• Added retry logic and exponential backoff for API requests
• Updated authentication headers and session management
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/api.py
• custom_components/contact_energy/manifest.json
• hacs.json

### Commits

• Release 0.0.4 (b7ace34)
• chore: rebuild changelog and release notes (4610db2)


## 0.0.3

### Changes

• Removed duplicate import statements in config flow
• Updated config flow validation schema and UI selectors
• Enhanced error handling and user-friendly error messages
• Added retry logic and exponential backoff for API requests
• Updated authentication headers and session management
• Added custom exception classes for better error handling
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/api.py
• custom_components/contact_energy/config_flow.py
• custom_components/contact_energy/manifest.json
• hacs.json

### Commits

• Release 0.0.3 (d6aae04)


## 0.0.2

### Changes

• Updated config flow validation schema and UI selectors
• Added retry logic and exponential backoff for API requests
• Updated authentication headers and session management
• Added custom exception classes for better error handling
• Enhanced integration setup and unload procedures
• Implemented proper coordinator and platform initialization
• Updated user interface strings and translations
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/__init__.py
• custom_components/contact_energy/api.py
• custom_components/contact_energy/config_flow.py
• custom_components/contact_energy/const.py
• custom_components/contact_energy/manifest.json
• custom_components/contact_energy/strings.json
• custom_components/contact_energy/translations/en.json
• hacs.json

### Commits

• Release 0.0.2 (eae721b)


## 0.0.1

### Changes

• Updated user interface strings and translations
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Added Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/__init__.py
• custom_components/contact_energy/api.py
• custom_components/contact_energy/config_flow.py
• custom_components/contact_energy/const.py
• custom_components/contact_energy/coordinator.py
• custom_components/contact_energy/manifest.json
• custom_components/contact_energy/sensor.py
• custom_components/contact_energy/services.yaml
• custom_components/contact_energy/strings.json
• custom_components/contact_energy/translations/en.json
• hacs.json

### Commits

• Release 0.0.1 (3739439)
• Initial commit (cef2939)



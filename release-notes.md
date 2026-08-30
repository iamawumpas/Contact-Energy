## [ 2.0.3 ]

### Fixed
- Fixed the Home Assistant long-term statistics metadata for cumulative energy totals so newer Core versions do not raise the deprecated/invalid `mean_type` warning when importing external statistics.
- Removed the explicit mean metadata for sum-only energy statistics and kept the metadata aligned with the current HA statistics contract.

### Changed
- Kept the external energy statistics metadata focused on the valid `has_sum` / `has_mean` semantics required by the current Home Assistant recorder API.
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-03

### Added
- **Core Over Arithmetic (`cricket_nrr.overs`)**: Exact Fraction-backed over object representation (`Over`) supporting standard operators (`+`, `-`, `*`, `/`, Comparisons) and base-6 conversion.
- **Validation Constraints (`cricket_nrr.validators`)**: Rejection of invalid cricket inputs (e.g. `19.6`, `19.7`, negative scores/wickets).
- **Match Records & Innings Models (`cricket_nrr.models`)**: Dataclasses for inputs representing match results.
- **ICC-Compliant NRR Calculations (`cricket_nrr.nrr`)**: Automated calculation including:
  - Bowled-out maximum over denominator rule.
  - DLS revised overs and target adjustment rules.
  - Super-over exclusion rule.
  - Abandoned / no-result match exclusion rule.
- **Duckworth-Lewis-Stern Standard Engine (`cricket_nrr.dls`)**: Fully loaded 51×10 resource percentage table with bilinear interpolation, target calculations, and par score estimation.
- **Tournament Standings Engine (`cricket_nrr.standings`)**:
  - Live sortable points table formatting.
  - Live what-if NRR solver (`whatif_nrr`).
  - Qualification margin details solver (`qualify_margin`).
- **Flexible Loaders (`cricket_nrr.loaders`)**: Support for IPL match sheets (`from_csv`), Cricsheet data formats (`from_cricsheet_csv`, `from_cricsheet_json`), and raw list of dicts.
- **Testing Suite**: 100 passing unit and integration tests covering overs, DLS, NRR, and Tournament standings.

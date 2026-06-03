# cricket-nrr

[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://pypi.org/project/cricket-nrr/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests Status](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)
[![Dependency Status](https://img.shields.io/badge/dependencies-zero%20(stdlib)-success)](pyproject.toml)

A robust, production-ready Python package for cricket analytics. It calculates **exact cricket over arithmetic**, **ICC-compliant Net Run Rates (NRR)**, **Duckworth-Lewis-Stern (DLS)** par scores/revised targets, and **tournament standings** with what-if predictors and qualification margin solvers.

Designed for developers, analysts, and sports enthusiasts, `cricket-nrr` has **zero external dependencies** (pure Python standard library), though it integrates seamlessly with `pandas` if available.

---

## Key Features

1. **Exact Cricket Over Arithmetic (`cricket_nrr.overs`)**
   - Native Python floats break under cricket base-6 decimal notation (e.g. `14.3 + 0.4` is not `14.7` but `15.1`).
   - Automatically validates over notation (rejecting inputs like `19.6` or `19.7`).
   - Uses `fractions.Fraction` internally for exact fraction math (e.g. `19.3` overs is represented as exactly `117/6` overs).
   - Full operator overloading for intuitive arithmetic: `Over("19.3") + Over("0.4") == Over("20.1")`.

2. **ICC-Compliant NRR Calculator (`cricket_nrr.nrr`)**
   - **The All-Out Rule**: If a team is bowled out, their full over quota (e.g. `20` or `50` overs) is automatically used as the denominator instead of the actual overs faced.
   - **DLS Match Rule**: In rain-curtailed matches, the team batting second has their target and overs quota adjusted to the revised target and overs allotment, and the team batting first has their score adjusted to the DLS par score for those revised overs.
   - **Super-Over Exclusion**: Super-overs are strictly excluded from NRR calculations.
   - **No-Result Exclusion**: Abandoned/no-result matches are excluded.
   - **Cumulative NRR Aggregation**: Automatically aggregates runs and overs across matches *first*, and then divides, instead of averaging per-match NRR values.

3. **DLS Standard Edition Engine (`cricket_nrr.dls`)**
   - Implements the complete **51×10 Duckworth-Lewis-Stern (DLS) Standard Edition resource table** (covering 0 to 50 overs left, and 0 to 9 wickets lost).
   - Supports 2-dimensional interpolation for fractional overs.
   - Calculates **revised targets** and **par scores** for both between-innings and mid-innings interruptions (using standard ICC $G_{50}$ constants).
   - Zero-dependency logic with optional vectorised pandas integrations for high-performance match simulation.

4. **Standings Tables & Qualification Predictors (`cricket_nrr.standings`)**
   - Renders formatted tournament standings tables sorted by points, NRR, and wins.
   - **What-If Predictor**: Solves equations to answer queries like:
     - *"If we score 195 batting first, what is the maximum we can concede to hit an NRR of +0.000?"*
     - *"If the opponent scores 170, what is the minimum runs we must score to exceed +0.300 NRR?"*
   - **Qualification Margin Solver**: Checks if a final group match qualifies a team ahead of their closest rival, detailing the points margin, NRR margin, or the NRR gap shortfall.

5. **Universal Data Loaders (`cricket_nrr.loaders`)**
   - Out-of-the-box support for:
     - **IPL 2026/matches.csv** schema
     - **Cricsheet** ball-by-ball CSV data
     - **Cricsheet** JSON data structures
     - Standard Python dict list representations

---

## Installation

```bash
# Pure python installation (Zero dependencies)
pip install cricket-nrr

# Optional: Install with pandas support
pip install "cricket-nrr[pandas]"
```

---

## Quick Start

### 1. Cricket Over Arithmetic
```python
from cricket_nrr import Over, InvalidOverError

# Parse overs from strings, floats, ints, or balls
o1 = Over("19.3")
o2 = Over(0.4)
print(o1 + o2)         # Output: Over("20.1") (20 overs and 1 ball)
print((o1 + o2).balls) # Output: 121

# Subtracting and comparing overs
diff = Over("50.0") - Over("48.2")
print(diff)            # Output: Over("1.4")
assert Over("20.0") > Over("19.5")

# Invalid overs raise custom error
try:
    Over("19.6")
except InvalidOverError as e:
    print(e)           # Output: Invalid over notation: '19.6' (extra balls must be between 0 and 5)
```

### 2. Match & Cumulative Tournament NRR
```python
from cricket_nrr import Tournament
from cricket_nrr.loaders import from_dict

# Load matches from dict representation
matches = from_dict([
    {
        "match_id": "1", "team1": "RCB", "team2": "CSK",
        "innings1": {"runs": 218, "overs": "20.0", "wickets": 5, "all_out": False},
        "innings2": {"runs": 191, "overs": "20.0", "wickets": 7, "all_out": False},
        "result": "team1", "max_overs": 20,
    },
    {
        "match_id": "2", "team1": "RCB", "team2": "MI",
        "innings1": {"runs": 140, "overs": "15.2", "wickets": 10, "all_out": True}, # Bowled out!
        "innings2": {"runs": 143, "overs": "14.1", "wickets": 3, "all_out": False},
        "result": "team2", "max_overs": 20,
    }
])

# NRR respects the 'All Out' rule: RCB's batting overs for match 2 count as full 20.0.
t = Tournament(matches)
table = t.standings()

for row in table:
    print(f"{row.team:<5} | Pts: {row.points} | NRR: {row.nrr_str()}")
# Output:
# CSK   | Pts: 0 | NRR: -1.350
# RCB   | Pts: 2 | NRR: +0.243
# MI    | Pts: 2 | NRR: +2.188
```

### 3. DLS Target and Par Scores
```python
from cricket_nrr import DLSEngine, Over

# Match interrupted in 1st Innings:
# Match starts as a 50-over match.
# In the 1st innings, after 35 overs (score 180/3), play is stopped by rain and overs reduced to 42 overs per side.
engine = DLSEngine(g50=244)
par, revised_target = engine.calculate_target_mid_innings(
    team1_score_before=180,
    overs_played_before=Over("35.0"),
    wickets_lost_before=3,
    overs_curtailed_to=Over("42.0"),
    max_overs_initial=Over("50.0")
)

print(f"Revised Target for Team 2: {revised_target} runs in 42.0 overs")
# Output: Revised Target for Team 2: 219 runs in 42.0 overs
```

### 4. Standings What-If Predictor
```python
# Check how a team can qualify or achieve a certain NRR in their final match
# Let's say RCB wants to know the conceding threshold to keep their NRR above +0.500:
result = t.whatif_nrr(
    team="RCB",
    batting_first=True,
    runs_scored=185,
    overs_batted=Over("20.0"),
    all_out=False,
    max_overs=Over("20.0"),
    target_nrr=0.500,
)

print(result.scenario)
# Output: "RCB scored 185 in 20.0 overs (not all out). To achieve NRR +0.500, they must concede AT MOST 141 runs in 20.0 overs."
print(f"Is achievable? {result.achievable}")  # Output: True
```

---

## Integration with pandas

If `pandas` is installed, you can effortlessly export standings tables to dataframes:

```python
import pandas as pd
from cricket_nrr import Tournament

# Build tournament
t = Tournament(matches)

# Export standings to DataFrame
df = t.to_dataframe()
print(df[["Team", "Played", "Won", "Points", "NRR"]])
```

---

## Directory Structure

```
cricket-nrr/
├── cricket_nrr/            # Main package source
│   ├── loaders/            # CSV, Cricsheet, JSON data loaders
│   ├── dls.py              # Duckworth-Lewis-Stern Engine
│   ├── formatters.py       # Helper functions to print scores & NRR
│   ├── models.py           # Match and Innings data structures
│   ├── nrr.py              # ICC Net Run Rate calculator
│   ├── overs.py            # Cricket Over representation and arithmetic
│   ├── standings.py        # Tournament standings and predictors
│   └── validators.py       # Input boundaries validation
├── examples/               # Example usage scripts
├── tests/                  # Complete test suite (pytest)
├── pyproject.toml          # Package installation & metadata
└── README.md               # User manual
```

---

## Testing

The package has 100% test coverage for math, validation, and ICC regulations. To run tests:

```bash
# Install development dependencies
pip install "cricket-nrr[dev]"

# Run tests
python -m pytest
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

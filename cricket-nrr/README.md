# cricket-nrr

This python library handles the arithmetic and rules needed for cricket data analysis. It covers overs calculations, net run rate calculations, and Duckworth-Lewis-Stern par scores. 

## The Problem with Cricket Math

Cricket calculations have some unusual rules that make them difficult to program. 

First, overs are recorded in a base-6 decimal format. Writing 14.3 overs means 14 overs and 3 balls. If you try to add 14.3 and 0.4 using standard python floats, you get 14.7 instead of 15.1. This library resolves that by parsing notation into exact fractions using the standard library fractions module. It also rejects invalid inputs like 19.6 or 19.7 because an over cannot have six or seven extra balls.

Second, net run rate is not a simple average. If a team is bowled out, their net run rate is calculated using the full quota of overs they were supposed to face. For example, if a team is bowled out in 15.2 overs of a 20 over match, you must divide their runs by 20.0, not 15.2. Super overs are excluded. Abandoned matches must be ignored. If a match is shortened by rain, you have to use the revised targets and revised overs to calculate the rates.

Third, Duckworth-Lewis-Stern targets require two-dimensional interpolation across a resource percentage table.

This library handles all of these rules.

## Installation

Install the package directly from PyPI.

```bash
pip install cricket-nrr
```

If you use pandas for analysis, you can install the optional dependency.

```bash
pip install "cricket-nrr[pandas]"
```

## Usage

Here are some examples of what the library does.

### Over Arithmetic

You can parse, add, subtract, and compare overs. The library handles the base-6 carrying automatically.

```python
from cricket_nrr import Over

# You can initialize using strings, floats, or integers
o1 = Over("19.3")
o2 = Over(0.4)
total = o1 + o2
print(total) # Prints 20.1
print(total.balls) # Prints 121

# Subtracting overs
remaining = Over("50.0") - Over("48.2")
print(remaining) # Prints 1.4
```

The library raises a custom error if you try to create an invalid over like `19.6`.

### Net Run Rate Calculations

To calculate tournament standings, you need to aggregate runs and overs across multiple matches. The library does this using the official rules.

```python
from cricket_nrr import Tournament
from cricket_nrr.loaders import from_dict

# Load matches from a list of dictionaries
matches = from_dict([
    {
        "match_id": "1", "team1": "RCB", "team2": "CSK",
        "innings1": {"runs": 218, "overs": "20.0", "wickets": 5, "all_out": False},
        "innings2": {"runs": 191, "overs": "20.0", "wickets": 7, "all_out": False},
        "result": "team1", "max_overs": 20,
    },
    {
        "match_id": "2", "team1": "RCB", "team2": "MI",
        "innings1": {"runs": 140, "overs": "15.2", "wickets": 10, "all_out": True},
        "innings2": {"runs": 143, "overs": "14.1", "wickets": 3, "all_out": False},
        "result": "team2", "max_overs": 20,
    }
])

t = Tournament(matches)
for row in t.standings():
    print(f"{row.team}: NRR = {row.nrr_str()} (Points: {row.points})")
```

### Duckworth-Lewis-Stern Par Scores

The library contains the standard edition resource table. It calculates revised targets for rain-affected games.

```python
from cricket_nrr import DLSEngine, Over

# If play is stopped during the first innings of a 50 over match
# After 35 overs the score is 180 for 3, and the match is reduced to 42 overs per side
engine = DLSEngine(g50=244)
par, revised_target = engine.calculate_target_mid_innings(
    team1_score_before=180,
    overs_played_before=Over("35.0"),
    wickets_lost_before=3,
    overs_curtailed_to=Over("42.0"),
    max_overs_initial=Over("50.0")
)

print(f"Revised Target: {revised_target} runs in 42.0 overs")
```

### Qualification Margin Finder

You can calculate the exact boundary conditions needed for a team to qualify. This answers what-if questions for upcoming matches.

```python
# Calculate what Mumbai Indians need in their final match to reach a target NRR of 0.000
result = t.whatif_nrr(
    team="Mumbai Indians",
    batting_first=True,
    runs_scored=195,
    overs_batted=Over("20.0"),
    all_out=False,
    max_overs=Over("20.0"),
    target_nrr=0.0,
)

print(result.scenario)
```

## Directory Structure

```
cricket-nrr/
├── cricket_nrr/
│   ├── loaders/
│   ├── dls.py
│   ├── formatters.py
│   ├── models.py
│   ├── nrr.py
│   ├── overs.py
│   ├── standings.py
│   └── validators.py
├── examples/
├── tests/
├── pyproject.toml
└── README.md
```

## License

This project is licensed under the MIT License.

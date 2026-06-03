"""
examples/nrr_whatif.py
~~~~~~~~~~~~~~~~~~~~~~~~
Demonstrate the live NRR what-if predictor.

Scenario: "Mumbai Indians are at -0.200 NRR before their last match.
           They score 195 batting first. What is the MAXIMUM they can
           concede to push their NRR above +0.000?"

Usage
-----
    python examples/nrr_whatif.py
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from cricket_nrr import Tournament, Over
from cricket_nrr.loaders import from_csv

MATCHES_CSV = Path(__file__).parent.parent.parent / "matches.csv"

if not MATCHES_CSV.exists():
    print(f"ERROR: matches.csv not found at {MATCHES_CSV}")
    sys.exit(1)

matches = from_csv(str(MATCHES_CSV))
t = Tournament(matches)

# ── Current standings ──────────────────────────────────────────────────────
table = {s.team: s for s in t.standings()}
for team_name, row in table.items():
    if "Mumbai" in team_name:
        print(f"Current NRR for {team_name}: {row.nrr_str()}")
        print(f"  Runs for:     {row.runs_for} in {float(row.overs_for):.2f} overs")
        print(f"  Runs against: {row.runs_against} in {float(row.overs_against):.2f} overs")
        print()
        break

# ── What-If: batting first, scored 195, target NRR = +0.000 ───────────────
result = t.whatif_nrr(
    "Mumbai Indians",
    batting_first=True,
    runs_scored=195,
    overs_batted=Over("20.0"),
    all_out=False,
    max_overs=Over("20.0"),
    target_nrr=0.0,
)

print("=" * 60)
print("WHAT-IF SCENARIO")
print("=" * 60)
print(result.scenario)
print()
print(f"  Current NRR before match : {result.current_nrr:+.3f}")
print(f"  Target NRR               : {result.target_nrr:+.3f}")
if result.max_concede is not None:
    print(f"  Max runs to concede      : {result.max_concede}")
print(f"  Projected NRR (at limit) : {result.projected_nrr:+.3f}")
print(f"  Achievable?              : {'Yes' if result.achievable else 'No'}")
print()

# ── What-If: bowling first, chasing scenario ───────────────────────────────
result2 = t.whatif_nrr(
    "Mumbai Indians",
    batting_first=False,
    runs_scored=170,   # opposition scored 170
    overs_batted=Over("20.0"),
    all_out=False,
    max_overs=Over("20.0"),
    target_nrr=0.300,
)

print("=" * 60)
print("WHAT-IF SCENARIO (BOWLING FIRST)")
print("=" * 60)
print(result2.scenario)
print()
print(f"  Min runs to score        : {result2.min_score}")
print(f"  Projected NRR (at limit) : {result2.projected_nrr:+.3f}")

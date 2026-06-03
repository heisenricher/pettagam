"""
examples/ipl2026_standings.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Print the full IPL 2026 tournament standings from matches.csv.

Usage
-----
    python examples/ipl2026_standings.py

Expected output (approximate — NRR depends on exact all-out flags):
    Pos  Team                           P   W   L   T  NR  Pts    NRR
     1   Royal Challengers Bengaluru   14  10   3   0   1   21  +0.XXX
    ...
"""

from pathlib import Path
import sys

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from cricket_nrr import Tournament
from cricket_nrr.loaders import from_csv

# ── Load data ─────────────────────────────────────────────────────────────
MATCHES_CSV = Path(__file__).parent.parent.parent / "matches.csv"

if not MATCHES_CSV.exists():
    print(f"ERROR: matches.csv not found at {MATCHES_CSV}")
    sys.exit(1)

matches = from_csv(str(MATCHES_CSV))
print(f"Loaded {len(matches)} matches.\n")

# ── Build standings ────────────────────────────────────────────────────────
t = Tournament(matches)
table = t.standings()

# ── Print table ────────────────────────────────────────────────────────────
header = (
    f"{'Pos':>3}  {'Team':<35}  {'P':>2}  {'W':>2}  {'L':>2}  {'T':>2}  "
    f"{'NR':>2}  {'Pts':>3}  {'NRR':>8}  "
    f"{'For':>12}  {'Against':>12}"
)
print(header)
print("-" * len(header))

for pos, row in enumerate(table, start=1):
    runs_for_str = f"{row.runs_for}/{float(row.overs_for):.1f}"
    runs_against_str = f"{row.runs_against}/{float(row.overs_against):.1f}"
    print(
        f"{pos:>3}  {row.team:<35}  {row.played:>2}  {row.won:>2}  {row.lost:>2}  "
        f"{row.tied:>2}  {row.no_result:>2}  {row.points:>3}  "
        f"{row.nrr_str():>8}  {runs_for_str:>12}  {runs_against_str:>12}"
    )

print()
print(f"Total valid NRR matches: {sum(1 for m in matches if m.result != 'no_result')}")
print(f"No-result matches excluded: {sum(1 for m in matches if m.result == 'no_result')}")

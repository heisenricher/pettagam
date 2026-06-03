"""
cricket_nrr
~~~~~~~~~~~
Cricket NRR, DLS par scores, and tournament standings — done correctly.

Quick start
-----------
>>> from cricket_nrr import Over, DLSEngine, Tournament
>>> from cricket_nrr.loaders import from_csv

# ── Over arithmetic ───────────────────────────────────────────────────
>>> Over("19.3") + Over("0.4")
Over('20.1')
>>> Over(19.6)   # raises InvalidOverError

# ── DLS par score ─────────────────────────────────────────────────────
>>> engine = DLSEngine(g50=245.0)
>>> engine.par_score(
...     team1_score=250, team1_overs_faced=Over("50.0"),
...     team1_max_overs=Over("50.0"), team1_wickets_lost=8,
...     team2_overs_available=Over("25.0"),
... )
182

# ── IPL 2026 standings ────────────────────────────────────────────────
>>> matches = from_csv("matches.csv")
>>> t = Tournament(matches)
>>> for row in t.standings():
...     print(row.team, row.points, row.nrr_str())

# ── What-if NRR predictor ─────────────────────────────────────────────
>>> result = t.whatif_nrr(
...     "Mumbai Indians", batting_first=True,
...     runs_scored=180, overs_batted=Over("20.0"),
...     all_out=False, max_overs=Over("20.0"),
...     target_nrr=0.500,
... )
>>> print(result)
"""

from .overs import Over
from .validators import InvalidOverError, InvalidWicketError, InvalidRunsError
from .models import InningsRecord, MatchRecord
from .nrr import MatchNRR, TeamNRRPool
from .dls import DLSEngine
from .standings import Tournament, TeamStanding, WhatIfResult, QualifyResult
from .formatters import format_nrr, format_over, format_score, nrr_series, over_series

__version__ = "0.1.0"
__author__ = "cricket-nrr contributors"

__all__ = [
    # Core type
    "Over",
    # Exceptions
    "InvalidOverError",
    "InvalidWicketError",
    "InvalidRunsError",
    # Data models
    "InningsRecord",
    "MatchRecord",
    # NRR engine
    "MatchNRR",
    "TeamNRRPool",
    # DLS engine
    "DLSEngine",
    # Tournament engine
    "Tournament",
    "TeamStanding",
    "WhatIfResult",
    "QualifyResult",
    # Formatters
    "format_nrr",
    "format_over",
    "format_score",
    "nrr_series",
    "over_series",
    # Version
    "__version__",
]

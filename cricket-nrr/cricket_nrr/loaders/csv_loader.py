"""
cricket_nrr.loaders.csv_loader
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Parse ``matches.csv`` (summary-level) into :class:`~cricket_nrr.MatchRecord` objects.

This loader is tuned to the exact schema of the IPL 2026 dataset:

    match_number, date, venue, team1, team2, toss_winner, toss_decision,
    winner, margin, team1_score, team2_score, team1_wickets, team2_wickets,
    team1_overs, team2_overs

Key handling:
- ``winner == "No Result"`` → ``result="no_result"``
- ``team*_wickets == 10``   → ``all_out=True``  (ICC all-out rule)
- ``team*_overs``            → parsed via :class:`~cricket_nrr.Over` (validated)
- Matches with 0 overs (no ball bowled) → ``result="no_result"``
"""

from __future__ import annotations

import csv
import datetime
from pathlib import Path
from typing import List, Optional, Union

from ..models import InningsRecord, MatchRecord
from ..overs import Over

__all__ = ["from_csv"]

# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------


def from_csv(
    path: Union[str, Path],
    *,
    format: str = "T20",
    max_overs: Over = Over(20.0),
    encoding: str = "utf-8-sig",
) -> List[MatchRecord]:
    """
    Load a summary-level matches CSV into a list of :class:`MatchRecord`.

    Parameters
    ----------
    path : str or Path
        Path to the CSV file (e.g. ``"matches.csv"``).
    format : str
        Match format — ``"T20"`` or ``"ODI"`` (default ``"T20"``).
    max_overs : Over
        Full over quota (default ``Over(20.0)`` for T20,
        use ``Over(50.0)`` for ODI).
    encoding : str
        File encoding (default ``"utf-8-sig"`` handles BOM from Excel).

    Returns
    -------
    list of MatchRecord

    Examples
    --------
    >>> from cricket_nrr.loaders import from_csv
    >>> matches = from_csv("matches.csv")
    >>> len(matches)
    75
    """
    path = Path(path)
    records: List[MatchRecord] = []

    with path.open(encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rec = _parse_row(row, format=format, max_overs=max_overs)
            if rec is not None:
                records.append(rec)

    return records


# ---------------------------------------------------------------------------
# Row parser
# ---------------------------------------------------------------------------


def _parse_row(
    row: dict,
    *,
    format: str,
    max_overs: Over,
) -> Optional[MatchRecord]:
    """Parse one CSV row into a :class:`MatchRecord`."""

    match_id = row.get("match_number", row.get("match_id", "?")).strip()
    date_str = row.get("date", "").strip()
    try:
        date = datetime.date.fromisoformat(date_str)
    except ValueError:
        date = datetime.date.today()

    team1 = row["team1"].strip()
    team2 = row["team2"].strip()
    venue = row.get("venue", "").strip()

    winner_raw = row.get("winner", "").strip()

    # ── Determine result ──────────────────────────────────────────────
    if winner_raw.lower() in ("no result", "no_result", ""):
        result: str = "no_result"
    elif winner_raw == team1:
        result = "team1"
    elif winner_raw == team2:
        result = "team2"
    else:
        result = "no_result"  # safety fallback

    # ── Parse scores and overs ────────────────────────────────────────
    t1_runs = _int(row.get("team1_score", "0"))
    t2_runs = _int(row.get("team2_score", "0"))
    t1_wkts = _int(row.get("team1_wickets", "0"))
    t2_wkts = _int(row.get("team2_wickets", "0"))

    t1_overs_raw = row.get("team1_overs", "0.0").strip() or "0.0"
    t2_overs_raw = row.get("team2_overs", "0.0").strip() or "0.0"

    # If no ball was bowled (0.0 overs for both), force no_result
    if t1_overs_raw in ("0.0", "0") and t2_overs_raw in ("0.0", "0"):
        result = "no_result"

    t1_overs = Over(t1_overs_raw)
    t2_overs = Over(t2_overs_raw)

    t1_all_out = (t1_wkts == 10)
    t2_all_out = (t2_wkts == 10)

    # ── Detect DLS (both sides play reduced overs AND it's a valid result) ──
    # Heuristic: if both innings have the same reduced over count and
    # neither team faced the full quota, it may be DLS.  The caller can
    # also pass a pre-annotated CSV with a "dls" column.
    dls_flag = row.get("dls", "").strip().lower() in ("1", "true", "yes")

    innings1 = InningsRecord(
        runs=t1_runs,
        overs_faced=t1_overs,
        wickets_lost=min(t1_wkts, 10),
        all_out=t1_all_out,
        max_overs=max_overs,
        dls_reduced=dls_flag,
    )
    innings2 = InningsRecord(
        runs=t2_runs,
        overs_faced=t2_overs,
        wickets_lost=min(t2_wkts, 10),
        all_out=t2_all_out,
        max_overs=max_overs,
        dls_reduced=dls_flag,
    )

    return MatchRecord(
        match_id=match_id,
        date=date,
        team1=team1,
        team2=team2,
        innings1=innings1,
        innings2=innings2,
        result=result,  # type: ignore[arg-type]
        dls_affected=dls_flag,
        format=format,  # type: ignore[arg-type]
        venue=venue,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _int(value: str) -> int:
    """Safe integer parse — returns 0 on failure."""
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return 0

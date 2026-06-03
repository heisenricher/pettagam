"""
cricket_nrr.loaders.cricsheet_loader
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Parse Cricsheet ball-by-ball CSV files into :class:`~cricket_nrr.MatchRecord`.

Supports the exact schema used in ``match_74_gt_vs_rcb_final.csv``:

    match_id, season, start_date, venue, innings, ball, batting_team,
    bowling_team, striker, non_striker, bowler, runs_off_bat, extras,
    wides, noballs, byes, legbyes, penalty, wicket_type,
    player_dismissed, other_wicket_type, other_player_dismissed, team_score

Also supports the standard Cricsheet JSON format.
"""

from __future__ import annotations

import csv
import datetime
import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..models import InningsRecord, MatchRecord
from ..overs import Over

__all__ = ["from_cricsheet_csv", "from_cricsheet_json"]


# ---------------------------------------------------------------------------
# Ball-by-ball CSV loader
# ---------------------------------------------------------------------------


def from_cricsheet_csv(
    path: Union[str, Path],
    *,
    format: str = "T20",
    max_overs: Over = Over(20.0),
    encoding: str = "utf-8-sig",
) -> MatchRecord:
    """
    Parse a Cricsheet-format ball-by-ball CSV into a :class:`MatchRecord`.

    Parameters
    ----------
    path : str or Path
        Path to the ball-by-ball CSV.
    format : str
        ``"T20"`` or ``"ODI"`` (default ``"T20"``).
    max_overs : Over
        Full over quota (default ``Over(20.0)``).
    encoding : str
        File encoding (default ``"utf-8-sig"``).

    Returns
    -------
    MatchRecord

    Examples
    --------
    >>> from cricket_nrr.loaders import from_cricsheet_csv
    >>> m = from_cricsheet_csv("match_74_gt_vs_rcb_final.csv")
    >>> m.team1
    'Gujarat Titans'
    >>> m.innings1.runs
    155
    """
    path = Path(path)

    # Accumulate per-innings data
    innings_data: Dict[int, _InningsAccum] = defaultdict(lambda: _InningsAccum())
    meta: Dict[str, Any] = {}

    with path.open(encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            inn_num = int(row["innings"])
            ball_notation = row["ball"].strip()
            acc = innings_data[inn_num]

            # Populate metadata from the first row
            if not meta:
                meta["match_id"] = row.get("match_id", "?").strip()
                meta["date"] = row.get("start_date", "").strip()
                meta["venue"] = row.get("venue", "").strip()

            # Track teams
            if acc.batting_team is None:
                acc.batting_team = row["batting_team"].strip()
                acc.bowling_team = row["bowling_team"].strip()

            # Count legal deliveries (exclude wides and no-balls for over count)
            is_wide = bool(row.get("wides", "").strip())
            is_noball = bool(row.get("noballs", "").strip())
            is_extra_delivery = is_wide or is_noball

            # Runs (runs off bat + all extras)
            runs_bat = _int(row.get("runs_off_bat", "0"))
            extras = _int(row.get("extras", "0"))
            acc.total_runs += runs_bat + extras

            # Legal ball count (overs)
            if not is_extra_delivery:
                acc.legal_balls += 1

            # Wickets — non-empty wicket_type means a dismissal
            wicket_type = row.get("wicket_type", "").strip()
            if wicket_type:
                acc.wickets += 1

    # Build InningsRecord objects
    innings_list = sorted(innings_data.items())  # sort by innings number

    if len(innings_list) < 2:
        raise ValueError(
            f"Expected at least 2 innings in {path}, found {len(innings_list)}."
        )

    # team1 = team that batted in innings 1
    inn1_num, inn1_acc = innings_list[0]
    inn2_num, inn2_acc = innings_list[1]

    team1 = inn1_acc.batting_team or "Team 1"
    team2 = inn2_acc.batting_team or "Team 2"

    t1_all_out = inn1_acc.wickets == 10
    t2_all_out = inn2_acc.wickets == 10

    innings1 = InningsRecord(
        runs=inn1_acc.total_runs,
        overs_faced=Over.from_balls(inn1_acc.legal_balls),
        wickets_lost=inn1_acc.wickets,
        all_out=t1_all_out,
        max_overs=max_overs,
    )
    innings2 = InningsRecord(
        runs=inn2_acc.total_runs,
        overs_faced=Over.from_balls(inn2_acc.legal_balls),
        wickets_lost=inn2_acc.wickets,
        all_out=t2_all_out,
        max_overs=max_overs,
    )

    # Determine result from scores
    if innings2.runs > innings1.runs:
        result = "team2"
    elif innings1.runs > innings2.runs:
        result = "team1"
    else:
        result = "tie"

    try:
        date = datetime.date.fromisoformat(meta.get("date", ""))
    except ValueError:
        date = datetime.date.today()

    return MatchRecord(
        match_id=meta.get("match_id", "?"),
        date=date,
        team1=team1,
        team2=team2,
        innings1=innings1,
        innings2=innings2,
        result=result,  # type: ignore[arg-type]
        format=format,  # type: ignore[arg-type]
        venue=meta.get("venue", ""),
    )


# ---------------------------------------------------------------------------
# Cricsheet JSON loader
# ---------------------------------------------------------------------------


def from_cricsheet_json(
    path: Union[str, Path],
    *,
    encoding: str = "utf-8",
) -> MatchRecord:
    """
    Parse a standard Cricsheet JSON file into a :class:`MatchRecord`.

    Cricsheet JSON format reference: https://cricsheet.org/format/json/

    Parameters
    ----------
    path : str or Path
        Path to the ``.json`` file from Cricsheet.
    encoding : str
        File encoding (default ``"utf-8"``).

    Returns
    -------
    MatchRecord
    """
    path = Path(path)
    with path.open(encoding=encoding) as fh:
        data = json.load(fh)

    info = data.get("info", {})
    innings_raw = data.get("innings", [])

    # Meta
    match_id = str(path.stem)
    dates = info.get("dates", [])
    date = datetime.date.fromisoformat(dates[0]) if dates else datetime.date.today()
    venue = info.get("venue", "")
    format_raw = info.get("match_type", "T20").upper()
    format_str = format_raw if format_raw in ("T20", "ODI", "TEST") else "T20"
    max_overs_val = info.get("overs", 20)
    max_overs = Over(int(max_overs_val))

    # Parse innings
    parsed: List[InningsRecord] = []
    team_names: List[str] = []

    for inn in innings_raw[:2]:
        batting_team = inn.get("team", "")
        team_names.append(batting_team)
        total_runs = 0
        legal_balls = 0
        wickets = 0

        for over_data in inn.get("overs", []):
            for delivery in over_data.get("deliveries", []):
                runs = delivery.get("runs", {})
                total_runs += runs.get("total", 0)

                extras = delivery.get("extras", {})
                is_wide = "wides" in extras
                is_noball = "noballs" in extras

                if not (is_wide or is_noball):
                    legal_balls += 1

                if "wickets" in delivery:
                    wickets += len(delivery["wickets"])

        all_out = wickets == 10
        parsed.append(InningsRecord(
            runs=total_runs,
            overs_faced=Over.from_balls(legal_balls),
            wickets_lost=min(wickets, 10),
            all_out=all_out,
            max_overs=max_overs,
        ))

    if len(parsed) < 2:
        raise ValueError(f"Expected 2 innings in {path}, found {len(parsed)}.")

    team1 = team_names[0]
    team2 = team_names[1]
    inn1, inn2 = parsed[0], parsed[1]

    if inn2.runs > inn1.runs:
        result = "team2"
    elif inn1.runs > inn2.runs:
        result = "team1"
    else:
        result = "tie"

    return MatchRecord(
        match_id=match_id,
        date=date,
        team1=team1,
        team2=team2,
        innings1=inn1,
        innings2=inn2,
        result=result,  # type: ignore[arg-type]
        format=format_str,  # type: ignore[arg-type]
        venue=venue,
    )


# ---------------------------------------------------------------------------
# Internal accumulator
# ---------------------------------------------------------------------------


class _InningsAccum:
    """Mutable accumulator for one innings during CSV parsing."""

    __slots__ = ("batting_team", "bowling_team", "total_runs", "legal_balls", "wickets")

    def __init__(self) -> None:
        self.batting_team: Optional[str] = None
        self.bowling_team: Optional[str] = None
        self.total_runs: int = 0
        self.legal_balls: int = 0
        self.wickets: int = 0


def _int(value: str) -> int:
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return 0

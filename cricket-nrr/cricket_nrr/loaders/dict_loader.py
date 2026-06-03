"""
cricket_nrr.loaders.dict_loader
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Construct :class:`~cricket_nrr.MatchRecord` directly from Python dicts.

Minimal API — no file I/O needed for one-off calculations.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict

from ..models import InningsRecord, MatchRecord
from ..overs import Over

__all__ = ["from_dict"]


def from_dict(data: Dict[str, Any]) -> MatchRecord:
    """
    Build a :class:`MatchRecord` from a plain Python dictionary.

    Parameters
    ----------
    data : dict
        Must contain the following keys::

            {
                "match_id": "001",           # str
                "team1":    "India",          # str
                "team2":    "Australia",      # str
                "innings1": {
                    "runs":       287,        # int
                    "overs":      "50.0",     # str | float | int
                    "wickets":    6,          # int
                    "all_out":    False,      # bool
                },
                "innings2": {
                    "runs":       230,
                    "overs":      "48.4",
                    "wickets":    10,
                    "all_out":    True,
                },
                "result":    "team1",         # "team1"|"team2"|"tie"|"no_result"
                "max_overs": 50,              # int | float | str  (default 20)
            }

        Optional keys:

        - ``"date"``              : ISO date string (default: today)
        - ``"format"``            : ``"T20"`` | ``"ODI"`` (default: ``"T20"``)
        - ``"venue"``             : str (default: ``""``)
        - ``"super_over_played"`` : bool (default: ``False``)
        - ``"dls_affected"``      : bool (default: ``False``)

    Returns
    -------
    MatchRecord

    Examples
    --------
    >>> from cricket_nrr.loaders import from_dict
    >>> m = from_dict({
    ...     "match_id": "001",
    ...     "team1": "India",
    ...     "team2": "Australia",
    ...     "innings1": {"runs": 287, "overs": "50.0", "wickets": 6, "all_out": False},
    ...     "innings2": {"runs": 230, "overs": "48.4", "wickets": 10, "all_out": True},
    ...     "result": "team1",
    ...     "max_overs": 50,
    ... })
    >>> m.innings2.nrr_overs
    Fraction(25, 1)   # 50.0 overs (all-out rule applied)
    """
    max_overs = Over(data.get("max_overs", 20))

    date_raw = data.get("date")
    if date_raw:
        date = datetime.date.fromisoformat(str(date_raw))
    else:
        date = datetime.date.today()

    innings1 = _parse_innings(data["innings1"], max_overs)
    innings2 = _parse_innings(data["innings2"], max_overs)

    return MatchRecord(
        match_id=str(data.get("match_id", "?")),
        date=date,
        team1=str(data["team1"]),
        team2=str(data["team2"]),
        innings1=innings1,
        innings2=innings2,
        result=data["result"],  # type: ignore[arg-type]
        super_over_played=bool(data.get("super_over_played", False)),
        dls_affected=bool(data.get("dls_affected", False)),
        format=data.get("format", "T20"),  # type: ignore[arg-type]
        venue=str(data.get("venue", "")),
    )


def _parse_innings(inn: Dict[str, Any], max_overs: Over) -> InningsRecord:
    return InningsRecord(
        runs=int(inn["runs"]),
        overs_faced=Over(inn["overs"]),
        wickets_lost=int(inn["wickets"]),
        all_out=bool(inn.get("all_out", int(inn["wickets"]) == 10)),
        max_overs=max_overs,
        dls_reduced=bool(inn.get("dls_reduced", False)),
        dls_revised_target=inn.get("dls_revised_target"),
    )

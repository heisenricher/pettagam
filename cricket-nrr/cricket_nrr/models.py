"""
cricket_nrr.models
~~~~~~~~~~~~~~~~~~
Shared, immutable data structures used across all cricket_nrr modules.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal, Optional

from .overs import Over

__all__ = ["InningsRecord", "MatchRecord"]


@dataclass(frozen=True)
class InningsRecord:
    """
    A single innings in a cricket match.

    Parameters
    ----------
    runs : int
        Total runs scored in this innings.
    overs_faced : Over
        Overs actually batted (e.g., ``Over("19.4")``).
    wickets_lost : int
        Number of wickets that fell (0–10).
    all_out : bool
        ``True`` if all 10 wickets fell.  When ``True``, the **full**
        ``max_overs`` is used as the NRR denominator (ICC "all-out" rule).
    max_overs : Over
        Maximum overs available (``Over(20.0)`` for T20, ``Over(50.0)`` for ODI).
    dls_reduced : bool
        ``True`` if this innings was rain-curtailed and DLS applied.
    dls_revised_target : int or None
        The DLS target set for this innings, if applicable.
    """

    runs: int
    overs_faced: Over
    wickets_lost: int
    all_out: bool
    max_overs: Over
    dls_reduced: bool = False
    dls_revised_target: Optional[int] = None

    def __post_init__(self) -> None:
        from .validators import validate_wickets, validate_runs
        validate_runs(self.runs, field="InningsRecord.runs")
        validate_wickets(self.wickets_lost, field="InningsRecord.wickets_lost")

    # ------------------------------------------------------------------
    # NRR-relevant accessors
    # ------------------------------------------------------------------

    @property
    def nrr_overs(self) -> Fraction:
        """
        Exact over count to use as the NRR denominator.

        Applies the ICC "all-out" rule automatically:
        - ``all_out=True`` → use ``max_overs`` (e.g. 20.0)
        - ``all_out=False`` → use ``overs_faced``
        """
        if self.all_out:
            return self.max_overs.as_fraction
        return self.overs_faced.as_fraction

    @property
    def run_rate(self) -> Fraction:
        """
        Runs per over using the NRR-correct denominator.

        Example — team bowled out for 127 in 19.4 overs, T20:
        >>> InningsRecord(127, Over("19.4"), 10, True, Over("20.0")).run_rate
        Fraction(127, 20)   # 127 / 20.0 = 6.35 rpo
        """
        denom = self.nrr_overs
        if denom == 0:
            return Fraction(0)
        return Fraction(self.runs) / denom


@dataclass(frozen=True)
class MatchRecord:
    """
    A complete cricket match with both innings and metadata.

    Parameters
    ----------
    match_id : str
        Unique identifier (e.g. ``"13"`` or ``"ipl_2026_013"``).
    date : datetime.date
        Match date.
    team1 : str
        Team that batted first.
    team2 : str
        Team that batted second.
    innings1 : InningsRecord
        Team 1's batting innings.
    innings2 : InningsRecord
        Team 2's batting innings.
    result : str
        ``"team1"`` | ``"team2"`` | ``"tie"`` | ``"no_result"``.
    super_over_played : bool
        If ``True``, the super-over result is excluded from NRR.
        The innings fields must contain only regulation-innings data.
    dls_affected : bool
        ``True`` if the match was rain-affected and DLS applied.
    dls_team1_overs_credited : Over or None
        For DLS matches: overs credited to Team 1 for NRR purposes
        (= overs actually bowled to Team 2).  ``None`` for normal matches.
    format : str
        ``"T20"`` | ``"ODI"`` | ``"Test"`` | ``"Hundred"``.
    venue : str
        Stadium name.
    """

    match_id: str
    date: datetime.date
    team1: str
    team2: str
    innings1: InningsRecord
    innings2: InningsRecord
    result: Literal["team1", "team2", "tie", "no_result"]
    super_over_played: bool = False
    dls_affected: bool = False
    dls_team1_overs_credited: Optional[Over] = None
    format: Literal["T20", "ODI", "Test", "Hundred"] = "T20"
    venue: str = ""

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def include_in_nrr(self) -> bool:
        """``False`` for no-result / abandoned matches."""
        return self.result != "no_result"

    @property
    def winner(self) -> Optional[str]:
        """Team name of the winner, or ``None`` for tie / no-result."""
        if self.result == "team1":
            return self.team1
        if self.result == "team2":
            return self.team2
        return None

    @property
    def teams(self) -> "tuple[str, str]":
        """``(team1, team2)`` tuple."""
        return (self.team1, self.team2)

    def innings_for(self, team: str) -> InningsRecord:
        """Return the batting innings for *team*."""
        if team == self.team1:
            return self.innings1
        if team == self.team2:
            return self.innings2
        raise ValueError(
            f"Team {team!r} did not play in match {self.match_id!r}."
        )

    def innings_against(self, team: str) -> InningsRecord:
        """Return the opponent's batting innings (bowling side of *team*)."""
        if team == self.team1:
            return self.innings2
        if team == self.team2:
            return self.innings1
        raise ValueError(
            f"Team {team!r} did not play in match {self.match_id!r}."
        )

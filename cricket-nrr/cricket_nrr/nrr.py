"""
cricket_nrr.nrr
~~~~~~~~~~~~~~~
Match-level and tournament-level Net Run Rate (NRR) calculator.

Implements all official ICC NRR rules:

1. **All-out rule** — if a team is bowled out, their full quota of overs
   is used as the NRR denominator, not the overs they actually faced.
2. **Super-over exclusion** — super-over runs/overs are never counted.
3. **No-result exclusion** — abandoned / no-result matches are excluded.
4. **DLS overs credit** — for rain-affected matches, Team 1's NRR overs
   equals the overs actually bowled to Team 2 (not their own innings).
5. **Exact arithmetic** — all over division uses :class:`~fractions.Fraction`
   to eliminate floating-point drift.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Iterable

from .models import InningsRecord, MatchRecord
from .overs import Over

__all__ = ["MatchNRR", "TeamNRRPool"]


class MatchNRR:
    """
    Net Run Rate contribution from a single cricket match.

    Parameters
    ----------
    match : MatchRecord
        The match to compute NRR for.

    Examples
    --------
    >>> from cricket_nrr import MatchRecord, InningsRecord, Over, MatchNRR
    >>> inn1 = InningsRecord(201, Over("20.0"), 9, False, Over("20.0"))
    >>> inn2 = InningsRecord(203, Over("15.4"), 4, False, Over("20.0"))
    >>> m = MatchRecord("1", ..., "SRH", "RCB", inn1, inn2, "team2")
    >>> nrr = MatchNRR(m)
    >>> nrr.is_valid_for_nrr()
    True
    """

    def __init__(self, match: MatchRecord) -> None:
        self._match = match

    # ------------------------------------------------------------------
    # Validity check
    # ------------------------------------------------------------------

    def is_valid_for_nrr(self) -> bool:
        """
        ``False`` for:
        - No-result / abandoned matches  (``result == "no_result"``)
        - Matches where a super over was played (the super over itself is
          already excluded by the innings fields, but the flag signals
          that the tournament engine should be aware).

        Note: super-over *matches* (where regulation innings ended in a tie)
        *do* count toward NRR — only the super-over overs/runs are excluded.
        """
        return self._match.include_in_nrr

    # ------------------------------------------------------------------
    # Team 1 NRR contributions
    # ------------------------------------------------------------------

    @property
    def team1_runs_for(self) -> int:
        """Runs scored by Team 1 in their batting innings."""
        return self._match.innings1.runs

    @property
    def team1_overs_for(self) -> Fraction:
        """
        Overs used as NRR denominator for Team 1's batting.

        Applies the **all-out rule** (ICC rule 1) and the
        **DLS overs-credit rule** (ICC rule 4).
        """
        if self._match.dls_affected and self._match.dls_team1_overs_credited is not None:
            # Rule 4: use overs actually bowled to Team 2, not Team 1's innings length
            return self._match.dls_team1_overs_credited.as_fraction
        return self._match.innings1.nrr_overs

    @property
    def team1_runs_against(self) -> int:
        """Runs conceded by Team 1 (= Team 2's batting total)."""
        return self._match.innings2.runs

    @property
    def team1_overs_against(self) -> Fraction:
        """Overs used as NRR denominator for Team 1's bowling (Team 2's batting)."""
        return self._match.innings2.nrr_overs

    def team1_match_nrr(self) -> float:
        """NRR for Team 1 in this individual match (for display only)."""
        if not self.is_valid_for_nrr():
            return 0.0
        rr_for = Fraction(self.team1_runs_for) / self.team1_overs_for
        rr_against = Fraction(self.team1_runs_against) / self.team1_overs_against
        return float(rr_for - rr_against)

    # ------------------------------------------------------------------
    # Team 2 NRR contributions
    # ------------------------------------------------------------------

    @property
    def team2_runs_for(self) -> int:
        return self._match.innings2.runs

    @property
    def team2_overs_for(self) -> Fraction:
        return self._match.innings2.nrr_overs

    @property
    def team2_runs_against(self) -> int:
        return self._match.innings1.runs

    @property
    def team2_overs_against(self) -> Fraction:
        """
        Overs used as NRR denominator for Team 2's bowling (Team 1's batting).

        For DLS matches, use the credited overs if available.
        """
        if self._match.dls_affected and self._match.dls_team1_overs_credited is not None:
            return self._match.dls_team1_overs_credited.as_fraction
        return self._match.innings1.nrr_overs

    def team2_match_nrr(self) -> float:
        """NRR for Team 2 in this individual match (for display only)."""
        if not self.is_valid_for_nrr():
            return 0.0
        rr_for = Fraction(self.team2_runs_for) / self.team2_overs_for
        rr_against = Fraction(self.team2_runs_against) / self.team2_overs_against
        return float(rr_for - rr_against)

    # ------------------------------------------------------------------
    # Generic accessor
    # ------------------------------------------------------------------

    def runs_for(self, team: str) -> int:
        """Runs scored by *team* in this match."""
        if team == self._match.team1:
            return self.team1_runs_for
        if team == self._match.team2:
            return self.team2_runs_for
        raise ValueError(f"Team {team!r} did not play in match {self._match.match_id!r}.")

    def overs_for(self, team: str) -> Fraction:
        """NRR batting overs for *team* in this match."""
        if team == self._match.team1:
            return self.team1_overs_for
        if team == self._match.team2:
            return self.team2_overs_for
        raise ValueError(f"Team {team!r} did not play in match {self._match.match_id!r}.")

    def runs_against(self, team: str) -> int:
        """Runs conceded by *team* in this match."""
        if team == self._match.team1:
            return self.team1_runs_against
        if team == self._match.team2:
            return self.team2_runs_against
        raise ValueError(f"Team {team!r} did not play in match {self._match.match_id!r}.")

    def overs_against(self, team: str) -> Fraction:
        """NRR bowling overs for *team* in this match."""
        if team == self._match.team1:
            return self.team1_overs_against
        if team == self._match.team2:
            return self.team2_overs_against
        raise ValueError(f"Team {team!r} did not play in match {self._match.match_id!r}.")

    def __repr__(self) -> str:
        m = self._match
        return (
            f"MatchNRR(match_id={m.match_id!r}, {m.team1} vs {m.team2}, "
            f"valid={self.is_valid_for_nrr()})"
        )


# ---------------------------------------------------------------------------
# Cumulative aggregator
# ---------------------------------------------------------------------------


class TeamNRRPool:
    """
    Cumulative NRR accumulator for one team across multiple matches.

    .. important::
        NRR is **not** the average of per-match NRRs.  The correct method
        is to sum all runs-for / overs-for across the tournament, then
        subtract the equivalent for runs-against.

        This class enforces the correct aggregation by design — it never
        stores per-match NRR values.

    Usage
    -----
    >>> pool = TeamNRRPool("Mumbai Indians")
    >>> for match in matches:
    ...     pool.add_match(match)
    >>> pool.nrr()
    1.425
    """

    def __init__(self, team: str) -> None:
        self.team = team
        self._runs_for: int = 0
        self._overs_for: Fraction = Fraction(0)
        self._runs_against: int = 0
        self._overs_against: Fraction = Fraction(0)

    def add_match(self, match: MatchRecord) -> None:
        """
        Accumulate NRR data from one match.

        No-result and super-over matches are silently skipped.
        """
        mnrr = MatchNRR(match)
        if not mnrr.is_valid_for_nrr():
            return
        if self.team not in (match.team1, match.team2):
            return
        self._runs_for += mnrr.runs_for(self.team)
        self._overs_for += mnrr.overs_for(self.team)
        self._runs_against += mnrr.runs_against(self.team)
        self._overs_against += mnrr.overs_against(self.team)

    @classmethod
    def from_matches(cls, team: str, matches: Iterable[MatchRecord]) -> "TeamNRRPool":
        """Construct and populate from an iterable of matches."""
        pool = cls(team)
        for m in matches:
            pool.add_match(m)
        return pool

    @property
    def runs_for(self) -> int:
        return self._runs_for

    @property
    def overs_for(self) -> Fraction:
        return self._overs_for

    @property
    def runs_against(self) -> int:
        return self._runs_against

    @property
    def overs_against(self) -> Fraction:
        return self._overs_against

    def nrr(self) -> float:
        """
        Tournament NRR for this team.

        Returns 0.0 if the team hasn't played any valid matches.
        """
        if self._overs_for == 0 or self._overs_against == 0:
            return 0.0
        rr_for = Fraction(self._runs_for) / self._overs_for
        rr_against = Fraction(self._runs_against) / self._overs_against
        return float(rr_for - rr_against)

    def run_rate_for(self) -> float:
        """Cumulative runs-per-over scored."""
        if self._overs_for == 0:
            return 0.0
        return float(Fraction(self._runs_for) / self._overs_for)

    def run_rate_against(self) -> float:
        """Cumulative runs-per-over conceded."""
        if self._overs_against == 0:
            return 0.0
        return float(Fraction(self._runs_against) / self._overs_against)

    def __repr__(self) -> str:
        return (
            f"TeamNRRPool(team={self.team!r}, "
            f"runs_for={self._runs_for}, overs_for={float(self._overs_for):.2f}, "
            f"nrr={self.nrr():+.3f})"
        )

"""
cricket_nrr.dls
~~~~~~~~~~~~~~~
Duckworth-Lewis-Stern (DLS) par score and revised target calculator.

Uses the **Standard Edition** resource table embedded in
:mod:`cricket_nrr._dls_table`.  For partial overs, the resource
percentage is linearly interpolated between the two bounding integer
over values.

Typical usage
-------------
>>> from cricket_nrr import DLSEngine, Over
>>> engine = DLSEngine(g50=245.0)

# Team 1 scored 250 in full 50 overs.
# Rain wipes out 25 overs between innings → Team 2 gets only 25 overs.
>>> engine.par_score(
...     team1_score=250,
...     team1_overs_faced=Over("50.0"),
...     team1_max_overs=Over("50.0"),
...     team1_wickets_lost=8,
...     team2_overs_available=Over("25.0"),
... )
182

# Mid-innings: Team 2 at 80/3 after 15 overs when rain stops play.
# They now have 10 overs left instead of 35.
>>> engine.par_score(
...     team1_score=250,
...     team1_overs_faced=Over("50.0"),
...     team1_max_overs=Over("50.0"),
...     team1_wickets_lost=8,
...     team2_overs_available=Over("25.0"),
...     team2_wickets_lost=3,
...     team2_overs_used=Over("15.0"),
... )
# returns the par score Team 2 must reach at the resumption point
"""

from __future__ import annotations

from fractions import Fraction
from typing import Optional

from .overs import Over
from ._dls_table import DLS_RESOURCE_TABLE
from .validators import validate_g50, validate_wickets, validate_runs

__all__ = ["DLSEngine"]

# A wicket count of 10 always means 0% resources regardless of overs.
_ALL_OUT_RESOURCE = 0.0


class DLSEngine:
    """
    DLS par score and revised target calculator.

    Parameters
    ----------
    g50 : float
        Average score expected in an uninterrupted 50-over innings.
        Standard values:

        - ``245`` — men's international / IPL (default)
        - ``200`` — women's international, U19, associate members

    Notes
    -----
    *Standard Edition* table is used (D/L 1998 / 2004).  Results will be
    accurate for most scenarios.  High-scoring T20 matches may diverge
    slightly from the ICC Professional Edition (Stern update).
    """

    def __init__(self, g50: float = 245.0) -> None:
        validate_g50(g50)
        self.g50 = g50

    # ------------------------------------------------------------------
    # Core resource lookup
    # ------------------------------------------------------------------

    def resource_percentage(
        self,
        overs_remaining: Over,
        wickets_lost: int,
    ) -> float:
        """
        Resource percentage remaining at a given match state.

        Parameters
        ----------
        overs_remaining : Over
            Overs left in the innings (e.g., ``Over("25.0")`` or
            ``Over("23.4")`` for mid-over interruptions).
        wickets_lost : int
            Wickets that have already fallen (0–9; 10 = all out → 0%).

        Returns
        -------
        float
            Percentage of batting resource remaining (0.0 – 100.0).

        Examples
        --------
        >>> engine = DLSEngine()
        >>> engine.resource_percentage(Over("50.0"), 0)
        100.0
        >>> engine.resource_percentage(Over("25.0"), 0)
        68.2
        >>> engine.resource_percentage(Over("10.0"), 5)
        26.4
        """
        validate_wickets(wickets_lost, field="wickets_lost")

        if wickets_lost == 10:
            return _ALL_OUT_RESOURCE

        # Cap at 50 overs (T20 uses 20, but table rows go to 50)
        floor_overs = overs_remaining.full_overs
        extra_balls = overs_remaining.extra_balls  # 0–5

        floor_overs = min(floor_overs, 50)

        floor_pct = DLS_RESOURCE_TABLE.get((floor_overs, wickets_lost), 0.0)

        if extra_balls == 0:
            return floor_pct

        # Linear interpolation for fractional overs
        ceil_overs = min(floor_overs + 1, 50)
        ceil_pct = DLS_RESOURCE_TABLE.get((ceil_overs, wickets_lost), 0.0)
        # extra_balls is how many balls INTO this over have been bowled,
        # so the "remaining fraction" within the over is (6 - extra_balls) / 6.
        # We interpolate between floor and ceil.
        fraction_of_over_completed = Fraction(extra_balls, 6)
        interpolated = float(
            ceil_pct + (floor_pct - ceil_pct) * (1 - fraction_of_over_completed)
        )
        return round(interpolated, 2)

    def resources_available(
        self,
        overs_available: Over,
        wickets_lost: int = 0,
    ) -> float:
        """
        Resource percentage available to a team *at the start of* their
        innings or after an interruption.

        This is equivalent to ``resource_percentage(overs_available, wickets_lost)``.
        """
        return self.resource_percentage(overs_available, wickets_lost)

    def resources_lost(
        self,
        overs_remaining_before: Over,
        overs_remaining_after: Over,
        wickets_lost: int,
    ) -> float:
        """
        Percentage of resources lost due to a rain interruption.

        Parameters
        ----------
        overs_remaining_before : Over
            Overs remaining *before* the interruption.
        overs_remaining_after : Over
            Overs remaining *after* the interruption resumes.
        wickets_lost : int
            Wickets fallen at the time of interruption.

        Returns
        -------
        float
            Resources lost (%). Always non-negative.
        """
        before = self.resource_percentage(overs_remaining_before, wickets_lost)
        after = self.resource_percentage(overs_remaining_after, wickets_lost)
        return max(0.0, round(before - after, 2))

    # ------------------------------------------------------------------
    # Par score calculation
    # ------------------------------------------------------------------

    def par_score(
        self,
        team1_score: int,
        team1_overs_faced: Over,
        team1_max_overs: Over,
        team1_wickets_lost: int,
        team2_overs_available: Over,
        team2_wickets_lost: int = 0,
        team2_overs_used: Optional[Over] = None,
    ) -> int:
        """
        Calculate the DLS par score for Team 2.

        Works for both interruption stages:

        **Between-innings** (default, ``team2_overs_used=None``)
            Rain falls between innings; Team 2 is given fewer overs than
            Team 1.  Wickets for Team 2 default to 0 (haven't batted yet).

        **Mid-innings**
            Rain interrupts Team 2's innings.  Pass ``team2_overs_used``
            as the overs batted so far and ``team2_wickets_lost`` as the
            wickets fallen.

        Parameters
        ----------
        team1_score : int
            Team 1's final total.
        team1_overs_faced : Over
            Overs Team 1 actually batted (affects R1 only if they didn't
            face their full quota, e.g., they were all out).
        team1_max_overs : Over
            Maximum overs available to Team 1.
        team1_wickets_lost : int
            Wickets Team 1 lost (used to compute R1 when they didn't bat
            their full overs without being all out).
        team2_overs_available : Over
            Overs available to Team 2 *after* the interruption.
        team2_wickets_lost : int
            Wickets Team 2 have lost at the interruption (mid-innings only).
        team2_overs_used : Over or None
            Overs Team 2 have already batted at the interruption.
            ``None`` for between-innings interruptions.

        Returns
        -------
        int
            The par score.  Team 2 must *exceed* this to win (the revised
            *target* is ``par_score + 1`` — see :meth:`revised_target`).

        Examples
        --------
        Between-innings, Team 1 batted full 50 overs:

        >>> engine = DLSEngine(g50=245.0)
        >>> engine.par_score(
        ...     team1_score=250,
        ...     team1_overs_faced=Over("50.0"),
        ...     team1_max_overs=Over("50.0"),
        ...     team1_wickets_lost=8,
        ...     team2_overs_available=Over("25.0"),
        ... )
        182
        """
        validate_runs(team1_score, field="team1_score")
        validate_wickets(team1_wickets_lost, field="team1_wickets_lost")
        validate_wickets(team2_wickets_lost, field="team2_wickets_lost")

        # R1 — resources available to Team 1
        r1 = self._team1_resources(
            team1_overs_faced, team1_max_overs, team1_wickets_lost
        )

        # R2 — resources available to Team 2
        r2 = self._team2_resources(
            team1_max_overs,
            team2_overs_available,
            team2_wickets_lost,
            team2_overs_used,
        )

        par = team1_score + self.g50 * (r2 - r1) / 100.0
        return max(0, int(par))

    def revised_target(
        self,
        team1_score: int,
        team1_overs_faced: Over,
        team1_max_overs: Over,
        team1_wickets_lost: int,
        team2_overs_available: Over,
        team2_wickets_lost: int = 0,
        team2_overs_used: Optional[Over] = None,
    ) -> int:
        """
        Revised target Team 2 must *beat* (= par score + 1).

        See :meth:`par_score` for parameter documentation.
        """
        return (
            self.par_score(
                team1_score=team1_score,
                team1_overs_faced=team1_overs_faced,
                team1_max_overs=team1_max_overs,
                team1_wickets_lost=team1_wickets_lost,
                team2_overs_available=team2_overs_available,
                team2_wickets_lost=team2_wickets_lost,
                team2_overs_used=team2_overs_used,
            )
            + 1
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _team1_resources(
        self,
        overs_faced: Over,
        max_overs: Over,
        wickets_lost: int,
    ) -> float:
        """
        R1 — resources used by Team 1.

        The resource percentage *used* by Team 1 is:
            R1 = R(start_of_innings) - R(end_of_innings)

        For a full innings (overs_faced >= max_overs), R(end) = 0
        so R1 = 100%.  For a curtailed / all-out innings:
            R(start) = resource% for (max_overs remaining, 0 wickets)
            R(end)   = resource% for (overs_remaining_at_end, wickets_lost)
        """
        if overs_faced >= max_overs:
            # Batted full quota — 100% resources used
            return 100.0

        overs_remaining_at_end = max_overs - overs_faced
        # Resources at the start of a full innings (0 wickets, max_overs remaining)
        r_start = self.resource_percentage(max_overs, 0)
        # Resources still remaining at the end of Team 1's (shortened) innings
        r_end = self.resource_percentage(overs_remaining_at_end, wickets_lost)
        return round(r_start - r_end, 2)

    def _team2_resources(
        self,
        team1_max_overs: Over,
        team2_overs_available: Over,
        team2_wickets_lost: int,
        team2_overs_used: Optional[Over],
    ) -> float:
        """
        R2 — resources available to Team 2.

        For a between-innings interruption: resource % for
        (team2_overs_available, 0).

        For a mid-innings interruption: resources at state
        (remaining_before_interruption, wickets) minus resources lost.
        """
        if team2_overs_used is None:
            # Between-innings: Team 2 hasn't started yet
            return self.resource_percentage(team2_overs_available, team2_wickets_lost)

        # Mid-innings: compute resources remaining before vs after
        overs_remaining_before = team1_max_overs - team2_overs_used
        # After the interruption Team 2 has team2_overs_available left
        overs_remaining_after = team2_overs_available

        r_before = self.resource_percentage(overs_remaining_before, team2_wickets_lost)
        r_after = self.resource_percentage(overs_remaining_after, team2_wickets_lost)

        # Resources lost = r_before - r_after (capped at 0)
        resources_lost = max(0.0, r_before - r_after)

        # Team 2's total resources = what they had at start - what they lost
        r2_full = self.resource_percentage(team1_max_overs, 0)
        return round(r2_full - resources_lost, 2)

    # ------------------------------------------------------------------
    # Pandas integration
    # ------------------------------------------------------------------

    def par_score_series(
        self,
        df: "pd.DataFrame",  # type: ignore[type-arg]
        *,
        team1_score_col: str = "team1_score",
        team1_overs_col: str = "team1_overs",
        team1_max_overs_col: str = "team1_max_overs",
        team1_wickets_col: str = "team1_wickets",
        team2_overs_avail_col: str = "team2_overs_available",
    ) -> "pd.Series":  # type: ignore[type-arg]
        """
        Vectorised par-score computation across a pandas DataFrame.

        Requires pandas (optional dependency).
        Each row must represent a between-innings DLS scenario.
        """
        return df.apply(
            lambda row: self.par_score(
                team1_score=int(row[team1_score_col]),
                team1_overs_faced=Over(row[team1_overs_col]),
                team1_max_overs=Over(row[team1_max_overs_col]),
                team1_wickets_lost=int(row[team1_wickets_col]),
                team2_overs_available=Over(row[team2_overs_avail_col]),
            ),
            axis=1,
        )

    def __repr__(self) -> str:
        return f"DLSEngine(g50={self.g50})"

"""
cricket_nrr.standings
~~~~~~~~~~~~~~~~~~~~~
Tournament standings engine.

Provides:

- :class:`Tournament` — builds and sorts a full points table
- :class:`TeamStanding` — one row of the points table
- :meth:`Tournament.whatif_nrr` — "if we score X, what can we concede?"
- :meth:`Tournament.qualify_margin` — "did we overtake them on NRR?"
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Iterable, List, Optional

from .models import InningsRecord, MatchRecord
from .nrr import MatchNRR, TeamNRRPool
from .overs import Over
from .formatters import format_nrr

__all__ = ["Tournament", "TeamStanding", "WhatIfResult", "QualifyResult"]


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TeamStanding:
    """
    One row of the tournament points table.

    Attributes
    ----------
    team : str
        Team name.
    played : int
        Matches played (excludes no-results for NRR, but counts for played total).
    won : int
    lost : int
    tied : int
    no_result : int
    points : int
    runs_for : int
        Cumulative runs scored across all valid NRR matches.
    overs_for : Fraction
        Cumulative exact overs faced across all valid NRR matches.
    runs_against : int
        Cumulative runs conceded across all valid NRR matches.
    overs_against : Fraction
        Cumulative exact overs bowled across all valid NRR matches.
    nrr : float
        Tournament NRR (cumulative, not average of per-match NRRs).
    """

    team: str
    played: int
    won: int
    lost: int
    tied: int
    no_result: int
    points: int
    runs_for: int
    overs_for: Fraction
    runs_against: int
    overs_against: Fraction
    nrr: float

    def nrr_str(self, decimals: int = 3) -> str:
        """Formatted NRR string, e.g. ``'+1.425'`` or ``'-0.312'``."""
        return format_nrr(self.nrr, decimals)

    def run_rate_for(self) -> float:
        """Cumulative runs-per-over scored."""
        if self.overs_for == 0:
            return 0.0
        return float(Fraction(self.runs_for) / self.overs_for)

    def run_rate_against(self) -> float:
        """Cumulative runs-per-over conceded."""
        if self.overs_against == 0:
            return 0.0
        return float(Fraction(self.runs_against) / self.overs_against)

    def to_dict(self) -> dict:
        """Convert to a plain dictionary (useful for DataFrame construction)."""
        return {
            "Team": self.team,
            "Played": self.played,
            "Won": self.won,
            "Lost": self.lost,
            "Tied": self.tied,
            "NR": self.no_result,
            "Points": self.points,
            "NRR": self.nrr_str(),
            "Runs For": self.runs_for,
            "Overs For": float(self.overs_for),
            "Runs Against": self.runs_against,
            "Overs Against": float(self.overs_against),
        }


@dataclass
class WhatIfResult:
    """
    Result of a ``Tournament.whatif_nrr`` query.

    Attributes
    ----------
    team : str
        The team whose NRR scenario was queried.
    scenario : str
        Human-readable summary of the scenario.
    current_nrr : float
        Team's NRR *before* the hypothetical match.
    target_nrr : float
        The NRR threshold they want to stay above (or reach).
    max_concede : int or None
        Maximum runs they can concede (if batting first) to hit ``target_nrr``.
        ``None`` if bowling first or not applicable.
    min_score : int or None
        Minimum runs they need to score (if bowling first) to hit ``target_nrr``.
        ``None`` if batting first or not applicable.
    projected_nrr : float
        Their NRR if the threshold boundary condition is exactly met.
    achievable : bool
        ``False`` if it is mathematically impossible to reach ``target_nrr``
        in this match (e.g., they would need to concede negative runs).
    """

    team: str
    scenario: str
    current_nrr: float
    target_nrr: float
    max_concede: Optional[int]
    min_score: Optional[int]
    projected_nrr: float
    achievable: bool

    def __str__(self) -> str:
        return self.scenario


@dataclass
class QualifyResult:
    """
    Result of a ``Tournament.qualify_margin`` query.

    Attributes
    ----------
    team_chasing : str
        Team trying to qualify.
    team_to_overtake : str
        Team currently above them on the table.
    qualified : bool
        Whether ``team_chasing`` overtook ``team_to_overtake``.
    points_after_team_chasing : int
    points_after_team_to_overtake : int
    nrr_after_team_chasing : float
    nrr_after_team_to_overtake : float
    nrr_needed : float
        NRR ``team_chasing`` needed to overtake (if points are equal).
    nrr_delta : float
        Gap closed / opened.
    margin_description : str
        e.g. ``"Qualified by +0.312 NRR"`` or ``"Not qualified — need +0.580 more NRR"``.
    """

    team_chasing: str
    team_to_overtake: str
    qualified: bool
    points_after_team_chasing: int
    points_after_team_to_overtake: int
    nrr_after_team_chasing: float
    nrr_after_team_to_overtake: float
    nrr_needed: float
    nrr_delta: float
    margin_description: str

    def __str__(self) -> str:
        return self.margin_description


# ---------------------------------------------------------------------------
# Main tournament engine
# ---------------------------------------------------------------------------


class Tournament:
    """
    Tournament standings engine.

    Aggregates multiple :class:`~cricket_nrr.MatchRecord` objects into a
    sorted points table, and provides live what-if and qualification queries.

    Parameters
    ----------
    matches : list of MatchRecord
        All matches played so far in the tournament.
    points_win : int
        Points awarded for a win (default 2).
    points_tie : int
        Points awarded for a tie / super over (default 1).
    points_no_result : int
        Points awarded for a no-result / abandoned match (default 1).

    Examples
    --------
    >>> from cricket_nrr.loaders import from_csv
    >>> matches = from_csv("matches.csv")
    >>> t = Tournament(matches)
    >>> for row in t.standings():
    ...     print(row.team, row.points, row.nrr_str())
    """

    def __init__(
        self,
        matches: Iterable[MatchRecord],
        *,
        points_win: int = 2,
        points_tie: int = 1,
        points_no_result: int = 1,
    ) -> None:
        self._matches: List[MatchRecord] = list(matches)
        self._points_win = points_win
        self._points_tie = points_tie
        self._points_no_result = points_no_result

        # Collect all team names
        self._teams: List[str] = []
        seen: set = set()
        for m in self._matches:
            for t in (m.team1, m.team2):
                if t not in seen:
                    self._teams.append(t)
                    seen.add(t)

    # ------------------------------------------------------------------
    # Core: standings table
    # ------------------------------------------------------------------

    def standings(
        self,
        sort_by: Optional[List[str]] = None,
    ) -> List[TeamStanding]:
        """
        Build and return the sorted tournament points table.

        Parameters
        ----------
        sort_by : list of str, optional
            Columns to sort by in descending order.
            Valid keys: ``"points"``, ``"nrr"``, ``"wins"``, ``"runs_for"``.
            Default: ``["points", "nrr", "wins"]``.

        Returns
        -------
        list of TeamStanding
            Sorted from first to last.
        """
        if sort_by is None:
            sort_by = ["points", "nrr", "wins"]

        rows = [self._build_standing(team) for team in self._teams]

        def sort_key(s: TeamStanding):
            keys = []
            for col in sort_by:
                if col == "points":
                    keys.append(-s.points)
                elif col == "nrr":
                    keys.append(-s.nrr)
                elif col == "wins":
                    keys.append(-s.won)
                elif col == "runs_for":
                    keys.append(-s.runs_for)
            return tuple(keys)

        return sorted(rows, key=sort_key)

    def to_dataframe(self) -> "pd.DataFrame":  # type: ignore[type-arg]
        """
        Convert standings to a pandas DataFrame.

        Requires pandas (optional dependency).
        """
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError(
                "pandas is required for to_dataframe(). "
                "Install with: pip install cricket-nrr[pandas]"
            ) from exc
        rows = [s.to_dict() for s in self.standings()]
        return pd.DataFrame(rows)

    def to_html_table(self) -> str:
        """
        Export the standings table as an HTML ``<table>`` string.

        No external dependencies required.
        """
        rows = self.standings()
        headers = [
            "Team", "P", "W", "L", "T", "NR", "Pts", "NRR",
            "Runs For", "Overs For", "Runs Against", "Overs Against",
        ]
        lines = ["<table>", "  <thead><tr>"]
        for h in headers:
            lines.append(f"    <th>{h}</th>")
        lines.append("  </tr></thead>")
        lines.append("  <tbody>")
        for s in rows:
            lines.append("  <tr>")
            cells = [
                s.team, s.played, s.won, s.lost, s.tied, s.no_result,
                s.points, s.nrr_str(),
                s.runs_for, f"{float(s.overs_for):.2f}",
                s.runs_against, f"{float(s.overs_against):.2f}",
            ]
            for c in cells:
                lines.append(f"    <td>{c}</td>")
            lines.append("  </tr>")
        lines.append("  </tbody>")
        lines.append("</table>")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # What-if predictor
    # ------------------------------------------------------------------

    def whatif_nrr(
        self,
        team: str,
        batting_first: bool,
        runs_scored: int,
        overs_batted: Over,
        all_out: bool,
        max_overs: Over,
        *,
        target_nrr: float,
    ) -> WhatIfResult:
        """
        Compute the threshold condition for *team* to achieve *target_nrr*.

        Answers one of two questions depending on ``batting_first``:

        **Batting first** (``batting_first=True``):
            "We scored *runs_scored* in *overs_batted* overs.
             What is the *maximum* we can concede in *max_overs* overs
             to keep our NRR above *target_nrr*?"

        **Bowling first** (``batting_first=False``):
            "The opposition scored *runs_scored* in *overs_batted* overs.
             What is the *minimum* we need to score (in at most *max_overs*)
             to push our NRR above *target_nrr*?"

        Parameters
        ----------
        team : str
            Team name (must appear in the tournament).
        batting_first : bool
            Whether *team* is batting first in the hypothetical match.
        runs_scored : int
            Runs scored by the batting side.
        overs_batted : Over
            Overs faced.
        all_out : bool
            Whether the batting side was all out.
        max_overs : Over
            Full over quota for the match.
        target_nrr : float
            The NRR threshold to hit or exceed.

        Returns
        -------
        WhatIfResult
        """
        pool = TeamNRRPool.from_matches(team, self._matches)
        current_nrr = pool.nrr()

        # Current cumulative totals
        rf = Fraction(pool.runs_for)
        of = pool.overs_for
        ra = Fraction(pool.runs_against)
        oa = pool.overs_against

        # Overs for NRR calculation (all-out rule)
        inn = InningsRecord(
            runs=runs_scored,
            overs_faced=overs_batted,
            wickets_lost=10 if all_out else 0,
            all_out=all_out,
            max_overs=max_overs,
        )
        nrr_overs_batted = inn.nrr_overs  # respects all-out rule
        nrr_overs_bowl = max_overs.as_fraction  # opponent bowls the full quota

        if batting_first:
            # We scored runs_scored.  What is max we can concede in max_overs?
            # New NRR = (rf + runs_scored) / (of + nrr_overs_batted)
            #           - (ra + x) / (oa + nrr_overs_bowl)
            # Solve for x such that new_nrr >= target_nrr
            new_of = of + nrr_overs_batted
            new_oa = oa + nrr_overs_bowl
            new_rf = rf + runs_scored

            # target_nrr <= new_rf / new_of - (ra + x) / new_oa
            # (ra + x) / new_oa <= new_rf / new_of - target_nrr
            # ra + x <= (new_rf / new_of - target_nrr) * new_oa
            rhs = (Fraction(new_rf) / new_of - Fraction(target_nrr).limit_denominator(10_000)) * new_oa
            max_concede_frac = rhs - ra
            max_concede = int(max_concede_frac)

            achievable = max_concede >= 0
            # Project NRR if exactly at boundary
            proj_ra = ra + max(Fraction(0), max_concede_frac)
            proj_nrr = float(Fraction(new_rf) / new_of - proj_ra / new_oa)

            scenario = (
                f"{team} scored {runs_scored} in {overs_batted} overs "
                f"({'all out' if all_out else 'not all out'}). "
                f"To achieve NRR {format_nrr(target_nrr)}, they must "
                f"concede AT MOST {max(0, max_concede)} runs in {max_overs} overs."
                if achievable
                else (
                    f"{team} scored {runs_scored} in {overs_batted} overs. "
                    f"It is mathematically impossible to reach NRR {format_nrr(target_nrr)} "
                    f"in this match — the required concede ({max_concede}) is negative."
                )
            )
            return WhatIfResult(
                team=team,
                scenario=scenario,
                current_nrr=current_nrr,
                target_nrr=target_nrr,
                max_concede=max(0, max_concede) if achievable else None,
                min_score=None,
                projected_nrr=round(proj_nrr, 6),
                achievable=achievable,
            )

        else:
            # Bowling first. Opposition scored runs_scored.
            # We need to score min_score runs in max_overs.
            # NRR = (rf + x) / (of + nrr_overs_bowl)
            #       - (ra + runs_scored) / (oa + nrr_overs_batted)
            new_of = of + nrr_overs_bowl
            new_oa = oa + nrr_overs_batted
            new_ra = ra + runs_scored

            # target_nrr <= (rf + x) / new_of - new_ra / new_oa
            # (rf + x) / new_of >= target_nrr + new_ra / new_oa
            # rf + x >= (target_nrr + new_ra / new_oa) * new_of
            rhs = (
                Fraction(target_nrr).limit_denominator(10_000)
                + Fraction(new_ra) / new_oa
            ) * new_of
            min_score_frac = rhs - rf
            min_score = int(min_score_frac) + (1 if min_score_frac % 1 != 0 else 0)

            achievable = True  # mathematically always possible (just score enough)
            proj_rf = rf + max(Fraction(0), min_score_frac)
            proj_nrr = float(proj_rf / new_of - Fraction(new_ra) / new_oa)

            scenario = (
                f"Opposition scored {runs_scored} in {overs_batted} overs "
                f"({'all out' if all_out else 'not all out'}). "
                f"{team} must score AT LEAST {min_score} runs in {max_overs} overs "
                f"to reach NRR {format_nrr(target_nrr)}."
            )
            return WhatIfResult(
                team=team,
                scenario=scenario,
                current_nrr=current_nrr,
                target_nrr=target_nrr,
                max_concede=None,
                min_score=min_score,
                projected_nrr=round(proj_nrr, 6),
                achievable=achievable,
            )

    # ------------------------------------------------------------------
    # Qualification margin finder
    # ------------------------------------------------------------------

    def qualify_margin(
        self,
        team_chasing: str,
        team_to_overtake: str,
        match_chasing: MatchRecord,
        match_to_overtake: Optional[MatchRecord] = None,
    ) -> QualifyResult:
        """
        Determine whether *team_chasing* has qualified ahead of *team_to_overtake*
        after a given final match.

        Parameters
        ----------
        team_chasing : str
            The team trying to move up the table.
        team_to_overtake : str
            The team currently above them.
        match_chasing : MatchRecord
            The match played by *team_chasing* (their final group match).
        match_to_overtake : MatchRecord or None
            The simultaneous match played by *team_to_overtake*, if any.
            ``None`` if they don't play in the same round.

        Returns
        -------
        QualifyResult
        """
        # Build current pools before the new matches
        pool_c = TeamNRRPool.from_matches(team_chasing, self._matches)
        pool_o = TeamNRRPool.from_matches(team_to_overtake, self._matches)
        pts_c = self._points_for(team_chasing)
        pts_o = self._points_for(team_to_overtake)

        # Add the new matches
        pool_c.add_match(match_chasing)
        pts_c += self._match_points(match_chasing, team_chasing)

        if match_to_overtake is not None:
            pool_o.add_match(match_to_overtake)
            pts_o += self._match_points(match_to_overtake, team_to_overtake)

        nrr_c = pool_c.nrr()
        nrr_o = pool_o.nrr()

        # Qualification logic: points first, NRR second
        if pts_c > pts_o:
            qualified = True
        elif pts_c < pts_o:
            qualified = False
        else:
            # Equal points → NRR decides
            qualified = nrr_c > nrr_o

        nrr_delta = round(nrr_c - nrr_o, 6)
        nrr_needed = nrr_o  # on equal points, need to beat this

        if qualified:
            if pts_c > pts_o:
                desc = (
                    f"{team_chasing} qualified with more points "
                    f"({pts_c} vs {pts_o})."
                )
            else:
                desc = (
                    f"{team_chasing} qualified on NRR. "
                    f"NRR: {format_nrr(nrr_c)} vs {format_nrr(nrr_o)} "
                    f"(margin: {format_nrr(nrr_delta)})."
                )
        else:
            if pts_c < pts_o:
                desc = (
                    f"{team_chasing} did not qualify — {team_to_overtake} has "
                    f"more points ({pts_o} vs {pts_c})."
                )
            else:
                shortfall = round(nrr_o - nrr_c, 6)
                desc = (
                    f"{team_chasing} did not qualify — NRR {format_nrr(nrr_c)} "
                    f"vs {format_nrr(nrr_o)}. "
                    f"Needed {format_nrr(shortfall)} more NRR."
                )

        return QualifyResult(
            team_chasing=team_chasing,
            team_to_overtake=team_to_overtake,
            qualified=qualified,
            points_after_team_chasing=pts_c,
            points_after_team_to_overtake=pts_o,
            nrr_after_team_chasing=round(nrr_c, 6),
            nrr_after_team_to_overtake=round(nrr_o, 6),
            nrr_needed=round(nrr_needed, 6),
            nrr_delta=nrr_delta,
            margin_description=desc,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_standing(self, team: str) -> TeamStanding:
        """Build a single TeamStanding row for one team."""
        played = won = lost = tied = no_result = points = 0
        pool = TeamNRRPool(team)

        for m in self._matches:
            if team not in (m.team1, m.team2):
                continue
            played += 1

            if m.result == "no_result":
                no_result += 1
                points += self._points_no_result
            elif m.result == "tie":
                tied += 1
                points += self._points_tie
                pool.add_match(m)
            elif m.winner == team:
                won += 1
                points += self._points_win
                pool.add_match(m)
            else:
                lost += 1
                pool.add_match(m)

        return TeamStanding(
            team=team,
            played=played,
            won=won,
            lost=lost,
            tied=tied,
            no_result=no_result,
            points=points,
            runs_for=pool.runs_for,
            overs_for=pool.overs_for,
            runs_against=pool.runs_against,
            overs_against=pool.overs_against,
            nrr=pool.nrr(),
        )

    def _points_for(self, team: str) -> int:
        """Current points tally for *team* across existing matches."""
        total = 0
        for m in self._matches:
            total += self._match_points(m, team)
        return total

    def _match_points(self, match: MatchRecord, team: str) -> int:
        """Points earned by *team* in *match*."""
        if team not in (match.team1, match.team2):
            return 0
        if match.result == "no_result":
            return self._points_no_result
        if match.result == "tie":
            return self._points_tie
        if match.winner == team:
            return self._points_win
        return 0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def teams(self) -> List[str]:
        """All team names in the tournament."""
        return list(self._teams)

    @property
    def matches(self) -> List[MatchRecord]:
        """All match records."""
        return list(self._matches)

    def __repr__(self) -> str:
        return f"Tournament(teams={len(self._teams)}, matches={len(self._matches)})"

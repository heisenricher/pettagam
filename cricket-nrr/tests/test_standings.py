"""
tests/test_standings.py
~~~~~~~~~~~~~~~~~~~~~~~~
Tests for Tournament standings, what-if predictor, and qualification finder.
"""

import datetime
import pytest

from cricket_nrr import InningsRecord, MatchRecord, Over, Tournament, TeamStanding
from cricket_nrr.formatters import format_nrr


# ---------------------------------------------------------------------------
# Points accumulation
# ---------------------------------------------------------------------------

class TestPoints:
    def test_win_gives_2_points(self, ipl_matches):
        t = Tournament(ipl_matches)
        table = t.standings()
        for row in table:
            # Points must be consistent with W/L/T/NR
            expected = row.won * 2 + row.tied * 1 + row.no_result * 1
            assert row.points == expected, (
                f"{row.team}: expected {expected} pts, got {row.points}"
            )

    def test_no_result_gives_1_point(self, no_result_match, simple_t20_match):
        t = Tournament([no_result_match, simple_t20_match])
        table = {s.team: s for s in t.standings()}
        # KKR and PBKS each get 1 point for the no-result
        assert table["Kolkata Knight Riders"].points == 1
        assert table["Punjab Kings"].points == 1

    def test_winner_at_top(self, ipl_matches):
        t = Tournament(ipl_matches)
        table = t.standings()
        # Top team has most points
        assert table[0].points >= table[1].points

    def test_10_teams_in_ipl(self, ipl_matches):
        t = Tournament(ipl_matches)
        assert len(t.standings()) == 10


# ---------------------------------------------------------------------------
# NRR format
# ---------------------------------------------------------------------------

class TestNRRFormat:
    def test_nrr_str_3_decimals(self, ipl_matches):
        t = Tournament(ipl_matches)
        for row in t.standings():
            s = row.nrr_str()
            assert s[0] in ("+", "-"), f"NRR string must start with + or -: {s}"
            decimal_part = s.split(".")[1]
            assert len(decimal_part) == 3, f"Expected 3 decimals: {s}"

    def test_positive_winner_nrr(self, ipl_matches):
        t = Tournament(ipl_matches)
        top = t.standings()[0]
        # The team at the top of the table (most points) should have positive NRR
        assert top.nrr > 0

    def test_format_nrr_signs(self):
        assert format_nrr(1.425) == "+1.425"
        assert format_nrr(-0.312) == "-0.312"
        assert format_nrr(0.0) == "+0.000"


# ---------------------------------------------------------------------------
# What-if predictor
# ---------------------------------------------------------------------------

class TestWhatIf:
    def test_batting_first_max_concede_is_int(self, ipl_matches):
        t = Tournament(ipl_matches)
        result = t.whatif_nrr(
            "Mumbai Indians",
            batting_first=True,
            runs_scored=180,
            overs_batted=Over("20.0"),
            all_out=False,
            max_overs=Over("20.0"),
            target_nrr=0.500,
        )
        assert isinstance(result.max_concede, int) or result.max_concede is None

    def test_batting_first_achievable(self, ipl_matches):
        t = Tournament(ipl_matches)
        result = t.whatif_nrr(
            "Sunrisers Hyderabad",
            batting_first=True,
            runs_scored=200,
            overs_batted=Over("20.0"),
            all_out=False,
            max_overs=Over("20.0"),
            target_nrr=-1.0,  # easy target (below their actual NRR)
        )
        assert result.achievable is True
        assert result.max_concede is not None
        assert result.max_concede > 0

    def test_bowling_first_min_score(self, ipl_matches):
        t = Tournament(ipl_matches)
        result = t.whatif_nrr(
            "Royal Challengers Bengaluru",
            batting_first=False,
            runs_scored=160,
            overs_batted=Over("20.0"),
            all_out=False,
            max_overs=Over("20.0"),
            target_nrr=0.800,
        )
        assert result.min_score is not None
        assert isinstance(result.min_score, int)

    def test_scenario_string_not_empty(self, ipl_matches):
        t = Tournament(ipl_matches)
        result = t.whatif_nrr(
            "Gujarat Titans",
            batting_first=True,
            runs_scored=170,
            overs_batted=Over("20.0"),
            all_out=False,
            max_overs=Over("20.0"),
            target_nrr=0.0,
        )
        assert len(result.scenario) > 10

    def test_projected_nrr_near_target(self, ipl_matches):
        """
        The projected NRR at the boundary condition should be approximately
        equal to the target NRR (within rounding).
        """
        t = Tournament(ipl_matches)
        target = 0.300
        result = t.whatif_nrr(
            "Chennai Super Kings",
            batting_first=True,
            runs_scored=190,
            overs_batted=Over("20.0"),
            all_out=False,
            max_overs=Over("20.0"),
            target_nrr=target,
        )
        if result.achievable:
            assert abs(result.projected_nrr - target) < 0.01


# ---------------------------------------------------------------------------
# Qualification margin
# ---------------------------------------------------------------------------

class TestQualifyMargin:
    def test_qualify_by_more_points(self, ipl_matches):
        """Team with more points after their final match qualifies outright."""
        # Build a tiny 2-match tournament
        from cricket_nrr.loaders import from_dict
        m1 = from_dict({
            "match_id": "A", "team1": "India", "team2": "Australia",
            "innings1": {"runs": 200, "overs": "20.0", "wickets": 5, "all_out": False},
            "innings2": {"runs": 180, "overs": "20.0", "wickets": 8, "all_out": False},
            "result": "team1", "max_overs": 20,
        })
        m2 = from_dict({
            "match_id": "B", "team1": "England", "team2": "Australia",
            "innings1": {"runs": 170, "overs": "20.0", "wickets": 6, "all_out": False},
            "innings2": {"runs": 175, "overs": "20.0", "wickets": 5, "all_out": False},
            "result": "team2", "max_overs": 20,
        })
        t = Tournament([m1, m2])

        # Now India's final match:
        m_final = from_dict({
            "match_id": "C", "team1": "India", "team2": "England",
            "innings1": {"runs": 220, "overs": "20.0", "wickets": 3, "all_out": False},
            "innings2": {"runs": 180, "overs": "20.0", "wickets": 9, "all_out": False},
            "result": "team1", "max_overs": 20,
        })
        result = t.qualify_margin("India", "Australia", m_final)
        assert result.qualified is True
        assert result.points_after_team_chasing == 4
        assert result.points_after_team_to_overtake == 2
        assert "more points" in result.margin_description

    def test_qualify_result_has_description(self, ipl_matches):
        """QualifyResult.margin_description must be a non-empty string."""
        # Use real data with hypothetical final match
        from cricket_nrr.loaders import from_dict
        m_final = from_dict({
            "match_id": "75",
            "team1": "Royal Challengers Bengaluru",
            "team2": "Gujarat Titans",
            "innings1": {"runs": 200, "overs": "20.0", "wickets": 4, "all_out": False},
            "innings2": {"runs": 180, "overs": "20.0", "wickets": 7, "all_out": False},
            "result": "team1", "max_overs": 20,
        })
        t = Tournament(ipl_matches)
        qr = t.qualify_margin(
            "Royal Challengers Bengaluru", "Gujarat Titans", m_final
        )
        assert isinstance(qr.margin_description, str)
        assert len(qr.margin_description) > 5
        assert isinstance(qr.qualified, bool)

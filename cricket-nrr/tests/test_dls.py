"""
tests/test_dls.py
~~~~~~~~~~~~~~~~~
Tests for the DLSEngine — resource table, par scores, interpolation.
"""

import pytest
from cricket_nrr import DLSEngine, Over
from cricket_nrr.validators import InvalidOverError


@pytest.fixture
def engine():
    return DLSEngine(g50=245.0)


# ---------------------------------------------------------------------------
# Resource table spot checks (Standard Edition known values)
# ---------------------------------------------------------------------------

class TestResourceTable:
    def test_full_overs_no_wickets(self, engine):
        assert engine.resource_percentage(Over("50.0"), 0) == 100.0

    def test_25_overs_no_wickets(self, engine):
        # Standard Edition: 25 overs remaining, 0 wickets = 68.2%
        assert abs(engine.resource_percentage(Over("25.0"), 0) - 68.2) < 0.01

    def test_10_overs_5_wickets(self, engine):
        # Standard Edition: 10 overs remaining, 5 wickets = 26.4%
        assert abs(engine.resource_percentage(Over("10.0"), 5) - 26.4) < 0.1

    def test_zero_overs(self, engine):
        assert engine.resource_percentage(Over("0.0"), 0) == 0.0

    def test_all_out(self, engine):
        """10 wickets → always 0% resources."""
        assert engine.resource_percentage(Over("25.0"), 10) == 0.0
        assert engine.resource_percentage(Over("10.0"), 10) == 0.0

    def test_20_overs_0_wickets(self, engine):
        # T20 full resources: 20 overs remaining, 0 wickets = 59.5%
        assert abs(engine.resource_percentage(Over("20.0"), 0) - 59.5) < 0.1


# ---------------------------------------------------------------------------
# Interpolation for fractional overs
# ---------------------------------------------------------------------------

class TestInterpolation:
    def test_between_integer_rows(self, engine):
        """
        23.4 overs remaining should interpolate between 23 and 24.
        Row 24: 66.5%, Row 23: 64.8%.
        4/6 of the way through the over means we're between 23 and 24,
        closer to 23.
        """
        pct_24 = engine.resource_percentage(Over("24.0"), 0)  # 66.5
        pct_23 = engine.resource_percentage(Over("23.0"), 0)  # 64.8
        pct_interp = engine.resource_percentage(Over("23.4"), 0)
        # Should be between 64.8 and 66.5
        assert pct_23 < pct_interp < pct_24

    def test_half_over(self, engine):
        """19.3 overs remaining — interpolation midpoint."""
        pct_19 = engine.resource_percentage(Over("19.0"), 0)
        pct_20 = engine.resource_percentage(Over("20.0"), 0)
        pct_half = engine.resource_percentage(Over("19.3"), 0)
        assert pct_19 < pct_half < pct_20


# ---------------------------------------------------------------------------
# Par score — between-innings interruption
# ---------------------------------------------------------------------------

class TestBetweenInningsPar:
    def test_classic_50_over_scenario(self, engine):
        """
        Team 1: 250 in 50.0 overs.
        Rain wipes 25 overs → Team 2 gets 25 overs.
        Expected par score ~182 per Standard Edition.
        """
        par = engine.par_score(
            team1_score=250,
            team1_overs_faced=Over("50.0"),
            team1_max_overs=Over("50.0"),
            team1_wickets_lost=8,
            team2_overs_available=Over("25.0"),
        )
        # Standard Edition DLS table: R1=100%, R2=68.2%
        # Par = 250 + 245 * (68.2 - 100) / 100 = 250 - 77.91 ≈ 172
        assert 168 <= par <= 176, f"Par score {par} outside Standard Edition range"

    def test_par_equal_score_wins(self, engine):
        """
        If Team 2's score exactly equals par, Team 1 wins (tie goes to Team 1
        since the target is par+1).
        """
        par = engine.par_score(
            team1_score=200,
            team1_overs_faced=Over("50.0"),
            team1_max_overs=Over("50.0"),
            team1_wickets_lost=6,
            team2_overs_available=Over("50.0"),
        )
        # Full 50 overs available → par == team1_score
        assert par == 200

    def test_t20_between_innings(self, engine):
        """T20: Team 1 scored 180 in 20.0 overs. Team 2 gets 15 overs."""
        par = engine.par_score(
            team1_score=180,
            team1_overs_faced=Over("20.0"),
            team1_max_overs=Over("20.0"),
            team1_wickets_lost=5,
            team2_overs_available=Over("15.0"),
        )
        assert par > 0
        assert par < 180  # fewer overs → lower par


# ---------------------------------------------------------------------------
# Par score — mid-innings interruption
# ---------------------------------------------------------------------------

class TestMidInningsPar:
    def test_mid_innings_interruption(self, engine):
        """
        Team 1: 250 in 50 overs.
        Team 2 at 80/3 after 20 overs, then rain interrupts.
        They now have 15 overs left instead of 30.
        """
        par = engine.par_score(
            team1_score=250,
            team1_overs_faced=Over("50.0"),
            team1_max_overs=Over("50.0"),
            team1_wickets_lost=8,
            team2_overs_available=Over("15.0"),
            team2_wickets_lost=3,
            team2_overs_used=Over("20.0"),
        )
        assert par > 0

    def test_mid_innings_par_lower_than_full(self, engine):
        """Fewer overs available mid-innings → lower par score."""
        par_full = engine.par_score(
            team1_score=250,
            team1_overs_faced=Over("50.0"),
            team1_max_overs=Over("50.0"),
            team1_wickets_lost=8,
            team2_overs_available=Over("50.0"),
        )
        par_reduced = engine.par_score(
            team1_score=250,
            team1_overs_faced=Over("50.0"),
            team1_max_overs=Over("50.0"),
            team1_wickets_lost=8,
            team2_overs_available=Over("30.0"),
            team2_wickets_lost=0,
            team2_overs_used=Over("0.0"),
        )
        assert par_reduced < par_full


# ---------------------------------------------------------------------------
# Revised target
# ---------------------------------------------------------------------------

class TestRevisedTarget:
    def test_revised_target_is_par_plus_one(self, engine):
        par = engine.par_score(
            team1_score=250,
            team1_overs_faced=Over("50.0"),
            team1_max_overs=Over("50.0"),
            team1_wickets_lost=8,
            team2_overs_available=Over("25.0"),
        )
        target = engine.revised_target(
            team1_score=250,
            team1_overs_faced=Over("50.0"),
            team1_max_overs=Over("50.0"),
            team1_wickets_lost=8,
            team2_overs_available=Over("25.0"),
        )
        assert target == par + 1


# ---------------------------------------------------------------------------
# G50 configuration
# ---------------------------------------------------------------------------

class TestG50:
    def test_default_g50(self):
        engine = DLSEngine()
        assert engine.g50 == 245.0

    def test_custom_g50_womens(self):
        engine = DLSEngine(g50=200.0)
        assert engine.g50 == 200.0

    def test_invalid_g50(self):
        from cricket_nrr.validators import validate_g50
        with pytest.raises(ValueError):
            validate_g50(-1.0)
        with pytest.raises(ValueError):
            validate_g50(0.0)

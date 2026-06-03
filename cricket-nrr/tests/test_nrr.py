"""
tests/test_nrr.py
~~~~~~~~~~~~~~~~~
Tests for MatchNRR and TeamNRRPool — all 5 ICC edge cases.
"""

import datetime
from fractions import Fraction
import pytest

from cricket_nrr import InningsRecord, MatchRecord, MatchNRR, Over, TeamNRRPool


# ---------------------------------------------------------------------------
# Rule 1: All-out → full quota overs
# ---------------------------------------------------------------------------

class TestAllOutRule:
    def test_allout_uses_full_quota(self, allout_match):
        """
        CSK all out for 127 in 19.4 overs → NRR denominator must be 20.0.
        CSK run rate = 127 / 20.0 = 6.35 (not 127 / 19.667)
        """
        nrr = MatchNRR(allout_match)
        # CSK is team1
        expected = Fraction(20)   # 20.0 full overs
        assert nrr.team1_overs_for == expected, (
            f"Expected Fraction(20) but got {nrr.team1_overs_for}"
        )

    def test_allout_run_rate(self, allout_match):
        """127 / 20.0 = Fraction(127, 20) = 6.35 rpo"""
        assert allout_match.innings1.run_rate == Fraction(127, 20)

    def test_not_allout_uses_actual_overs(self, simple_t20_match):
        """SRH scored 201 in 20.0 overs, not all out — use 20.0 (same here)."""
        nrr = MatchNRR(simple_t20_match)
        assert nrr.team1_overs_for == Fraction(20)

    def test_chasing_team_allout(self):
        """KKR all out for 161 in 16.0 overs → NRR denominator = 20.0."""
        inn1 = InningsRecord(226, Over("20.0"), 8, False, Over("20.0"))
        inn2 = InningsRecord(161, Over("16.0"), 10, True, Over("20.0"))
        match = MatchRecord(
            "6", datetime.date(2026, 4, 2),
            "Sunrisers Hyderabad", "Kolkata Knight Riders",
            inn1, inn2, "team1",
        )
        nrr = MatchNRR(match)
        assert nrr.team2_overs_for == Fraction(20), (
            "All-out team must use full 20-over quota"
        )
        # Run rate = 161 / 20.0 = 8.05
        assert inn2.run_rate == Fraction(161, 20)


# ---------------------------------------------------------------------------
# Rule 2: Super over — still counts for NRR (regulation innings only)
# ---------------------------------------------------------------------------

class TestSuperOver:
    def test_valid_for_nrr(self):
        """Super-over match: regulation innings count, super-over excluded."""
        inn1 = InningsRecord(180, Over("20.0"), 6, False, Over("20.0"))
        inn2 = InningsRecord(180, Over("20.0"), 7, False, Over("20.0"))
        match = MatchRecord(
            "SO", datetime.date(2026, 5, 1),
            "India", "Australia", inn1, inn2, "tie",
            super_over_played=True,
        )
        nrr = MatchNRR(match)
        # Tied regulation match with super over still counts toward NRR
        assert nrr.is_valid_for_nrr() is True


# ---------------------------------------------------------------------------
# Rule 3: No-result exclusion
# ---------------------------------------------------------------------------

class TestNoResult:
    def test_no_result_invalid(self, no_result_match):
        nrr = MatchNRR(no_result_match)
        assert nrr.is_valid_for_nrr() is False

    def test_no_result_not_counted(self, no_result_match):
        pool = TeamNRRPool("Kolkata Knight Riders")
        pool.add_match(no_result_match)
        # Pool should be empty
        assert pool.runs_for == 0
        assert pool.overs_for == Fraction(0)

    def test_two_no_results_in_ipl(self, ipl_matches):
        """Matches 12 and 38 in IPL 2026 are No Result."""
        no_results = [m for m in ipl_matches if m.result == "no_result"]
        assert len(no_results) == 2, (
            f"Expected 2 no-result matches, found {len(no_results)}"
        )


# ---------------------------------------------------------------------------
# Rule 4: DLS match overs credit
# ---------------------------------------------------------------------------

class TestDLSOversCredit:
    def test_dls_overs_credited(self):
        """
        DLS match: Team 1 faced 11.0 overs, Team 2 faced 11.0 overs.
        Team 1's NRR overs = overs actually bowled to Team 2 = 11.0.
        """
        inn1 = InningsRecord(150, Over("11.0"), 3, False, Over("11.0"))
        inn2 = InningsRecord(123, Over("11.0"), 9, False, Over("11.0"))
        match = MatchRecord(
            "13", datetime.date(2026, 4, 7),
            "Rajasthan Royals", "Mumbai Indians",
            inn1, inn2, "team1",
            dls_affected=True,
            dls_team1_overs_credited=Over("11.0"),
        )
        nrr = MatchNRR(match)
        assert nrr.team1_overs_for == Fraction(11)
        assert nrr.team2_overs_against == Fraction(11)


# ---------------------------------------------------------------------------
# Rule 5: Exact arithmetic (no floating-point drift)
# ---------------------------------------------------------------------------

class TestExactArithmetic:
    def test_fraction_denominator(self, simple_t20_match):
        nrr = MatchNRR(simple_t20_match)
        # overs_against for team1 = 15.4 overs = 94 balls = Fraction(94, 6) = Fraction(47, 3)
        assert nrr.team1_overs_against == Fraction(94, 6)

    def test_pool_overs_exact(self, ipl_matches):
        pool = TeamNRRPool.from_matches("Royal Challengers Bengaluru", ipl_matches)
        # Overs must be a Fraction, not a float
        assert isinstance(pool.overs_for, Fraction)
        assert isinstance(pool.overs_against, Fraction)


# ---------------------------------------------------------------------------
# TeamNRRPool — cumulative aggregation correctness
# ---------------------------------------------------------------------------

class TestTeamNRRPool:
    def test_cumulative_not_averaged(self, ipl_matches):
        """
        NRR must be cumulative totals, not average of per-match NRRs.
        Verify by computing manually for one team.
        """
        team = "Royal Challengers Bengaluru"
        pool = TeamNRRPool.from_matches(team, ipl_matches)

        # Manual calculation
        total_rf = Fraction(0)
        total_of = Fraction(0)
        total_ra = Fraction(0)
        total_oa = Fraction(0)
        for m in ipl_matches:
            mnrr = MatchNRR(m)
            if not mnrr.is_valid_for_nrr():
                continue
            if team not in m.teams:
                continue
            total_rf += Fraction(mnrr.runs_for(team))
            total_of += mnrr.overs_for(team)
            total_ra += Fraction(mnrr.runs_against(team))
            total_oa += mnrr.overs_against(team)

        manual_nrr = float(total_rf / total_of - total_ra / total_oa)
        assert abs(pool.nrr() - manual_nrr) < 1e-9

    def test_nrr_sign(self, ipl_matches):
        """Winning team (RCB) should have positive NRR in IPL 2026."""
        pool = TeamNRRPool.from_matches("Royal Challengers Bengaluru", ipl_matches)
        assert pool.nrr() > 0, "Tournament winner should have positive NRR"

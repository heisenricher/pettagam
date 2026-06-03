"""
tests/conftest.py
~~~~~~~~~~~~~~~~~
Shared fixtures for the cricket-nrr test suite.
"""

import datetime
from pathlib import Path
import pytest

from cricket_nrr import InningsRecord, MatchRecord, Over
from cricket_nrr.loaders import from_csv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
MATCHES_CSV = ROOT.parent / "matches.csv"             # ../matches.csv
FINAL_CSV = ROOT.parent / "2026_ipl_final_dataset" / "match_74_gt_vs_rcb_final.csv"


# ---------------------------------------------------------------------------
# Simple match fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_t20_match():
    """RCB beat SRH by 6 wickets — Match 1 of IPL 2026."""
    inn1 = InningsRecord(
        runs=201, overs_faced=Over("20.0"), wickets_lost=9,
        all_out=False, max_overs=Over("20.0"),
    )
    inn2 = InningsRecord(
        runs=203, overs_faced=Over("15.4"), wickets_lost=4,
        all_out=False, max_overs=Over("20.0"),
    )
    return MatchRecord(
        match_id="1",
        date=datetime.date(2026, 3, 28),
        team1="Sunrisers Hyderabad",
        team2="Royal Challengers Bengaluru",
        innings1=inn1,
        innings2=inn2,
        result="team2",
    )


@pytest.fixture
def allout_match():
    """
    CSK vs RR, Match 3 — CSK all out for 127 in 19.4 overs.
    CSK's NRR denominator must be 20.0, not 19.4.
    """
    inn1 = InningsRecord(
        runs=127, overs_faced=Over("19.4"), wickets_lost=10,
        all_out=True, max_overs=Over("20.0"),
    )
    inn2 = InningsRecord(
        runs=128, overs_faced=Over("12.1"), wickets_lost=2,
        all_out=False, max_overs=Over("20.0"),
    )
    return MatchRecord(
        match_id="3",
        date=datetime.date(2026, 3, 30),
        team1="Chennai Super Kings",
        team2="Rajasthan Royals",
        innings1=inn1,
        innings2=inn2,
        result="team2",
    )


@pytest.fixture
def no_result_match():
    """Match 12 — KKR vs PBKS, No Result."""
    inn1 = InningsRecord(
        runs=25, overs_faced=Over("3.4"), wickets_lost=2,
        all_out=False, max_overs=Over("20.0"),
    )
    inn2 = InningsRecord(
        runs=0, overs_faced=Over("0.0"), wickets_lost=0,
        all_out=False, max_overs=Over("20.0"),
    )
    return MatchRecord(
        match_id="12",
        date=datetime.date(2026, 4, 6),
        team1="Kolkata Knight Riders",
        team2="Punjab Kings",
        innings1=inn1,
        innings2=inn2,
        result="no_result",
    )


@pytest.fixture
def ipl_matches():
    """All 75 IPL 2026 matches loaded from real CSV."""
    if not MATCHES_CSV.exists():
        pytest.skip(f"matches.csv not found at {MATCHES_CSV}")
    return from_csv(str(MATCHES_CSV))

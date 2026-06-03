"""
cricket_nrr.formatters
~~~~~~~~~~~~~~~~~~~~~~~
String formatting utilities for NRR values, over notation, and scorecards.

All formatters are also available as pandas-compatible vectorised functions
for mapping across Series/DataFrame columns.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Union

__all__ = [
    "format_nrr",
    "format_over",
    "format_score",
    "nrr_series",
    "over_series",
    "score_series",
]


# ---------------------------------------------------------------------------
# NRR formatter
# ---------------------------------------------------------------------------


def format_nrr(nrr: float, decimals: int = 3) -> str:
    """
    Format an NRR value as a signed string with fixed decimal places.

    Parameters
    ----------
    nrr : float
        Net Run Rate value (may be negative).
    decimals : int
        Number of decimal places (default 3).

    Returns
    -------
    str
        e.g. ``'+1.425'``, ``'-0.312'``, ``'+0.000'``

    Examples
    --------
    >>> format_nrr(1.425)
    '+1.425'
    >>> format_nrr(-0.312)
    '-0.312'
    >>> format_nrr(0.0)
    '+0.000'
    >>> format_nrr(1.2, decimals=2)
    '+1.20'
    """
    fmt = f"+.{decimals}f" if nrr >= 0 else f".{decimals}f"
    return format(nrr, fmt)


# ---------------------------------------------------------------------------
# Over formatter
# ---------------------------------------------------------------------------


def format_over(over: "Union[str, float, int]") -> str:
    """
    Return a canonical cricket over-notation string.

    Accepts the same types as :class:`~cricket_nrr.Over`.

    >>> format_over(19.3)
    '19.3'
    >>> format_over("20.0")
    '20.0'
    >>> format_over(20)
    '20.0'
    """
    from .overs import Over as _Over
    return _Over(over).notation


# ---------------------------------------------------------------------------
# Score formatter
# ---------------------------------------------------------------------------


def format_score(runs: int, wickets: int) -> str:
    """
    Format a scorecard score as ``'runs/wickets'``.

    >>> format_score(155, 8)
    '155/8'
    >>> format_score(203, 4)
    '203/4'
    """
    return f"{runs}/{wickets}"


def parse_score(score_str: str) -> "tuple[int, int]":
    """
    Parse a scorecard string into ``(runs, wickets)``.

    >>> parse_score("155/8")
    (155, 8)
    """
    parts = score_str.strip().split("/")
    if len(parts) != 2:
        raise ValueError(
            f"Cannot parse score string {score_str!r}. "
            "Expected format: 'runs/wickets' (e.g. '155/8')."
        )
    return int(parts[0]), int(parts[1])


# ---------------------------------------------------------------------------
# Pandas vectorised helpers
# ---------------------------------------------------------------------------


def nrr_series(series: "pd.Series", decimals: int = 3) -> "pd.Series":  # type: ignore[type-arg]
    """
    Apply :func:`format_nrr` across a pandas Series.

    Requires pandas (optional dependency).

    >>> import pandas as pd
    >>> nrr_series(pd.Series([1.425, -0.312, 0.0]))
    0    +1.425
    1    -0.312
    2    +0.000
    dtype: object
    """
    return series.map(lambda v: format_nrr(float(v), decimals))


def over_series(series: "pd.Series") -> "pd.Series":  # type: ignore[type-arg]
    """
    Convert a pandas Series of raw over values to canonical notation strings.

    Requires pandas (optional dependency).

    >>> import pandas as pd
    >>> over_series(pd.Series([19.3, "20.0", 20]))
    0    19.3
    1    20.0
    2    20.0
    dtype: object
    """
    return series.map(format_over)


def score_series(runs_series: "pd.Series", wickets_series: "pd.Series") -> "pd.Series":  # type: ignore[type-arg]
    """
    Combine runs and wickets Series into formatted score strings.

    Requires pandas (optional dependency).

    >>> import pandas as pd
    >>> score_series(pd.Series([155, 203]), pd.Series([8, 4]))
    0    155/8
    1    203/4
    dtype: object
    """
    return runs_series.combine(wickets_series, lambda r, w: format_score(int(r), int(w)))

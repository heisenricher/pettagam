"""
cricket_nrr.overs
~~~~~~~~~~~~~~~~~
The Core Conversion Engine — cricket's base-6 over arithmetic.

Cricket uses a base-6 decimal notation for overs.  ``14.3`` means
*14 full overs and 3 balls*, NOT fourteen-point-three in decimal math.
This means native Python floats are **wrong** for over arithmetic:

    >>> 19.3 + 0.4   # naive Python
    19.700000000000003   # WRONG — should be 20.1 (20 overs, 1 ball)

This module provides :class:`Over`, backed by :class:`fractions.Fraction`
(total balls / 6) for exact, lossless arithmetic, with a full operator
protocol so downstream code stays readable:

    >>> Over("19.3") + Over("0.4")
    Over('20.1')
    >>> Over("20.0") - Over("0.3")
    Over('19.3')
    >>> Over("14.2").balls
    86
    >>> Over.from_balls(86).notation
    '14.2'
"""

from __future__ import annotations

from fractions import Fraction
from typing import Union

from .validators import validate_over_notation, InvalidOverError  # noqa: F401

__all__ = ["Over", "InvalidOverError"]

# Type alias for anything coercible to an Over.
OverLike = Union["Over", float, int, str]


class Over:
    """
    A cricket over count stored as an exact :class:`~fractions.Fraction`.

    **Notation**: ``19.3`` = 19 full overs and 3 balls = 117 total balls
    = ``Fraction(117, 6)`` internally.

    Construction
    ------------
    >>> Over(19.3)            # from float
    Over('19.3')
    >>> Over("19.3")          # from string
    Over('19.3')
    >>> Over(20)              # int → 20 whole overs
    Over('20.0')
    >>> Over.from_balls(86)   # 14 overs + 2 balls
    Over('14.2')

    Arithmetic
    ----------
    >>> Over("19.3") + Over("0.4")
    Over('20.1')
    >>> Over("20.0") - Over("0.3")
    Over('19.3')
    >>> Over("20.0") * 2          # returns Fraction (used in NRR calc)
    Fraction(40, 1)
    >>> Over("14.2") / Over("20.0")  # dimensionless ratio
    Fraction(43, 60)

    Validation
    ----------
    >>> Over(19.6)   # raises InvalidOverError — ball 6 completes the over
    >>> Over(19.7)   # raises InvalidOverError
    >>> Over(-0.1)   # raises InvalidOverError
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, notation: OverLike) -> None:
        if isinstance(notation, Over):
            self._fraction: Fraction = notation._fraction
            return
        full, balls = validate_over_notation(notation)
        self._fraction = Fraction(full * 6 + balls, 6)

    @classmethod
    def from_balls(cls, total_balls: int) -> "Over":
        """
        Construct from an absolute ball count.

        >>> Over.from_balls(119)
        Over('19.5')
        >>> Over.from_balls(120)
        Over('20.0')
        """
        if total_balls < 0:
            raise InvalidOverError(
                f"Ball count cannot be negative (got {total_balls})."
            )
        obj = cls.__new__(cls)
        obj._fraction = Fraction(total_balls, 6)
        return obj

    @classmethod
    def from_fraction(cls, frac: Fraction) -> "Over":
        """Construct from an exact :class:`~fractions.Fraction` of overs."""
        if frac < 0:
            raise InvalidOverError("Over fraction cannot be negative.")
        obj = cls.__new__(cls)
        obj._fraction = frac
        return obj

    # ------------------------------------------------------------------
    # Core properties
    # ------------------------------------------------------------------

    @property
    def balls(self) -> int:
        """Total number of legal balls bowled."""
        return int(self._fraction * 6)

    @property
    def full_overs(self) -> int:
        """Number of complete overs (floor division)."""
        return self.balls // 6

    @property
    def extra_balls(self) -> int:
        """Balls bowled within the current (incomplete) over (0–5)."""
        return self.balls % 6

    @property
    def notation(self) -> str:
        """
        Standard cricket over notation string.

        >>> Over.from_balls(117).notation
        '19.3'
        >>> Over.from_balls(120).notation
        '20.0'
        """
        return f"{self.full_overs}.{self.extra_balls}"

    @property
    def as_fraction(self) -> Fraction:
        """
        Exact fractional value in *overs*.

        Use this as the denominator in NRR and run-rate calculations to
        avoid floating-point rounding drift.

        >>> Over("14.2").as_fraction
        Fraction(43, 6)
        """
        return self._fraction

    @property
    def as_decimal(self) -> float:
        """
        Approximate ``float`` representation.

        .. warning::
            Do **not** use this as an NRR denominator.  Use
            :attr:`as_fraction` instead.
        """
        return float(self._fraction)

    # ------------------------------------------------------------------
    # Arithmetic operators
    # ------------------------------------------------------------------

    def __add__(self, other: OverLike) -> "Over":
        """
        >>> Over("19.3") + Over("0.4")
        Over('20.1')
        """
        return Over.from_fraction(self._fraction + _coerce(other)._fraction)

    def __radd__(self, other: OverLike) -> "Over":
        return self.__add__(other)

    def __sub__(self, other: OverLike) -> "Over":
        """
        >>> Over("20.0") - Over("0.3")
        Over('19.3')
        """
        result = self._fraction - _coerce(other)._fraction
        if result < 0:
            raise InvalidOverError(
                f"Cannot subtract {other!r} from {self!r}: result would be negative."
            )
        return Over.from_fraction(result)

    def __mul__(self, scalar: "Union[int, float, Fraction]") -> Fraction:
        """
        Multiply by a scalar — returns a :class:`~fractions.Fraction`.

        >>> Over("20.0") * 2
        Fraction(40, 1)
        """
        return self._fraction * Fraction(scalar).limit_denominator(10_000)

    def __rmul__(self, scalar: "Union[int, float, Fraction]") -> Fraction:
        return self.__mul__(scalar)

    def __truediv__(self, other: OverLike) -> Fraction:
        """
        Divide one over count by another — dimensionless ratio.

        >>> Over("14.2") / Over("20.0")
        Fraction(43, 60)
        """
        other = _coerce(other)
        if other._fraction == 0:
            raise ZeroDivisionError("Cannot divide by zero overs.")
        return self._fraction / other._fraction

    # ------------------------------------------------------------------
    # Comparison operators
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Over):
            return self._fraction == other._fraction
        try:
            return self._fraction == _coerce(other)._fraction  # type: ignore[arg-type]
        except (InvalidOverError, TypeError):
            return NotImplemented

    def __lt__(self, other: OverLike) -> bool:
        return self._fraction < _coerce(other)._fraction

    def __le__(self, other: OverLike) -> bool:
        return self._fraction <= _coerce(other)._fraction

    def __gt__(self, other: OverLike) -> bool:
        return self._fraction > _coerce(other)._fraction

    def __ge__(self, other: OverLike) -> bool:
        return self._fraction >= _coerce(other)._fraction

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Over('{self.notation}')"

    def __str__(self) -> str:
        return self.notation

    def __hash__(self) -> int:
        return hash(self._fraction)

    def __bool__(self) -> bool:
        return self._fraction != 0

    # ------------------------------------------------------------------
    # Pandas / NumPy vectorisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def from_notation(value: "Union[str, float, int]") -> "Over":
        """
        Factory suitable for ``pd.Series.map`` / ``df[col].apply``.

        >>> import pandas as pd
        >>> pd.Series(["19.3", "20.0", "14.2"]).map(Over.from_notation)
        0    Over('19.3')
        1    Over('20.0')
        2    Over('14.2')
        dtype: object
        """
        return Over(value)

    @staticmethod
    def total_balls_series(series: "pd.Series") -> "pd.Series":  # type: ignore[type-arg]
        """
        Convert a pandas Series of over-notation values to total balls.

        Requires pandas (optional dependency).

        >>> import pandas as pd
        >>> Over.total_balls_series(pd.Series(["19.3", "14.2"]))
        0    117
        1     86
        dtype: int64
        """
        return series.map(lambda v: Over(v).balls)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _coerce(value: OverLike) -> Over:
    """Coerce a raw value into an :class:`Over` if not already one."""
    if isinstance(value, Over):
        return value
    return Over(value)

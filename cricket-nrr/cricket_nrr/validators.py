"""
cricket_nrr.validators
~~~~~~~~~~~~~~~~~~~~~~~
Input validation with descriptive cricket-domain error messages.
All public functions raise ``InvalidOverError`` or ``ValueError`` with
enough context for the caller to understand exactly what went wrong.
"""

from __future__ import annotations

__all__ = [
    "InvalidOverError",
    "InvalidWicketError",
    "InvalidRunsError",
    "validate_over_notation",
    "validate_max_overs",
    "validate_wickets",
    "validate_runs",
    "validate_g50",
]


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class InvalidOverError(ValueError):
    """
    Raised when a cricket over value is mathematically impossible.

    Cricket uses base-6 within each over (balls 1–6).
    A notation like ``19.6`` or ``19.9`` is illegal because the 6th
    delivery *completes* that over, making the next legal value ``20.0``.

    Examples of invalid inputs
    --------------------------
    >>> from cricket_nrr import Over
    >>> Over(19.6)   # raises InvalidOverError
    >>> Over(-0.1)   # raises InvalidOverError
    """


class InvalidWicketError(ValueError):
    """Raised when a wicket count is outside the legal range [0, 10]."""


class InvalidRunsError(ValueError):
    """Raised when a run count is negative or non-integer."""


# ---------------------------------------------------------------------------
# Over validation
# ---------------------------------------------------------------------------


def validate_over_notation(value: "float | int | str") -> "tuple[int, int]":
    """
    Parse and validate a cricket over notation string or number.

    Returns ``(full_overs, extra_balls)`` if valid.

    Accepts
    -------
    - ``float``  : e.g. ``19.3``, ``20.0``, ``0.0``
    - ``int``    : e.g. ``20`` (treated as ``20.0``)
    - ``str``    : e.g. ``"19.3"``, ``"20"``

    Raises
    ------
    InvalidOverError
        - Ball digit is >= 6 (e.g. 19.6, 19.7 …)
        - Value is negative
        - String cannot be parsed as a number

    Examples
    --------
    >>> validate_over_notation(19.3)
    (19, 3)
    >>> validate_over_notation("14.2")
    (14, 2)
    >>> validate_over_notation(20)
    (20, 0)
    """
    # Check numeric negativity BEFORE string conversion.
    # "-0.5" → str splits to ["-0", "5"] → int("-0") == 0, missing the sign.
    # We must NOT catch InvalidOverError here (it IS a ValueError subclass).
    _neg_err: "InvalidOverError | None" = None
    try:
        numeric = float(value)
        if numeric < 0:
            _neg_err = InvalidOverError(
                f"Over count cannot be negative (got {value!r})."
            )
    except (TypeError, ValueError):
        pass  # non-numeric — will be caught and reported below
    if _neg_err is not None:
        raise _neg_err

    try:
        s = str(value).strip()
        parts = s.split(".")
        if len(parts) > 2:
            raise InvalidOverError(
                f"Invalid over notation {value!r}: more than one decimal point."
            )
        full_overs = int(parts[0])
        extra_balls = int(parts[1]) if len(parts) == 2 else 0
    except (TypeError, ValueError) as exc:
        raise InvalidOverError(
            f"Cannot parse {value!r} as a cricket over notation. "
            "Expected a value like 19.3 (19 overs and 3 balls)."
        ) from exc

    if full_overs < 0:
        raise InvalidOverError(
            f"Over count cannot be negative (got {value!r})."
        )
    if extra_balls < 0:
        raise InvalidOverError(
            f"Ball count within an over cannot be negative (got {value!r})."
        )
    if extra_balls >= 6:
        suggestion = (
            f"{full_overs + 1}.{extra_balls - 6}"
            if extra_balls - 6 < 6
            else f"{full_overs + 1}.0"
        )
        raise InvalidOverError(
            f"Invalid over notation {value!r}: the ball digit is {extra_balls}, "
            "but a cricket over only has 6 balls (0–5 in mid-over notation). "
            f"Ball 6 completes the over — did you mean {suggestion!r}?"
        )
    return full_overs, extra_balls


def validate_max_overs(value: "float | int | str") -> None:
    """Ensure max_overs is a whole-number over (e.g. 20.0 or 50.0)."""
    full, balls = validate_over_notation(value)
    if balls != 0:
        raise InvalidOverError(
            f"max_overs must be a whole number of overs (e.g. 20.0 or 50.0), "
            f"got {value!r}."
        )


# ---------------------------------------------------------------------------
# Wicket validation
# ---------------------------------------------------------------------------


def validate_wickets(value: int, *, field: str = "wickets") -> None:
    """
    Ensure a wicket count is in [0, 10].

    Raises
    ------
    InvalidWicketError
    """
    if not isinstance(value, int):
        raise InvalidWicketError(
            f"{field} must be an integer, got {type(value).__name__!r}."
        )
    if not (0 <= value <= 10):
        raise InvalidWicketError(
            f"{field} must be between 0 and 10 (got {value})."
        )


# ---------------------------------------------------------------------------
# Runs validation
# ---------------------------------------------------------------------------


def validate_runs(value: int, *, field: str = "runs") -> None:
    """
    Ensure a run count is a non-negative integer.

    Raises
    ------
    InvalidRunsError
    """
    if not isinstance(value, int):
        raise InvalidRunsError(
            f"{field} must be an integer, got {type(value).__name__!r}."
        )
    if value < 0:
        raise InvalidRunsError(
            f"{field} cannot be negative (got {value})."
        )


# ---------------------------------------------------------------------------
# G50 validation
# ---------------------------------------------------------------------------


def validate_g50(value: float) -> None:
    """Ensure G50 is a positive number."""
    if value <= 0:
        raise ValueError(
            f"G50 (average score in a full innings) must be positive, "
            f"got {value}. Typical values: 245 (men's international / IPL), "
            "200 (women's, U19, associate members)."
        )

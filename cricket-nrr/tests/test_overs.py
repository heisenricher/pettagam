"""
tests/test_overs.py
~~~~~~~~~~~~~~~~~~~
Tests for the Over class — arithmetic, validation, and edge cases.
"""

import pytest
from fractions import Fraction
from cricket_nrr import Over
from cricket_nrr.validators import InvalidOverError


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_from_float(self):
        o = Over(19.3)
        assert o.full_overs == 19
        assert o.extra_balls == 3

    def test_from_string(self):
        o = Over("19.3")
        assert o.full_overs == 19
        assert o.extra_balls == 3

    def test_from_int(self):
        o = Over(20)
        assert o.full_overs == 20
        assert o.extra_balls == 0

    def test_from_over(self):
        o1 = Over("14.2")
        o2 = Over(o1)  # copy construction
        assert o1 == o2

    def test_from_balls(self):
        assert Over.from_balls(117) == Over("19.3")
        assert Over.from_balls(120) == Over("20.0")
        assert Over.from_balls(86) == Over("14.2")

    def test_zero(self):
        assert Over("0.0").balls == 0
        assert Over(0).balls == 0


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

class TestProperties:
    def test_balls(self):
        assert Over("19.3").balls == 117    # 19*6 + 3
        assert Over("14.2").balls == 86     # 14*6 + 2
        assert Over("20.0").balls == 120

    def test_notation(self):
        assert Over.from_balls(117).notation == "19.3"
        assert Over.from_balls(120).notation == "20.0"
        assert Over.from_balls(86).notation == "14.2"

    def test_as_fraction(self):
        assert Over("14.2").as_fraction == Fraction(86, 6)
        assert Over("20.0").as_fraction == Fraction(20, 1)

    def test_full_overs_and_extra_balls(self):
        o = Over("19.5")
        assert o.full_overs == 19
        assert o.extra_balls == 5


# ---------------------------------------------------------------------------
# Arithmetic — GOLDEN VALUES
# ---------------------------------------------------------------------------

class TestArithmetic:
    def test_add_crosses_over(self):
        result = Over("19.3") + Over("0.4")
        assert result == Over("20.1"), f"Got {result}"

    def test_add_whole_overs(self):
        assert Over("5.0") + Over("3.0") == Over("8.0")

    def test_add_with_balls(self):
        # 3.4 + 0.2 = 3.6? No — 3 overs + 4 balls + 2 balls = 3 overs + 6 balls = 4.0
        assert Over("3.4") + Over("0.2") == Over("4.0")

    def test_sub_basic(self):
        assert Over("20.0") - Over("0.3") == Over("19.3")

    def test_sub_exact(self):
        assert Over("14.2") - Over("0.2") == Over("14.0")

    def test_sub_crosses_back(self):
        assert Over("20.1") - Over("0.4") == Over("19.3")

    def test_sub_negative_raises(self):
        with pytest.raises(InvalidOverError):
            Over("5.0") - Over("10.0")

    def test_mul_scalar(self):
        result = Over("20.0") * 2
        assert result == Fraction(40, 1)

    def test_mul_fraction(self):
        result = Over("20.0") * Fraction(1, 2)
        assert result == Fraction(10, 1)

    def test_div_over(self):
        ratio = Over("14.2") / Over("20.0")
        assert ratio == Fraction(86, 120)   # = Fraction(43, 60)

    def test_div_zero_raises(self):
        with pytest.raises(ZeroDivisionError):
            Over("5.0") / Over("0.0")

    def test_radd_numeric(self):
        # 0 + Over("5.0") should work (for sum() usage)
        result = Over("5.0") + Over("0.0")
        assert result == Over("5.0")


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

class TestComparison:
    def test_eq(self):
        assert Over("19.3") == Over("19.3")
        assert Over("20.0") == Over(20)

    def test_lt(self):
        assert Over("19.3") < Over("20.0")

    def test_gt(self):
        assert Over("20.0") > Over("19.3")

    def test_le_equal(self):
        assert Over("19.3") <= Over("19.3")

    def test_ge_equal(self):
        assert Over("20.0") >= Over("20.0")


# ---------------------------------------------------------------------------
# Validation — MUST raise InvalidOverError
# ---------------------------------------------------------------------------

class TestValidation:
    @pytest.mark.parametrize("bad", [
        19.6, 19.7, 19.8, 19.9,    # ball digit >= 6
        "19.6", "14.6", "0.6",
        -1.0,                        # clearly negative (int part is -1)
        "abc",                        # non-numeric
        "-1.0", "-0.5",              # negative strings
    ])
    def test_invalid_raises(self, bad):
        with pytest.raises(InvalidOverError):
            Over(bad)

    @pytest.mark.parametrize("good", [
        0.0, 0.1, 0.5, 14.2, 19.3, 19.5, 20.0, 50.0,
        "19.3", "20.0", "0.0", 20, 0,
    ])
    def test_valid_passes(self, good):
        Over(good)  # should not raise


# ---------------------------------------------------------------------------
# Repr / str / bool
# ---------------------------------------------------------------------------

class TestDunder:
    def test_repr(self):
        assert repr(Over("19.3")) == "Over('19.3')"

    def test_str(self):
        assert str(Over("19.3")) == "19.3"

    def test_bool_nonzero(self):
        assert bool(Over("5.0")) is True

    def test_bool_zero(self):
        assert bool(Over("0.0")) is False

    def test_hash(self):
        s = {Over("19.3"), Over("19.3")}
        assert len(s) == 1

"""Money helpers for the generator: integer paise in, integer paise out.

Why: random draws are floats by nature, but no money value may be carried as one.
`scale` turns a random multiplier into a Decimal and quantizes to whole paise at once.
"""

from decimal import ROUND_HALF_UP, Decimal

ONE = Decimal(1)
_PAISE = Decimal(1)


def scale(amount: int, factor: float) -> int:
    """Return `amount` (paise) times `factor`, rounded half-up to whole paise, never negative."""
    value = (Decimal(amount) * Decimal(repr(factor))).quantize(_PAISE, rounding=ROUND_HALF_UP)
    return max(0, int(value))


def rupees(value: int) -> int:
    """Whole rupees to paise."""
    return value * 100


def round_to(amount: int, step: int) -> int:
    """Round paise to the nearest `step` paise (e.g. 100_00 for ₹100), half-up, at least one step."""
    units = (Decimal(amount) / Decimal(step)).quantize(ONE, rounding=ROUND_HALF_UP)
    return max(step, int(units) * step)


def emi(principal: int, annual_rate: Decimal, months: int) -> int:
    """Monthly instalment in paise: EMI = P·i·(1+i)^n / ((1+i)^n - 1), i = annual_rate / 12.

    Formula from the finance-domain skill; i = 0 gives P/n. Rounded half-up to whole paise.
    """
    if months <= 0:
        raise ValueError("tenure must be positive")
    p = Decimal(principal)
    i = annual_rate / 12
    if i == 0:
        value = p / months
    else:
        growth = (ONE + i) ** months
        value = p * i * growth / (growth - ONE)
    return int(value.quantize(_PAISE, rounding=ROUND_HALF_UP))


def principal_for_emi(instalment: int, annual_rate: Decimal, months: int) -> int:
    """Largest principal (paise) whose standard EMI is `instalment`: the EMI formula inverted."""
    if months <= 0:
        raise ValueError("tenure must be positive")
    i = annual_rate / 12
    if i == 0:
        value = Decimal(instalment) * months
    else:
        growth = (ONE + i) ** months
        value = Decimal(instalment) * (growth - ONE) / (i * growth)
    return int(value.quantize(_PAISE, rounding=ROUND_HALF_UP))


def outstanding(principal: int, annual_rate: Decimal, months: int, paid: int) -> int:
    """Principal still owed in paise after `paid` instalments of the standard EMI schedule."""
    if paid >= months:
        return 0
    p = Decimal(principal)
    i = annual_rate / 12
    instalment = Decimal(emi(principal, annual_rate, months))
    if i == 0:
        value = p - instalment * paid
    else:
        growth = (ONE + i) ** paid
        value = p * growth - instalment * (growth - ONE) / i
    return max(0, int(value.quantize(_PAISE, rounding=ROUND_HALF_UP)))

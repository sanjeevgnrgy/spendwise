from decimal import Decimal

DEFAULT_CURRENCY = "INR"
PAISE_PER_RUPEE = 100


def rupees_to_paise(rupees: Decimal | int | str) -> int:
    """'450.50' -> 45050."""
    # Decimal, never float: floats can't hold most decimal fractions exactly (0.1 + 0.2 != 0.3).
    paise = Decimal(str(rupees)) * PAISE_PER_RUPEE
    # Refuse fractions of a paisa rather than silently rounding money away.
    if paise != paise.to_integral_value():
        raise ValueError(f"{rupees} rupees has more than 2 decimal places")
    return int(paise)


def paise_to_rupees(paise: int) -> Decimal:
    """45050 -> Decimal('450.50')."""
    # scaleb(-2) shifts the decimal point two places and keeps both digits ("450.50", not "450.5").
    return Decimal(paise).scaleb(-2)

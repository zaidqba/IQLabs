"""
IQ-RAD Unit Conversion Utilities
Handles conversion between Rotem native units and IQ-RAD standard units.
All conversions are versioned — if a factor changes, create a new version
and document it in the config_versions table.
"""
from decimal import Decimal
from typing import Optional


# Conversion factors (multiply raw value to get normalized value)
# Currently all Rotem units are used as-is (factor = 1.0)
# Future: apply calibration correction_factor from calibration_records
UNIT_CONVERSION_FACTORS: dict[str, Decimal] = {
    "CPS": Decimal("1.0"),          # Counts per second — no conversion
    "MR_PER_HR": Decimal("1.0"),    # mR/h — native Rotem unit, no conversion
    "M3_PER_S": Decimal("1.0"),     # m³/sec — native Rotem unit, no conversion
    "COUNT": Decimal("1.0"),        # Cumulative count — no conversion
}


def apply_conversion(raw_value: Decimal, uom_code: str) -> Decimal:
    """
    Apply unit conversion factor to raw value.
    Returns normalized_value = raw_value × conversion_factor.
    """
    factor = UNIT_CONVERSION_FACTORS.get(uom_code, Decimal("1.0"))
    return raw_value * factor


def apply_calibration_correction(value: Decimal, correction_factor: Decimal) -> Decimal:
    """
    Apply detector calibration correction factor.
    correction_factor comes from calibration_records.correction_factor.
    """
    return value * correction_factor


def validate_value_range(
    value: Decimal,
    uom_code: str,
    min_val: Optional[Decimal] = None,
    max_val: Optional[Decimal] = None,
) -> tuple[bool, Optional[str]]:
    """
    Validate that a value is within physically plausible range.
    Returns (is_valid, reason_if_invalid).
    """
    if value < Decimal("0"):
        return False, f"Negative value {value} is not physically valid for {uom_code}"

    # Physical limits by unit type
    physical_limits: dict[str, tuple[Decimal, Decimal]] = {
        "CPS": (Decimal("0"), Decimal("1e9")),          # Up to 1 GHz CPS
        "MR_PER_HR": (Decimal("0"), Decimal("1e6")),    # Up to 1 MSv/hr equivalent
        "M3_PER_S": (Decimal("0"), Decimal("1000")),    # Up to 1000 m³/sec
        "COUNT": (Decimal("0"), Decimal("1e12")),
    }

    if uom_code in physical_limits:
        lo, hi = physical_limits[uom_code]
        if value > hi:
            return False, f"Value {value} exceeds physical maximum {hi} for {uom_code}"

    if min_val is not None and value < min_val:
        return False, f"Value {value} below configured minimum {min_val}"
    if max_val is not None and value > max_val:
        return False, f"Value {value} above configured maximum {max_val}"

    return True, None

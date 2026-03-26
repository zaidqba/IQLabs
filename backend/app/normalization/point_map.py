"""
IQ-RAD Rotem Point ID → IQ-RAD Channel Mapping
This is the single source of truth for translating Rotem WebiSmarts
raw field names and PointIDs into IQ-RAD standard channel codes.

NEVER let application logic depend on raw vendor field names directly.
All Rotem point name references are isolated to this module.
When Rotem updates firmware naming, only this file changes.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PointMapping:
    """Maps one Rotem WebiSmarts point to an IQ-RAD channel."""
    rotem_point_id: int
    rotem_point_name: str           # From WebiSmarts Points[].Name
    rotem_adapter_id: int           # From WebiSmarts Points[].AdapterID
    rotem_detector_type: str        # From WebiSmarts Points[].Detector_Type
    iq_rad_channel_code: str        # IQ-RAD standard code
    uom_code: str                   # IQ-RAD UOM code
    description: str


# ─── Rotem WebiSmarts Point → IQ-RAD Channel Mapping ─────────────────────────
# Source: WebiSmarts system JSON (provided by site USA56)
# PointID 1 (HyperLink) excluded — UI element, not a measurement channel
ROTEM_POINT_MAP: dict[int, PointMapping] = {
    2: PointMapping(
        rotem_point_id=2,
        rotem_point_name="StackPM11",
        rotem_adapter_id=0,
        rotem_detector_type="Stack_PM11",
        iq_rad_channel_code="STACK.PM11",
        uom_code="CPS",
        description="PM11 Photomultiplier — Count Rate",
    ),
    3: PointMapping(
        rotem_point_id=3,
        rotem_point_name="StackGM42",
        rotem_adapter_id=1,
        rotem_detector_type="Stack_GM-42",
        iq_rad_channel_code="STACK.GM42",
        uom_code="MR_PER_HR",
        description="GM-42 Geiger-Mueller — Dose Rate",
    ),
    4: PointMapping(
        rotem_point_id=4,
        rotem_point_name="StackAir",
        rotem_adapter_id=2,
        rotem_detector_type="AirFlow",
        iq_rad_channel_code="STACK.AIR",
        uom_code="M3_PER_S",
        description="Air Flow Sensor — Volumetric Flow Rate",
    ),
    5: PointMapping(
        rotem_point_id=5,
        rotem_point_name="W1",
        rotem_adapter_id=11,
        rotem_detector_type="Unknown",
        iq_rad_channel_code="STACK.W1",
        uom_code="CPS",
        description="Beta Detector Window 1",
    ),
    6: PointMapping(
        rotem_point_id=6,
        rotem_point_name="W2",
        rotem_adapter_id=12,
        rotem_detector_type="Unknown",
        iq_rad_channel_code="STACK.W2",
        uom_code="CPS",
        description="Beta Detector Window 2",
    ),
    7: PointMapping(
        rotem_point_id=7,
        rotem_point_name="W3",
        rotem_adapter_id=13,
        rotem_detector_type="Unknown",
        iq_rad_channel_code="STACK.W3",
        uom_code="CPS",
        description="Beta Detector Window 3",
    ),
    8: PointMapping(
        rotem_point_id=8,
        rotem_point_name="W4",
        rotem_adapter_id=14,
        rotem_detector_type="Unknown",
        iq_rad_channel_code="STACK.W4",
        uom_code="CPS",
        description="Beta Detector Window 4",
    ),
    9: PointMapping(
        rotem_point_id=9,
        rotem_point_name="W5",
        rotem_adapter_id=15,
        rotem_detector_type="Unknown",
        iq_rad_channel_code="STACK.W5",
        uom_code="CPS",
        description="Beta Detector Window 5",
    ),
}

# Reverse lookup: channel_code → PointMapping
CHANNEL_CODE_MAP: dict[str, PointMapping] = {
    m.iq_rad_channel_code: m for m in ROTEM_POINT_MAP.values()
}

# Reverse lookup: rotem_point_name → PointMapping (case-insensitive)
POINT_NAME_MAP: dict[str, PointMapping] = {
    m.rotem_point_name.lower(): m for m in ROTEM_POINT_MAP.values()
}


def get_mapping_by_point_id(point_id: int) -> Optional[PointMapping]:
    return ROTEM_POINT_MAP.get(point_id)


def get_mapping_by_point_name(name: str) -> Optional[PointMapping]:
    return POINT_NAME_MAP.get(name.lower())


def get_mapping_by_channel_code(code: str) -> Optional[PointMapping]:
    return CHANNEL_CODE_MAP.get(code)


def get_all_active_point_ids() -> list[int]:
    return sorted(ROTEM_POINT_MAP.keys())

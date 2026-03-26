"""
IQ-RAD Rotem Normalizer
Converts raw bytes from Rotem connectors into NormalizedEvent objects.
This is the vendor-specific parsing layer — the only place Rotem wire
format details are known. All downstream code uses NormalizedEvent.

Protocol Analysis:
  The Rotem WebiSmarts Connection Unit (localhost:15386) speaks to the
  devices and serves data via an internal HTTP interface. The Stack device
  at 10.0.0.160:4001 returns JSON-formatted point data based on the
  WebiSmarts Points schema we've been provided.

  Expected response format (JSON array of point readings):
  [
    {"PointID": 2, "Name": "StackPM11", "Rate": 123.45, "Dose": 0.0,
     "AlarmState": 0, "Quality": 0, "Timestamp": "2025-03-12T10:36:28.999"},
    ...
  ]

  If the actual wire format differs, adjust _parse_rotem_json() only.
  The NormalizedEvent output contract must remain stable.
"""
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.connectors.base import RawPacket
from app.core.logging import get_logger
from app.core.ntp_sync import get_ntp_offset_ms, is_ntp_valid
from app.normalization.point_map import get_mapping_by_point_id, get_mapping_by_point_name
from app.normalization.unit_converter import apply_conversion, validate_value_range
from app.schemas.common import NormalizedEvent, QualityFlag, SeverityLevel

logger = get_logger(__name__)


class RotemNormalizer:
    """
    Parses raw Rotem TCP/HTTP response bytes into NormalizedEvent objects.

    channel_map: dict mapping channel_code → (channel_id, uom_id, alarm_profile)
    Populated at startup from the database channels table.
    """

    def __init__(self, channel_map: dict):
        """
        channel_map: {channel_code: {"channel_id": int, "uom_id": int,
                                      "alarm_profile": AlarmProfileData | None}}
        """
        self._channel_map = channel_map

    def parse(self, packet: RawPacket) -> list[NormalizedEvent]:
        """
        Parse a RawPacket into a list of NormalizedEvent objects.
        Returns empty list on complete parse failure (logged as error).
        Partial failures yield events for successfully parsed points only.
        """
        events: list[NormalizedEvent] = []
        ntp_offset = get_ntp_offset_ms()
        ntp_ok = is_ntp_valid()

        try:
            point_readings = self._extract_json_body(packet.raw_bytes)
            if point_readings is None:
                logger.warning(
                    "normalizer_parse_failed",
                    extra={
                        "device_id": packet.device_id,
                        "session_id": packet.session_id,
                        "reason": "no_json_body",
                    },
                )
                return events

            for point_data in point_readings:
                event = self._parse_point(
                    packet=packet,
                    point_data=point_data,
                    ntp_offset=ntp_offset,
                    ntp_ok=ntp_ok,
                )
                if event is not None:
                    events.append(event)

        except Exception as exc:
            logger.error(
                "normalizer_exception",
                extra={"device_id": packet.device_id, "error": str(exc)},
            )

        return events

    def _extract_json_body(self, raw_bytes: bytes) -> Optional[list]:
        """
        Extract JSON body from HTTP or raw TCP response.
        Handles both HTTP/1.x responses and raw JSON payloads.
        """
        try:
            text = raw_bytes.decode("utf-8", errors="replace")

            # Strip HTTP headers if present
            if text.startswith("HTTP/"):
                separator = "\r\n\r\n"
                idx = text.find(separator)
                if idx != -1:
                    text = text[idx + 4:]

            text = text.strip()
            if not text:
                return None

            data = json.loads(text)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "points" in data:
                return data["points"]
            return None

        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.debug("json_parse_failed", extra={"error": str(exc)})
            return None

    def _parse_point(
        self,
        packet: RawPacket,
        point_data: dict,
        ntp_offset: Optional[int],
        ntp_ok: bool,
        ingestion_id: int = 0,  # Set after DB INSERT by ingestion_service
    ) -> Optional[NormalizedEvent]:
        """Parse one point dict into a NormalizedEvent."""
        try:
            # Resolve point ID and channel mapping
            point_id = int(point_data.get("PointID", 0))
            point_name = str(point_data.get("Name", ""))

            mapping = get_mapping_by_point_id(point_id) or get_mapping_by_point_name(point_name)
            if mapping is None:
                logger.debug("unknown_point", extra={"point_id": point_id, "name": point_name})
                return None

            channel_info = self._channel_map.get(mapping.iq_rad_channel_code)
            if channel_info is None:
                logger.warning("channel_not_in_map", extra={"code": mapping.iq_rad_channel_code})
                return None

            # Parse value
            raw_value = Decimal(str(point_data.get("Rate", point_data.get("Value", 0))))
            normalized_value = apply_conversion(raw_value, mapping.uom_code)

            # Validate range
            is_valid, invalid_reason = validate_value_range(normalized_value, mapping.uom_code)

            # Parse timestamp
            ts_str = point_data.get("Timestamp") or point_data.get("timestamp")
            if ts_str:
                try:
                    measured_at = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if measured_at.tzinfo is None:
                        measured_at = measured_at.replace(tzinfo=timezone.utc)
                except ValueError:
                    measured_at = packet.received_at_utc
            else:
                measured_at = packet.received_at_utc

            # Quality flag
            vendor_quality = int(point_data.get("Quality", 0))
            if not ntp_ok:
                quality_flag = QualityFlag.SUSPECT
                quality_detail = f"NTP drift exceeds threshold (offset={ntp_offset}ms)"
            elif not is_valid:
                quality_flag = QualityFlag.BAD
                quality_detail = invalid_reason
            elif vendor_quality != 0:
                quality_flag = QualityFlag.SUSPECT
                quality_detail = f"Vendor quality code: {vendor_quality}"
            else:
                quality_flag = QualityFlag.GOOD
                quality_detail = None

            alarm_profile = channel_info.get("alarm_profile")

            return NormalizedEvent(
                ingestion_id=ingestion_id,
                device_id=packet.device_id,
                channel_id=channel_info["channel_id"],
                channel_code=mapping.iq_rad_channel_code,
                rotem_point_id=mapping.rotem_point_id,
                measured_at_utc=measured_at,
                received_at_utc=packet.received_at_utc,
                raw_value=raw_value,
                normalized_value=normalized_value,
                uom_code=mapping.uom_code,
                uom_id=channel_info["uom_id"],
                quality_flag=quality_flag,
                quality_detail=quality_detail,
                ntp_offset_ms=ntp_offset,
                alarm_profile_id=alarm_profile.get("profile_id") if alarm_profile else None,
                low_threshold=Decimal(str(alarm_profile["low_threshold"])) if alarm_profile and alarm_profile.get("low_threshold") else None,
                alert_threshold=Decimal(str(alarm_profile["alert_threshold"])) if alarm_profile else None,
                alarm_threshold=Decimal(str(alarm_profile["alarm_threshold"])) if alarm_profile else None,
                danger_threshold=Decimal(str(alarm_profile["danger_threshold"])) if alarm_profile else None,
                high_dose_threshold=Decimal(str(alarm_profile["high_dose_threshold"])) if alarm_profile and alarm_profile.get("high_dose_threshold") else None,
            )

        except (InvalidOperation, KeyError, ValueError, TypeError) as exc:
            logger.warning(
                "point_parse_error",
                extra={"error": str(exc), "point_data": str(point_data)[:200]},
            )
            return None

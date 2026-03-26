"""
IQ-RAD Threshold Evaluator
Stateless, pure-function evaluation of reading severity against alarm profiles.
This is the regulatory heart of the system: incorrect logic here directly
affects radiation protection decisions (10 CFR Part 20).

Priority order (highest severity wins):
  HIGH_DOSE > DANGER > ALARM > ALERT > LOW > NORMAL
"""
from decimal import Decimal
from typing import Optional

from app.schemas.common import NormalizedEvent, SeverityLevel


class ThresholdEvaluator:
    """
    Stateless threshold evaluator.
    Operates purely on NormalizedEvent data — no database calls.
    Returns the severity level and which threshold name was crossed.
    """

    def evaluate(self, event: NormalizedEvent) -> tuple[SeverityLevel, Optional[str]]:
        """
        Evaluate a NormalizedEvent against its active alarm profile thresholds.

        Returns:
            (SeverityLevel, threshold_name_crossed)
            threshold_name_crossed is None for NORMAL.

        Thresholds are applied from highest severity downward.
        If quality_flag is BAD, severity is forced to ALARM to ensure
        the operator is notified of data quality issues.
        """
        from app.schemas.common import QualityFlag

        # BAD quality data triggers ALARM to force operator attention
        if event.quality_flag == QualityFlag.BAD:
            return SeverityLevel.ALARM, "DATA_QUALITY"

        v = event.normalized_value

        # Check if we have any thresholds to evaluate against
        if event.alarm_threshold is None:
            return SeverityLevel.NORMAL, None

        # Evaluate from highest severity downward
        if event.high_dose_threshold is not None and v >= event.high_dose_threshold:
            return SeverityLevel.HIGH_DOSE, "high_dose_threshold"

        if v >= event.danger_threshold:
            return SeverityLevel.DANGER, "danger_threshold"

        if v >= event.alarm_threshold:
            return SeverityLevel.ALARM, "alarm_threshold"

        if v >= event.alert_threshold:
            return SeverityLevel.ALERT, "alert_threshold"

        if event.low_threshold is not None and v <= event.low_threshold and v >= Decimal("0"):
            return SeverityLevel.LOW, "low_threshold"

        return SeverityLevel.NORMAL, None

    def requires_signature(self, severity: SeverityLevel) -> bool:
        """
        Determines if an alarm at this severity requires an electronic signature
        for acknowledgement per 21 CFR Part 11 policy.
        DANGER and HIGH_DOSE require e-signature; ALERT and ALARM require comment only.
        """
        return severity in (SeverityLevel.DANGER, SeverityLevel.HIGH_DOSE)

    def escalation_minutes(self, severity: SeverityLevel) -> Optional[int]:
        """
        Time (minutes) before an unacknowledged alarm escalates.
        None means no escalation deadline.
        """
        escalation_map = {
            SeverityLevel.ALERT: 15,
            SeverityLevel.ALARM: 5,
            SeverityLevel.DANGER: 2,
            SeverityLevel.HIGH_DOSE: 1,
        }
        return escalation_map.get(severity)

    def alarm_message(self, channel_code: str, severity: SeverityLevel, value: Decimal, uom_code: str) -> str:
        """Generate a human-readable alarm message."""
        severity_labels = {
            SeverityLevel.LOW: "Below-minimum reading",
            SeverityLevel.ALERT: "Alert threshold exceeded",
            SeverityLevel.ALARM: "ALARM threshold exceeded",
            SeverityLevel.DANGER: "DANGER threshold exceeded",
            SeverityLevel.HIGH_DOSE: "HIGH DOSE threshold exceeded — IMMEDIATE ACTION REQUIRED",
        }
        label = severity_labels.get(severity, "Threshold exceeded")
        return f"{channel_code}: {label} — value={value} {uom_code}"

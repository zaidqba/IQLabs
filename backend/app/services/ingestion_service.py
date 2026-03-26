"""
IQ-RAD Ingestion Service
Orchestrates the full data pipeline:
  Connector → RawPacket → raw_ingestion_log → Normalizer → NormalizedEvent
  → normalized_readings → Rules Engine → AlarmManager → WebSocket broadcast

This is the central event loop of IQ-RAD.
Runs two asyncio tasks: one for Rotem Stack (:4001), one for DPU3 (:5000).
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import RawPacket
from app.connectors.rotem_dpu3 import RotemDPU3ConnectorWithReconnect
from app.connectors.rotem_stack import RotemStackConnectorWithReconnect
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.exceptions import DeviceConnectionError
from app.core.logging import get_logger
from app.core.ntp_sync import ntp_monitor_loop
from app.models.master import AlarmProfile, Channel, Device, UnitOfMeasure
from app.models.runtime import (
    DeviceStatus,
    HeartbeatLog,
    NormalizedReading,
    RawIngestionLog,
)
from app.normalization.normalizer import RotemNormalizer
from app.rules_engine.alarm_manager import AlarmManager
from app.rules_engine.compliance_checks import ComplianceWatchdog
from app.schemas.common import NormalizedEvent, QualityFlag
from app.services.websocket_service import ws_manager

settings = get_settings()
logger = get_logger(__name__)

alarm_manager = AlarmManager()


class IngestionService:
    """
    Manages the ingestion pipeline lifecycle.
    Start with run() as an asyncio task from FastAPI lifespan.
    """

    def __init__(self):
        self._running = False
        self._stack_connector: Optional[RotemStackConnectorWithReconnect] = None
        self._dpu3_connector: Optional[RotemDPU3ConnectorWithReconnect] = None
        self._normalizer: Optional[RotemNormalizer] = None
        self._watchdog: Optional[ComplianceWatchdog] = None
        self._channel_map: dict = {}

    async def run(self) -> None:
        """Start all ingestion tasks. Call from FastAPI lifespan."""
        self._running = True
        logger.info("ingestion_service_starting")

        # Load channel map from database
        await self._load_channel_map()

        # Initialise connectors
        async with AsyncSessionLocal() as db:
            stack_dev = await self._get_device(db, "ROTEM-STACK")
            dpu3_dev = await self._get_device(db, "ROTEM-DPU3")

        self._stack_connector = RotemStackConnectorWithReconnect(
            device_id=stack_dev.device_id if stack_dev else 1,
            host=settings.rotem_stack_host,
            port=settings.rotem_stack_port,
            poll_interval_s=settings.poll_interval_s,
        )
        self._dpu3_connector = RotemDPU3ConnectorWithReconnect(
            device_id=dpu3_dev.device_id if dpu3_dev else 2,
            host=settings.rotem_dpu3_host,
            port=settings.rotem_dpu3_port,
            poll_interval_s=settings.poll_interval_s,
        )
        self._normalizer = RotemNormalizer(self._channel_map)
        self._watchdog = ComplianceWatchdog(
            device_poll_intervals={
                self._stack_connector.device_id: settings.poll_interval_s,
                self._dpu3_connector.device_id: settings.poll_interval_s,
            }
        )

        # Launch all background tasks
        await asyncio.gather(
            self._connector_loop(self._stack_connector, "rotem_stack"),
            self._connector_loop(self._dpu3_connector, "rotem_dpu3"),
            self._heartbeat_loop(),
            self._watchdog_loop(),
            ntp_monitor_loop(interval_s=60),
            return_exceptions=True,
        )

    async def stop(self) -> None:
        self._running = False
        if self._stack_connector:
            await self._stack_connector.disconnect()
        if self._dpu3_connector:
            await self._dpu3_connector.disconnect()
        logger.info("ingestion_service_stopped")

    async def _connector_loop(self, connector, name: str) -> None:
        """Poll loop for one connector. Handles reconnect with backoff."""
        attempt = 0
        while self._running:
            try:
                await connector.connect_with_retry()
                await self._emit_device_status(connector.device_id, "ONLINE")
                attempt = 0

                while self._running and connector.is_connected:
                    try:
                        async for packet in connector.poll():
                            await self._process_packet(packet)
                        await asyncio.sleep(connector.poll_interval_s)
                    except DeviceConnectionError:
                        await self._emit_device_status(connector.device_id, "OFFLINE")
                        break

            except Exception as exc:
                logger.error(
                    f"{name}_loop_error",
                    extra={"error": str(exc), "attempt": attempt},
                )
                await self._emit_device_status(connector.device_id, "FAULT")
                delay = min(2 ** attempt, 30)
                await asyncio.sleep(delay)
                attempt += 1

    async def _process_packet(self, packet: RawPacket) -> None:
        """Process one raw packet: persist → normalize → rules → broadcast."""
        async with AsyncSessionLocal() as db:
            try:
                # 1. Persist raw packet (IMMUTABLE)
                raw_log = RawIngestionLog(
                    device_id=packet.device_id,
                    received_at_utc=packet.received_at_utc,
                    source_ip=packet.source_ip,
                    source_port=packet.source_port,
                    session_id=packet.session_id,
                    raw_payload=packet.raw_bytes,
                    payload_length=packet.payload_length,
                    parse_status="PENDING",
                    packet_sequence=packet.packet_sequence,
                )
                db.add(raw_log)
                await db.flush()

                # 2. Normalize
                events = self._normalizer.parse(packet)

                parse_status = "PARSED" if events else "FAILED"
                raw_log.parse_status = parse_status

                # 3. Persist normalized readings and evaluate rules
                for event in events:
                    event = event.model_copy(update={"ingestion_id": raw_log.ingestion_id})

                    reading = NormalizedReading(
                        ingestion_id=raw_log.ingestion_id,
                        channel_id=event.channel_id,
                        measured_at_utc=event.measured_at_utc,
                        received_at_utc=event.received_at_utc,
                        raw_value=event.raw_value,
                        normalized_value=event.normalized_value,
                        uom_id=event.uom_id,
                        quality_flag=event.quality_flag,
                        quality_detail=event.quality_detail,
                        alarm_profile_id=event.alarm_profile_id,
                        severity_level=event.severity_level,
                        ntp_offset_ms=event.ntp_offset_ms,
                    )
                    db.add(reading)
                    await db.flush()

                    # 4. Rules engine
                    ws_alarm_events = await alarm_manager.handle_event(
                        db, event, reading.reading_id
                    )

                    # 5. Broadcast reading via WebSocket
                    await ws_manager.broadcast_reading(
                        channel_code=event.channel_code,
                        channel_name=event.channel_code,
                        value=str(event.normalized_value),
                        uom=event.uom_code,
                        severity=event.severity_level,
                        quality_flag=event.quality_flag,
                        measured_at=event.measured_at_utc,
                        channel_id=event.channel_id,
                    )

                    # 6. Broadcast alarm events
                    for alarm_event in ws_alarm_events:
                        await ws_manager.broadcast(alarm_event)

                await db.commit()

            except Exception as exc:
                await db.rollback()
                logger.error(
                    "packet_processing_error",
                    extra={"device_id": packet.device_id, "error": str(exc)},
                )

    async def _heartbeat_loop(self) -> None:
        """Record heartbeats and NTP status every poll_interval_s."""
        from app.core.ntp_sync import get_ntp_offset_ms, is_ntp_valid
        seq = 0
        while self._running:
            await asyncio.sleep(settings.poll_interval_s)
            seq += 1
            ntp_offset = get_ntp_offset_ms()
            ntp_ok = is_ntp_valid()

            for connector in [self._stack_connector, self._dpu3_connector]:
                if connector and connector.is_connected:
                    async with AsyncSessionLocal() as db:
                        db.add(HeartbeatLog(
                            device_id=connector.device_id,
                            ntp_offset_ms=ntp_offset,
                            is_ntp_valid=ntp_ok,
                            sequence_num=seq,
                            session_id=connector.session_id,
                        ))
                        await db.commit()

                    await ws_manager.broadcast_heartbeat(
                        device_id=connector.device_id,
                        ntp_offset_ms=ntp_offset,
                        is_ntp_valid=ntp_ok,
                        sequence_num=seq,
                    )

    async def _watchdog_loop(self) -> None:
        """Run compliance checks every 60 seconds."""
        while self._running:
            await asyncio.sleep(60)
            async with AsyncSessionLocal() as db:
                try:
                    alerts = await self._watchdog.run_checks(db)
                    await db.commit()
                    if alerts:
                        logger.info(
                            "watchdog_alerts",
                            extra={"count": len(alerts)},
                        )
                except Exception as exc:
                    logger.error("watchdog_error", extra={"error": str(exc)})

    async def _load_channel_map(self) -> None:
        """Load channel configuration from DB into memory."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Channel, UnitOfMeasure, AlarmProfile)
                .join(UnitOfMeasure, Channel.uom_id == UnitOfMeasure.uom_id)
                .outerjoin(
                    AlarmProfile,
                    (AlarmProfile.channel_id == Channel.channel_id)
                    & (AlarmProfile.is_current == True),
                )
                .where(Channel.is_active == True)
            )
            rows = result.all()

            for channel, uom, profile in rows:
                self._channel_map[channel.channel_code] = {
                    "channel_id": channel.channel_id,
                    "uom_id": uom.uom_id,
                    "uom_code": uom.uom_code,
                    "alarm_profile": {
                        "profile_id": profile.profile_id,
                        "low_threshold": profile.low_threshold,
                        "alert_threshold": profile.alert_threshold,
                        "alarm_threshold": profile.alarm_threshold,
                        "danger_threshold": profile.danger_threshold,
                        "high_dose_threshold": profile.high_dose_threshold,
                    } if profile else None,
                }
        logger.info("channel_map_loaded", extra={"count": len(self._channel_map)})

    async def _emit_device_status(self, device_id: int, status_code: str) -> None:
        async with AsyncSessionLocal() as db:
            db.add(DeviceStatus(device_id=device_id, status_code=status_code))
            await db.commit()
        await ws_manager.broadcast_device_status(
            device_id=device_id,
            device_code=f"device_{device_id}",
            status_code=status_code,
        )

    @staticmethod
    async def _get_device(db: AsyncSession, device_code: str) -> Optional[Device]:
        result = await db.execute(
            select(Device).where(Device.device_code == device_code)
        )
        return result.scalar_one_or_none()


# Global singleton
ingestion_service = IngestionService()

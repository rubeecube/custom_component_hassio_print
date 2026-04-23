"""Sensor entities for the Auto Print integration."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_LAST_FILENAME,
    ATTR_LAST_STATUS,
    CONF_PRINTER_NAME,
    DOMAIN,
    SENSOR_JOB_LOG,
    SENSOR_LAST_JOB,
    SENSOR_QUEUE_DEPTH,
)
from .coordinator import AutoPrintCoordinator, AutoPrintData

logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AutoPrintCoordinator = entry.runtime_data
    async_add_entities(
        [
            QueueDepthSensor(coordinator, entry),
            LastJobSensor(coordinator, entry),
            JobLogSensor(coordinator, entry),
        ]
    )


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Auto Print — {entry.data[CONF_PRINTER_NAME]}",
        manufacturer="Auto Print",
        model="Email → IPP Bridge",
        entry_type=DeviceEntryType.SERVICE,
    )


class QueueDepthSensor(CoordinatorEntity[AutoPrintCoordinator], SensorEntity):
    """Number of PDF files currently waiting in the print queue folder."""

    _attr_has_entity_name = True
    _attr_translation_key = SENSOR_QUEUE_DEPTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "files"
    _attr_icon = "mdi:printer-outline"

    def __init__(self, coordinator: AutoPrintCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_QUEUE_DEPTH}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int:
        return self.coordinator.data.queue_depth if self.coordinator.data else 0


class LastJobSensor(CoordinatorEntity[AutoPrintCoordinator], SensorEntity):
    """Status of the most recently attempted print job."""

    _attr_has_entity_name = True
    _attr_translation_key = SENSOR_LAST_JOB
    _attr_icon = "mdi:file-pdf-box"

    def __init__(self, coordinator: AutoPrintCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_LAST_JOB}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> str | None:
        data: AutoPrintData | None = self.coordinator.data
        if data is None or data.last_job is None:
            return None
        return "success" if data.last_job.success else "failed"

    @property
    def extra_state_attributes(self) -> dict:
        data: AutoPrintData | None = self.coordinator.data
        if data is None or data.last_job is None:
            return {}
        job = data.last_job
        attrs: dict = {ATTR_LAST_FILENAME: job.filename}
        if job.error:
            attrs[ATTR_LAST_STATUS] = job.error
        if job.sender:
            attrs["sender"] = job.sender
        if job.duplex:
            attrs["duplex"] = job.duplex
        attrs["booklet"] = job.booklet
        attrs["timestamp"] = job.timestamp
        return attrs


class JobLogSensor(CoordinatorEntity[AutoPrintCoordinator], SensorEntity):
    """Cumulative print job counter with full history in attributes.

    state      : total number of jobs sent since last HA restart
    attributes : jobs — list of the last 50 print attempts with full metadata
    """

    _attr_has_entity_name = True
    _attr_translation_key = SENSOR_JOB_LOG
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "jobs"
    _attr_icon = "mdi:clipboard-text-clock"

    def __init__(self, coordinator: AutoPrintCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_JOB_LOG}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int:
        return self.coordinator.data.total_jobs_sent if self.coordinator.data else 0

    @property
    def extra_state_attributes(self) -> dict:
        data: AutoPrintData | None = self.coordinator.data
        if data is None:
            return {"jobs": []}
        return {
            "jobs": [
                {
                    "timestamp": j.timestamp,
                    "filename": j.filename,
                    "success": j.success,
                    "error": j.error,
                    "sender": j.sender,
                    "duplex": j.duplex,
                    "booklet": j.booklet,
                }
                for j in data.job_history
            ]
        }

"""Sensor platform for Proxmox CPU Dashboard."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProxmoxCPUCoordinator


@dataclass(frozen=True, kw_only=True)
class ProxmoxSensorDescription(SensorEntityDescription):
    """Describes a ProxmoxCPU sensor (with an extraction callback)."""

    value_fn: Callable[[dict[str, Any]], Any] = lambda d: None


SENSORS: tuple[ProxmoxSensorDescription, ...] = (
    ProxmoxSensorDescription(
        key="cpu_temperature",
        translation_key="cpu_temperature",
        name="CPU Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("temps", {}).get("cpu_tctl"),
    ),
    ProxmoxSensorDescription(
        key="nvme_composite_temperature",
        translation_key="nvme_composite_temperature",
        name="NVMe Composite Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("temps", {}).get("nvme_composite"),
    ),
    ProxmoxSensorDescription(
        key="nvme_sensor1_temperature",
        translation_key="nvme_sensor1_temperature",
        name="NVMe Sensor 1 Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("temps", {}).get("nvme_sensor1"),
    ),
    ProxmoxSensorDescription(
        key="cpu_frequency",
        translation_key="cpu_frequency",
        name="CPU Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: round(d.get("cpufreq", {}).get("current_khz", 0) / 1000),
    ),
    ProxmoxSensorDescription(
        key="cpu_max_frequency",
        translation_key="cpu_max_frequency",
        name="CPU Max Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: round(d.get("cpufreq", {}).get("max_khz", 0) / 1000),
    ),
    ProxmoxSensorDescription(
        key="cpu_governor",
        translation_key="cpu_governor",
        name="CPU Governor",
        value_fn=lambda d: d.get("cpufreq", {}).get("governor"),
    ),
    ProxmoxSensorDescription(
        key="cpu_power",
        translation_key="cpu_power",
        name="CPU Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("power_w"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: ProxmoxCPUCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ProxmoxCPUSensor(coordinator, entry, desc) for desc in SENSORS
    )


class ProxmoxCPUSensor(CoordinatorEntity[ProxmoxCPUCoordinator], SensorEntity):
    """A single sensor entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ProxmoxCPUCoordinator,
        entry: ConfigEntry,
        description: ProxmoxSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Proxmox CPU ({coordinator.host})",
            manufacturer="Proxmox CPU Dashboard",
            model="pve-cpufreq-api",
            configuration_url=f"http://{coordinator.host}:8006",
        )

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Hide sensor if no value (e.g. power_w when RAPL unavailable)."""
        val = self.native_value
        if self.entity_description.key == "cpu_power":
            return val is not None
        return super().available

"""Select platform: CPU governor dropdown."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProxmoxCPUCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the governor select entity."""
    coordinator: ProxmoxCPUCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GovernorSelect(coordinator, entry)])


class GovernorSelect(CoordinatorEntity[ProxmoxCPUCoordinator], SelectEntity):
    """Lets the user pick an available CPU governor."""

    _attr_has_entity_name = True
    _attr_translation_key = "cpu_governor"
    _attr_name = "CPU Governor"
    _attr_icon = "mdi:cpu-64-bit"

    def __init__(self, coordinator: ProxmoxCPUCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_governor_select"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Proxmox CPU ({coordinator.host})",
            manufacturer="Proxmox CPU Dashboard",
            model="pve-cpufreq-api",
        )

    @property
    def options(self) -> list[str]:
        if self.coordinator.data is None:
            return []
        return self.coordinator.data.get("cpufreq", {}).get(
            "available_governors", []
        ) or []

    @property
    def current_option(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("cpufreq", {}).get("governor")

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_cpufreq(governor=option)

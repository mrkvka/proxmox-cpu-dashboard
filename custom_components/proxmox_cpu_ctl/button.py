"""Button platform: one-click preset profiles."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PRESETS
from .coordinator import ProxmoxCPUCoordinator

_NAMES = {
    "performance": ("Preset Performance", "mdi:rocket-launch"),
    "balanced": ("Preset Balanced", "mdi:balance-scale"),
    "powersave": ("Preset Powersave", "mdi:leaf"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ProxmoxCPUCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        PresetButton(coordinator, entry, preset) for preset in PRESETS
    )


class PresetButton(CoordinatorEntity[ProxmoxCPUCoordinator], ButtonEntity):
    """One-tap preset: sets both governor and max_freq in a single call."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ProxmoxCPUCoordinator,
        entry: ConfigEntry,
        preset: str,
    ) -> None:
        super().__init__(coordinator)
        self._preset = preset
        label, icon = _NAMES[preset]
        self._attr_name = label
        self._attr_icon = icon
        self._attr_translation_key = f"preset_{preset}"
        self._attr_unique_id = f"{entry.entry_id}_preset_{preset}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Proxmox CPU ({coordinator.host})",
            manufacturer="Proxmox CPU Dashboard",
            model="pve-cpufreq-api",
        )

    async def async_press(self) -> None:
        cfg = PRESETS[self._preset]
        await self.coordinator.async_set_cpufreq(
            governor=cfg["governor"],
            max_freq_khz=cfg["max_freq"],
        )

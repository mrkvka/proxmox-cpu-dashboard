"""DataUpdateCoordinator for Proxmox CPU Dashboard."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ProxmoxCPUCoordinator(DataUpdateCoordinator):
    """Polls the Proxmox CPU Dashboard API (/status) and sends commands to /cpufreq."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        scan_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{host}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host = host
        self.port = port
        self._base = f"http://{host}:{port}"
        self._session: aiohttp.ClientSession = async_get_clientsession(hass)

    @property
    def base_url(self) -> str:
        """Return the base URL of the API."""
        return self._base

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest data from /status."""
        try:
            async with self._session.get(
                f"{self._base}/status", timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"HTTP {resp.status} from /status")
                data = await resp.json()
                if "error" in data:
                    raise UpdateFailed(data["error"])
                return data
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Cannot reach {self._base}: {err}") from err

    async def async_health(self) -> bool:
        """Return True if the API responds to /health."""
        try:
            async with self._session.get(
                f"{self._base}/health", timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200
        except Exception:  # noqa: BLE001
            return False

    async def async_set_cpufreq(
        self,
        governor: str | None = None,
        max_freq_khz: int | None = None,
    ) -> None:
        """Send POST /cpufreq and trigger refresh."""
        form: dict[str, str] = {}
        if governor:
            form["governor"] = governor
        if max_freq_khz:
            form["max_freq"] = str(int(max_freq_khz))
        if not form:
            return
        async with self._session.post(
            f"{self._base}/cpufreq",
            data=form,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise UpdateFailed(f"POST /cpufreq failed ({resp.status}): {body}")
        await self.async_request_refresh()

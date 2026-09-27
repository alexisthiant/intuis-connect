"""Sélecteurs pour le pilotage global de l'installation.

Reproduit le widget "Home" de l'application Intuis Connect : mode de la
maison (Programmation / Hors gel / Absent) et choix du planning actif.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, HOME_MODE_AWAY, HOME_MODE_FROST, HOME_MODE_SCHEDULE, HOME_MODES
from .coordinator import IntuisDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

MODE_LABELS = {
    HOME_MODE_SCHEDULE: "Programmation",
    HOME_MODE_FROST: "Hors gel",
    HOME_MODE_AWAY: "Absent",
}
LABEL_TO_MODE = {v: k for k, v in MODE_LABELS.items()}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: IntuisDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([IntuisHomeModeSelect(coordinator), IntuisScheduleSelect(coordinator)])


class _IntuisHomeEntity(CoordinatorEntity[IntuisDataUpdateCoordinator]):
    """Entité rattachée au périphérique "maison" (la passerelle Intuis)."""

    def __init__(self, coordinator: IntuisDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.home_id or "intuis")},
            name=coordinator.data["home"].get("name", "Intuis Connect"),
            manufacturer="Intuis (Muller / Legrand)",
            model="Passerelle Intuis Connect",
        )


class IntuisHomeModeSelect(_IntuisHomeEntity, SelectEntity):
    """Mode global de la maison : Programmation / Hors gel / Absent."""

    _attr_has_entity_name = True
    _attr_name = "Mode de la maison"
    _attr_icon = "mdi:home-thermometer"
    _attr_options = [MODE_LABELS[m] for m in HOME_MODES]

    def __init__(self, coordinator: IntuisDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.home_id}_home_mode"

    @property
    def current_option(self) -> str | None:
        mode = self.coordinator.data["home"].get("therm_mode")
        return MODE_LABELS.get(mode)

    async def async_select_option(self, option: str) -> None:
        mode = LABEL_TO_MODE.get(option)
        if mode is None:
            return
        await self.coordinator.client.async_set_home_mode(self.coordinator.home_id, mode)
        await self.coordinator.async_request_refresh()


class IntuisScheduleSelect(_IntuisHomeEntity, SelectEntity):
    """Choix du planning de chauffe actif (ex : Semaine type / Vacances)."""

    _attr_has_entity_name = True
    _attr_name = "Planning actif"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: IntuisDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.home_id}_schedule"

    @property
    def _schedules(self) -> list[dict[str, Any]]:
        return self.coordinator.data["home"].get("therm_schedules", [])

    @property
    def options(self) -> list[str]:
        return [s["name"] for s in self._schedules]

    @property
    def current_option(self) -> str | None:
        for schedule in self._schedules:
            if schedule.get("selected"):
                return schedule["name"]
        return None

    async def async_select_option(self, option: str) -> None:
        for schedule in self._schedules:
            if schedule["name"] == option:
                await self.coordinator.client.async_switch_schedule(
                    self.coordinator.home_id, schedule["id"]
                )
                break
        await self.coordinator.async_request_refresh()

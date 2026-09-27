"""Curseur de durée pour la consigne manuelle, un par pièce.

Ce réglage est purement local à Home Assistant (l'API Intuis ne l'expose
pas) : il fixe la durée utilisée par le thermostat standard (dial/carte)
quand tu ajustes la température normalement, pour éviter de devoir passer
par le service `intuis.set_manual_temperature` à chaque fois.
"""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MAX_MANUAL_DURATION_HOURS, MIN_MANUAL_DURATION_HOURS
from .coordinator import IntuisDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: IntuisDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        IntuisManualDurationNumber(coordinator, room_id) for room_id in coordinator.data["rooms"]
    )


class IntuisManualDurationNumber(
    CoordinatorEntity[IntuisDataUpdateCoordinator], RestoreEntity, NumberEntity
):
    """Durée (en heures) appliquée par le thermostat standard de cette pièce."""

    _attr_has_entity_name = True
    _attr_name = "Durée de consigne manuelle"
    _attr_icon = "mdi:timer-outline"
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_native_min_value = MIN_MANUAL_DURATION_HOURS
    _attr_native_max_value = MAX_MANUAL_DURATION_HOURS
    _attr_native_step = 1

    def __init__(self, coordinator: IntuisDataUpdateCoordinator, room_id: str) -> None:
        super().__init__(coordinator)
        self._room_id = room_id
        self._attr_unique_id = f"{coordinator.home_id}_{room_id}_manual_duration"
        self._value: float | None = None
        room = coordinator.data["rooms"][room_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room_id)}, name=room.get("name", room_id)
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        value: float | None = None
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                value = float(last_state.state)
            except ValueError:
                value = None
        if value is None:
            app_default_hours = self.coordinator.default_duration / 3600
            value = min(
                max(round(app_default_hours), MIN_MANUAL_DURATION_HOURS),
                MAX_MANUAL_DURATION_HOURS,
            )
        self._value = value
        self.coordinator.room_duration_hours[self._room_id] = value

    @property
    def native_value(self) -> float | None:
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        self._value = value
        self.coordinator.room_duration_hours[self._room_id] = value
        self.async_write_ha_state()

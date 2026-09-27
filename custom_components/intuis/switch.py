"""Interrupteur 'fenêtre ouverte' par pièce — lecture ET écriture.

Contrairement à l'intégration HomeKit d'origine (où cette info est en
lecture seule), ce switch envoie la commande `open_window` à l'API Intuis
quand on le bascule, exactement comme le fait l'appli mobile : il peut donc
être piloté par une automatisation à partir d'un vrai capteur d'ouverture.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IntuisDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: IntuisDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        IntuisWindowSwitch(coordinator, room_id) for room_id in coordinator.data["rooms"]
    )


class IntuisWindowSwitch(CoordinatorEntity[IntuisDataUpdateCoordinator], SwitchEntity):
    """État fenêtre ouverte/fermée d'une pièce, forçable manuellement."""

    _attr_has_entity_name = True
    _attr_name = "Fenêtre ouverte"
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:window-open-variant"

    def __init__(self, coordinator: IntuisDataUpdateCoordinator, room_id: str) -> None:
        super().__init__(coordinator)
        self._room_id = room_id
        self._attr_unique_id = f"{coordinator.home_id}_{room_id}_open_window"
        room = coordinator.data["rooms"][room_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room_id)}, name=room.get("name", room_id)
        )

    @property
    def _room(self) -> dict[str, Any]:
        return self.coordinator.data["rooms"][self._room_id]

    @property
    def is_on(self) -> bool:
        return bool(self._room.get("open_window", False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_room_state(
            self.coordinator.home_id, self._room_id, open_window=True
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_room_state(
            self.coordinator.home_id, self._room_id, open_window=False
        )
        await self.coordinator.async_request_refresh()

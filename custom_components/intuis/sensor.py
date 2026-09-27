"""Capteurs de consommation électrique (expérimental) pour Intuis Connect.

⚠️ Basé sur un endpoint non documenté (`/api/gethomemeasure`), repéré via les
retours de la communauté HACF (flow Node-RED "Intuis connect sans HomeKit").
Netatmo réserve normalement cet endpoint aux applications "de confiance"
(webapp / appli native) ; comme cette intégration réutilise le client OAuth
de l'appli mobile Intuis Connect elle-même, l'appel fonctionne en pratique,
mais rien ne garantit qu'il continue de le faire dans le temps. Si les
valeurs semblent fausses ou toujours à 0, regarde les logs (`custom_components.intuis`
en debug) et ajuste au besoin `ENERGY_MEASURE_TYPES` dans `const.py`.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IntuisDataUpdateCoordinator, IntuisEnergyCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    domain_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: IntuisDataUpdateCoordinator = domain_data["coordinator"]
    energy_coordinator: IntuisEnergyCoordinator = domain_data["energy_coordinator"]

    async_add_entities(
        IntuisRoomEnergySensor(coordinator, energy_coordinator, room_id)
        for room_id in coordinator.data["rooms"]
    )


class IntuisRoomEnergySensor(CoordinatorEntity[IntuisEnergyCoordinator], SensorEntity):
    """Consommation électrique du jour pour une pièce (rattachable au même appareil que son thermostat)."""

    _attr_has_entity_name = True
    _attr_name = "Consommation électrique du jour"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_icon = "mdi:lightning-bolt"

    def __init__(
        self,
        main_coordinator: IntuisDataUpdateCoordinator,
        energy_coordinator: IntuisEnergyCoordinator,
        room_id: str,
    ) -> None:
        super().__init__(energy_coordinator)
        self._main = main_coordinator
        self._room_id = room_id
        self._attr_unique_id = f"{main_coordinator.home_id}_{room_id}_energy_today"
        room = main_coordinator.data["rooms"][room_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room_id)}, name=room.get("name", room_id)
        )

    @property
    def native_value(self) -> float | None:
        wh = self.coordinator.data.get(self._room_id)
        if wh is None:
            return None
        return round(wh / 1000, 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "note": "Endpoint non officiel, valeur expérimentale (voir sensor.py).",
        }

    @property
    def available(self) -> bool:
        return super().available and self._room_id in (self.coordinator.data or {})

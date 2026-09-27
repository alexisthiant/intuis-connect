"""Entités thermostat (une par pièce/radiateur) pour Intuis Connect."""
from __future__ import annotations

import logging
import time
from typing import Any

import voluptuous as vol

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MAX_MANUAL_DURATION_HOURS,
    MIN_MANUAL_DURATION_HOURS,
    ROOM_MODE_FROST,
    ROOM_MODE_HOME,
    ROOM_MODE_MANUAL,
    ROOM_MODE_OFF,
    SERVICE_SET_MANUAL_TEMPERATURE,
)
from .coordinator import IntuisDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PRESET_HOME = "home"
PRESET_FROST = "hg"
PRESET_MODES = [PRESET_HOME, PRESET_FROST]

MIN_TEMP = 7.0
MAX_TEMP = 30.0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: IntuisDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        IntuisRoomClimate(coordinator, room_id) for room_id in coordinator.data["rooms"]
    )

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_MANUAL_TEMPERATURE,
        {
            vol.Required(ATTR_TEMPERATURE): vol.Coerce(float),
            vol.Required("duration_hours"): vol.All(
                vol.Coerce(float),
                vol.Range(min=MIN_MANUAL_DURATION_HOURS, max=MAX_MANUAL_DURATION_HOURS),
            ),
        },
        "async_set_manual_temperature",
    )


class IntuisRoomClimate(CoordinatorEntity[IntuisDataUpdateCoordinator], ClimateEntity):
    """Thermostat pour une pièce / un radiateur Intuis.

    - hvac_mode AUTO  -> le radiateur suit le planning de la maison ("Home")
    - hvac_mode HEAT  -> consigne manuelle fixe (comme le + / - de l'appli)
    - preset "hg"     -> mode Hors Gel pour cette pièce
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_translation_key = "room"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT]
    _attr_preset_modes = PRESET_MODES
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )

    def __init__(self, coordinator: IntuisDataUpdateCoordinator, room_id: str) -> None:
        super().__init__(coordinator)
        self._room_id = room_id
        self._attr_unique_id = f"{coordinator.home_id}_{room_id}_climate"
        room = coordinator.data["rooms"][room_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room_id)},
            name=room.get("name", room_id),
            manufacturer="Intuis (Muller / Legrand)",
            model=room.get("type", "Radiateur"),
            via_device=(DOMAIN, coordinator.home_id or "intuis"),
        )

    @property
    def _room(self) -> dict[str, Any]:
        return self.coordinator.data["rooms"][self._room_id]

    @property
    def name(self) -> str:
        return self._room.get("name", self._room_id)

    @property
    def current_temperature(self) -> float | None:
        return self._room.get("therm_measured_temperature")

    @property
    def target_temperature(self) -> float | None:
        return self._room.get("therm_setpoint_temperature")

    @property
    def hvac_mode(self) -> HVACMode:
        if self._room.get("therm_setpoint_mode") == ROOM_MODE_MANUAL:
            return HVACMode.HEAT
        return HVACMode.AUTO

    @property
    def hvac_action(self) -> HVACAction | None:
        # L'API ne fournit pas d'état "en train de chauffer" ; on ne remonte
        # que le cas où le radiateur est physiquement coupé.
        if self._room.get("therm_setpoint_mode") == ROOM_MODE_OFF:
            return HVACAction.OFF
        return None

    @property
    def preset_mode(self) -> str | None:
        if self._room.get("therm_setpoint_mode") == ROOM_MODE_FROST:
            return PRESET_FROST
        return PRESET_HOME

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "open_window": self._room.get("open_window", False),
            "reachable": self._room.get("reachable"),
            "raw_mode": self._room.get("therm_setpoint_mode"),
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        duration_hours = self.coordinator.default_duration / 3600
        await self._async_apply_manual_setpoint(float(temperature), duration_hours)

    async def async_set_manual_temperature(self, temperature: float, duration_hours: float) -> None:
        """Consigne manuelle avec durée choisie (1 à 12h) — service intuis.set_manual_temperature."""
        await self._async_apply_manual_setpoint(temperature, duration_hours)

    async def _async_apply_manual_setpoint(self, temperature: float, duration_hours: float) -> None:
        end_time = int(time.time()) + int(duration_hours * 3600)
        await self.coordinator.client.async_set_room_state(
            self.coordinator.home_id,
            self._room_id,
            therm_setpoint_mode=ROOM_MODE_MANUAL,
            therm_setpoint_temperature=float(temperature),
            therm_setpoint_end_time=end_time,
        )
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.AUTO:
            await self.coordinator.client.async_set_room_state(
                self.coordinator.home_id,
                self._room_id,
                boost=False,
                therm_setpoint_mode=ROOM_MODE_HOME,
            )
            await self.coordinator.async_request_refresh()
        elif hvac_mode == HVACMode.HEAT:
            # Repasse en manuel à la consigne actuellement affichée.
            await self.async_set_temperature(temperature=self.target_temperature or MIN_TEMP)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_FROST:
            await self.coordinator.client.async_set_room_state(
                self.coordinator.home_id, self._room_id, therm_setpoint_mode=ROOM_MODE_FROST
            )
        else:
            await self.coordinator.client.async_set_room_state(
                self.coordinator.home_id,
                self._room_id,
                boost=False,
                therm_setpoint_mode=ROOM_MODE_HOME,
            )
        await self.coordinator.async_request_refresh()

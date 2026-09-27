"""Coordinateur de mise à jour pour l'intégration Intuis Connect."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from homeassistant.util import dt as dt_util

from .api import IntuisApiClient, IntuisApiError, IntuisAuthError
from .const import (
    DEFAULT_BOOST_DURATION_SECONDS,
    DOMAIN,
    ENERGY_UPDATE_INTERVAL_SECONDS,
    UPDATE_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class IntuisDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Récupère périodiquement l'état complet de l'installation Intuis."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: IntuisApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.client = client
        self.home_id: str | None = None
        self.default_duration: int = DEFAULT_BOOST_DURATION_SECONDS

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            home = await self.client.async_get_homesdata()
            self.home_id = home["id"]
            rooms_status = await self.client.async_get_homestatus(self.home_id)
            if self.data is None:
                self.default_duration = await self.client.async_get_default_boost_duration(
                    self.home_id
                )
        except IntuisAuthError as err:
            raise ConfigEntryAuthFailed("Session Intuis Connect invalide") from err
        except IntuisApiError as err:
            raise UpdateFailed(str(err)) from err

        rooms_meta = {room["id"]: room for room in home.get("rooms", [])}
        rooms_status_by_id = {room["id"]: room for room in rooms_status}

        rooms: dict[str, dict[str, Any]] = {}
        for room_id, meta in rooms_meta.items():
            rooms[room_id] = {**meta, **rooms_status_by_id.get(room_id, {})}

        return {"home": home, "rooms": rooms}


class IntuisEnergyCoordinator(DataUpdateCoordinator[dict[str, float]]):
    """Récupère périodiquement la consommation électrique du jour, par pièce.

    Interroge un endpoint non documenté (voir `api.async_get_home_energy_today`)
    ; une fréquence plus faible que le coordinateur principal suffit largement
    et limite le risque de sollicitation excessive de ce endpoint fragile.
    """

    def __init__(
        self, hass: HomeAssistant, main_coordinator: IntuisDataUpdateCoordinator
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_energy",
            update_interval=timedelta(seconds=ENERGY_UPDATE_INTERVAL_SECONDS),
        )
        self._main = main_coordinator

    async def _async_update_data(self) -> dict[str, float]:
        home_id = self._main.home_id
        if home_id is None:
            return {}

        start_of_day = dt_util.start_of_local_day()
        date_begin = int(start_of_day.timestamp())
        date_end = int(dt_util.utcnow().timestamp())

        try:
            return await self._main.client.async_get_home_energy_today(
                home_id, date_begin, date_end
            )
        except IntuisAuthError as err:
            raise ConfigEntryAuthFailed("Session Intuis Connect invalide") from err
        except IntuisApiError as err:
            # Endpoint non officiel : on log en debug plutôt que de faire
            # échouer bruyamment l'intégration si Netatmo/Intuis le ferme.
            _LOGGER.debug("Consommation électrique indisponible: %s", err)
            raise UpdateFailed(str(err)) from err

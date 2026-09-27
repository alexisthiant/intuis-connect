"""Intégration Home Assistant non-officielle pour Intuis Connect (Muller Intuitiv)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IntuisApiClient
from .const import DOMAIN
from .coordinator import IntuisDataUpdateCoordinator, IntuisEnergyCoordinator

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialise l'intégration à partir d'une config entry."""
    session = async_get_clientsession(hass)
    client = IntuisApiClient(session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

    coordinator = IntuisDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    energy_coordinator = IntuisEnergyCoordinator(hass, coordinator)
    # La conso est optionnelle/expérimentale : un échec ici ne doit pas
    # empêcher le reste de l'intégration de fonctionner.
    await energy_coordinator.async_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "energy_coordinator": energy_coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge une config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

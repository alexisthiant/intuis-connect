"""Config flow pour Intuis Connect (Muller Intuitiv)."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IntuisApiClient, IntuisApiError, IntuisAuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class IntuisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère la configuration de l'intégration Intuis Connect."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = IntuisApiClient(
                session, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            try:
                await client.async_login()
                home = await client.async_get_homesdata()
            except IntuisAuthError:
                errors["base"] = "invalid_auth"
            except IntuisApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(home["id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=home.get("name") or "Intuis Connect",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

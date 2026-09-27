"""Client API pour Intuis Connect (Muller Intuitiv).

Reverse-engineered à partir du plugin Jeedom "jeedom-plugin-MullerIntuitiv"
(https://github.com/shun84/jeedom-plugin-mullerintuitiv), qui documente les
mêmes endpoints "syncapi" que ceux utilisés par Netatmo Energy. Aucune
affiliation avec Intuis / Muller / Legrand.
"""
from __future__ import annotations

import base64
import logging
import time
from typing import Any

import aiohttp

from .const import (
    BASE_URL,
    CLIENT_ID_B64,
    CLIENT_SECRET_B64,
    DEFAULT_BOOST_DURATION_SECONDS,
    ENERGY_MEASURE_TYPES,
)

_LOGGER = logging.getLogger(__name__)


class IntuisApiError(Exception):
    """Erreur générique lors d'un appel à l'API Intuis."""


class IntuisAuthError(IntuisApiError):
    """Identifiants invalides ou session impossible à rafraîchir."""


class IntuisApiClient:
    """Petit wrapper HTTP asynchrone autour de l'API cloud Intuis Connect."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._client_id = base64.b64decode(CLIENT_ID_B64).decode()
        self._client_secret = base64.b64decode(CLIENT_SECRET_B64).decode()
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0.0
        self._home_id: str | None = None

    # ------------------------------------------------------------------ #
    # Authentification
    # ------------------------------------------------------------------ #

    async def async_login(self) -> None:
        """Authentification initiale par identifiant / mot de passe."""
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "user_prefix": "muller",
            "grant_type": "password",
            "scope": "read_muller write_muller",
            "username": self._username,
            "password": self._password,
        }
        await self._async_token_request(data)

    async def _async_refresh(self) -> None:
        if not self._refresh_token:
            await self.async_login()
            return
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
        }
        try:
            await self._async_token_request(data)
        except IntuisApiError:
            # Le refresh token a pu lui aussi expirer : on retente un login complet.
            await self.async_login()

    async def _async_token_request(self, data: dict[str, str]) -> None:
        try:
            async with self._session.post(f"{BASE_URL}/oauth2/token", data=data) as resp:
                if resp.status in (400, 401):
                    raise IntuisAuthError("Identifiants Intuis Connect refusés")
                resp.raise_for_status()
                payload = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise IntuisApiError(f"Erreur réseau lors de l'authentification: {err}") from err

        self._access_token = payload["access_token"]
        self._refresh_token = payload.get("refresh_token", self._refresh_token)
        self._expires_at = time.time() + payload.get("expires_in", 3600)

    async def _async_ensure_token(self) -> str:
        if not self._access_token:
            await self.async_login()
        elif time.time() > self._expires_at - 60:
            await self._async_refresh()
        assert self._access_token is not None
        return self._access_token

    # ------------------------------------------------------------------ #
    # Requêtes génériques
    # ------------------------------------------------------------------ #

    async def _async_request(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        token = await self._async_ensure_token()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        try:
            async with self._session.post(f"{BASE_URL}{path}", headers=headers, json=json) as resp:
                if resp.status == 401:
                    # Token invalidé côté serveur entre deux appels : on rafraîchit et on
                    # retente une seule fois.
                    await self._async_refresh()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    async with self._session.post(
                        f"{BASE_URL}{path}", headers=headers, json=json
                    ) as retry_resp:
                        retry_resp.raise_for_status()
                        return await retry_resp.json(content_type=None)
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise IntuisApiError(f"Erreur d'appel API Intuis ({path}): {err}") from err

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #

    async def async_get_home_id(self) -> str:
        if self._home_id is None:
            home = await self.async_get_homesdata()
            self._home_id = home["id"]
        return self._home_id

    async def async_get_homesdata(self) -> dict[str, Any]:
        """Structure statique de l'installation : pièces, plannings, mode maison."""
        payload = await self._async_request("/api/homesdata")
        home = payload["body"]["homes"][0]
        self._home_id = home["id"]
        return home

    async def async_get_homestatus(self, home_id: str) -> list[dict[str, Any]]:
        """État courant (température, consigne, fenêtre...) de chaque pièce."""
        payload = await self._async_request("/syncapi/v1/homestatus", {"home_id": home_id})
        return payload["body"]["home"]["rooms"]

    async def async_get_default_boost_duration(self, home_id: str) -> int:
        """Durée par défaut (s) d'une dérogation manuelle, réglée dans l'appli Intuis."""
        try:
            payload = await self._async_request("/syncapi/v1/getconfigs", {"home_id": home_id})
            modules = payload["body"]["home"]["modules"]
            for module in modules:
                if "therm_setpoint_default_duration" in module:
                    return int(module["therm_setpoint_default_duration"]) * 60
        except (IntuisApiError, KeyError, IndexError, TypeError):
            _LOGGER.debug("Durée de dérogation par défaut indisponible, valeur de repli utilisée")
        return DEFAULT_BOOST_DURATION_SECONDS

    async def async_get_home_energy_today(
        self, home_id: str, date_begin: int, date_end: int
    ) -> dict[str, float]:
        """Consommation électrique (Wh) du jour, par pièce.

        Interroge en une seule fois les différents types de mesure possibles
        (tarif unique / heures pleines / heures creuses / pas de contrat) et
        retient, pour chaque pièce, le premier type qui renvoie une valeur.
        Retourne un dict {room_id: wh_du_jour}.
        """
        payload = await self._async_request(
            "/api/gethomemeasure",
            {
                "home_id": home_id,
                "scale": "1day",
                "type": ENERGY_MEASURE_TYPES,
                "date_begin": date_begin,
                "date_end": date_end,
                "real_time": False,
            },
        )

        rooms = payload.get("body", {}).get("home", {}).get("rooms", [])
        result: dict[str, float] = {}
        for room in rooms:
            room_id = room.get("id")
            if room_id is None:
                continue
            totals_by_type = [0.0] * len(ENERGY_MEASURE_TYPES)
            for measure in room.get("measures", []):
                for bucket in measure.get("value") or []:
                    for idx, val in enumerate(bucket):
                        if idx < len(totals_by_type) and val is not None:
                            totals_by_type[idx] += float(val)
            # On garde le premier type dont le total est strictement positif ;
            # à défaut (rien consommé aujourd'hui), on garde le premier type
            # défini, qui vaut alors légitimement 0.
            chosen = next((t for t in totals_by_type if t > 0), totals_by_type[0])
            result[room_id] = chosen
        return result

    # ------------------------------------------------------------------ #
    # Écriture
    # ------------------------------------------------------------------ #

    async def async_set_home_mode(self, home_id: str, mode: str) -> None:
        """Applique le mode maison : schedule (programmation) / hg (hors gel) / away (absent)."""
        await self._async_request("/api/setthermmode", {"mode": mode, "home_id": home_id})

    async def async_switch_schedule(self, home_id: str, schedule_id: str) -> None:
        """Active un planning de chauffe existant."""
        await self._async_request(
            "/api/switchhomeschedule", {"schedule_id": schedule_id, "home_id": home_id}
        )

    async def async_set_room_state(self, home_id: str, room_id: str, **fields: Any) -> None:
        """Applique un patch d'état à une pièce (mode, consigne, fenêtre, boost...)."""
        room_patch = {"id": room_id, **fields}
        await self._async_request(
            "/syncapi/v1/setstate", {"home": {"id": home_id, "rooms": [room_patch]}}
        )

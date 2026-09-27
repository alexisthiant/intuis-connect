"""Constantes pour l'intégration Intuis Connect (Muller Intuitiv)."""
from __future__ import annotations

DOMAIN = "intuis"

BASE_URL = "https://app.muller-intuitiv.net"

# Identifiants OAuth "publics" utilisés par l'application mobile officielle
# Intuis Connect. Ils sont partagés par tous les utilisateurs (constaté par
# la communauté Jeedom / Node-RED qui a rétro-ingénieré cette API) ; seuls le
# login et le mot de passe du compte utilisateur sont personnels.
CLIENT_ID_B64 = "NTllNjA0OTQ4ZmUyODNmZDRkYzdlMzU1"
CLIENT_SECRET_B64 = "ckFlV3U4WTNZcVhFUHFSSjRCcEZ6Rkc5OE1SWHBDY3o="

UPDATE_INTERVAL_SECONDS = 60

# Modes de fonctionnement au niveau de la maison (widget "Home" de l'appli
# Intuis Connect).
HOME_MODE_SCHEDULE = "schedule"
HOME_MODE_FROST = "hg"
HOME_MODE_AWAY = "away"
HOME_MODES = [HOME_MODE_SCHEDULE, HOME_MODE_FROST, HOME_MODE_AWAY]

# Modes de fonctionnement au niveau d'une pièce / d'un radiateur.
ROOM_MODE_HOME = "home"
ROOM_MODE_FROST = "hg"
ROOM_MODE_MANUAL = "manual"
ROOM_MODE_OFF = "off"

DEFAULT_BOOST_DURATION_SECONDS = 3 * 60 * 60

# --- Suivi de consommation (expérimental) ------------------------------- #
# Endpoint non documenté, repéré via les retours de la communauté HACF
# (flow Node-RED "Intuis connect"). Netatmo réserve normalement cet
# endpoint aux applications "de confiance" (webapp / appli native) ; comme
# cette intégration réutilise le client OAuth de l'appli mobile Intuis
# Connect elle-même, l'appel passe, mais rien ne garantit sa pérennité.
#
# Suivant que le compte a renseigné ou non un contrat électrique dans
# l'appli, le type de mesure exploitable diffère (tarif unique, heures
# pleines/creuses, ou pas de contrat du tout). On les demande tous en une
# seule fois et on retient le premier qui répond une valeur exploitable.
ENERGY_MEASURE_TYPES = [
    "sum_energy_elec$0",
    "sum_energy_elec$1",
    "sum_energy_elec$2",
    "sum_energy_elec",
]
ENERGY_UPDATE_INTERVAL_SECONDS = 15 * 60

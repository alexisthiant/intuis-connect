# Intuis Connect pour Home Assistant (intégration custom, non officielle)

Intégration custom pour piloter des radiateurs Intuis Connect / Muller
Intuitiv (Legrand) directement via l'API cloud utilisée par l'appli mobile,
**sans passer par HomeKit**. Basée sur le protocole documenté par le plugin
Jeedom `jeedom-plugin-MullerIntuitiv` (mêmes endpoints "syncapi" que Netatmo
Energy).

⚠️ Projet non affilié à Intuis / Muller / Legrand. L'API n'étant pas
publique, elle peut changer sans préavis.

## Ce que ça apporte par rapport à HomeKit

- **`climate.*`** : un thermostat par pièce/radiateur (température mesurée,
  consigne, mode Auto/Manuel, preset Hors gel).
- **`select.mode_de_la_maison`** et **`select.planning_actif`** : pilotage
  global de l'installation comme le widget "Home" de l'appli (Programmation
  / Hors gel / Absent, choix du planning actif).
- **`switch.fenetre_ouverte`** (un par pièce) : **lecture ET écriture**. Tu
  peux le combiner avec un vrai capteur d'ouverture de fenêtre dans une
  automatisation pour déclencher/lever le mode fenêtre ouverte, ce que
  l'intégration HomeKit ne permet pas.

## Installation

1. Copie le dossier `custom_components/intuis` de cette archive dans le
   dossier `custom_components` de ta configuration Home Assistant (le créer
   s'il n'existe pas), pour obtenir :
   `<config>/custom_components/intuis/...`
2. Redémarre Home Assistant.
3. **Paramètres → Appareils et services → Ajouter une intégration**, cherche
   "Intuis Connect".
4. Renseigne l'e-mail et le mot de passe de ton compte Intuis Connect (les
   mêmes que dans l'appli mobile).

Les entités sont créées automatiquement pour chaque pièce détectée, plus les
deux sélecteurs globaux.

- **`sensor.*` — Consommation électrique du jour** (kWh, par pièce,
  ⚠️ **expérimental**, voir plus bas) : compatible avec le tableau de bord
  Énergie (section "Appareils individuels"), comme dans l'appli Intuis.

## ⚠️ À propos du suivi de consommation

Il repose sur un endpoint (`/api/gethomemeasure`) **non documenté**, que
Netatmo réserve normalement aux applications "de confiance" (webapp / appli
native) — un développeur tiers avec son propre `client_id` n'y a pas accès.
Cette intégration s'en sort seulement parce qu'elle réutilise le client
OAuth de l'appli mobile Intuis Connect elle-même (comme documenté par la
communauté HACF et son flow Node-RED). Concrètement :

- Ça peut cesser de fonctionner du jour au lendemain si Intuis/Netatmo
  change quelque chose côté serveur — sans lien avec un bug de
  l'intégration.
- La consommation est **par pièce**, pas par radiateur : si plusieurs
  radiateurs partagent une pièce, tu n'auras qu'un seul total.
- Le type de mesure à utiliser dépend de si tu as renseigné un contrat
  électrique dans l'appli (tarif unique / heures pleines-creuses / aucun
  contrat) : l'intégration essaie les 4 variantes possibles à chaque appel
  et garde celle qui répond une valeur. Si les chiffres semblent faux,
  regarde les logs (`custom_components.intuis` en `debug`) et ajuste
  `ENERGY_MEASURE_TYPES` dans `const.py` si besoin.
- Rafraîchi toutes les 15 min (indépendamment des thermostats, à 60 s) pour
  limiter la sollicitation de cet endpoint fragile — réglable via
  `ENERGY_UPDATE_INTERVAL_SECONDS`.

## Limites connues / pistes d'amélioration

- Pas de détection de présence (non exposée par cette API).
- Le radiateur ne peut pas être remis en position "off" matériel depuis
  Home Assistant — l'API ne l'expose pas (comportement identique à HomeKit
  sur ce point).
- Intervalle de rafraîchissement : 60 s (ajustable dans `const.py`,
  `UPDATE_INTERVAL_SECONDS`).

## Détail technique (pour toi si tu veux l'étendre)

- `api.py` : client HTTP (OAuth password grant, refresh automatique, tous
  les appels `syncapi`/`api`).
- `coordinator.py` : un seul polling toutes les 60 s qui alimente toutes les
  entités.
- `climate.py`, `select.py`, `switch.py` : les entités.
- `config_flow.py` : formulaire de connexion dans l'UI (pas de YAML requis).

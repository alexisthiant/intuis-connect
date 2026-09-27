<p align="center">
  <img src="brands/intuis/icon@2x.png" width="110" alt="Logo Intuis Connect">
</p>

# Intuis Connect – Intégration Home Assistant (non officielle)

🇫🇷 Français | [🇬🇧 English](README.en.md)

> **Pilotage des radiateurs électriques Intuis / Muller Intuitiv (Legrand)** directement depuis Home Assistant, sans passer par HomeKit — thermostats par pièce, pilotage global de l'installation, gestion de la fenêtre ouverte en écriture, et suivi de consommation.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/alexisthiant/intuis-connect)](https://github.com/alexisthiant/intuis-connect/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

⚠️ Projet non affilié à Intuis / Muller / Legrand. Basé sur une API cloud non publique ; voir [Détails techniques](#détails-techniques).

---

## Fonctionnalités en un coup d'œil

| Fonctionnalité | Description |
| --- | --- |
| **Thermostats par pièce** | Un `climate.*` par radiateur/pièce : température mesurée, consigne, mode Auto/Manuel |
| **Consigne manuelle à durée choisie** | Service dédié pour fixer une température **et sa durée (1 à 12h)**, plutôt que la durée fixe de l'appli |
| **Pilotage global de la maison** | Sélecteurs Programmation / Hors gel / Absent, et choix du planning actif — comme le widget "Home" de l'appli |
| **Fenêtre ouverte en écriture** | Un `switch.*` par pièce, pas juste un capteur : automatisable avec un vrai détecteur d'ouverture |
| **Suivi de consommation** ⚠️ expérimental | `sensor.*` de consommation électrique du jour (kWh) par pièce, compatible tableau de bord Énergie |

---

## Installation

> Nécessite Home Assistant récent (2024.1+) ; HACS optionnel mais recommandé.

### Installation en un clic

[![Ouvre ton instance Home Assistant et ajoute ce dépôt dans HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=alexisthiant&repository=intuis-connect&category=integration)

### Via HACS (dépôt personnalisé)

1. HACS → les trois points **⋮** → **Dépôts personnalisés**
2. URL : `https://github.com/alexisthiant/intuis-connect` — catégorie **Intégration**
3. Cherche "Intuis Connect" dans HACS → **Télécharger** → redémarre Home Assistant

### Installation manuelle

1. Copie le dossier `custom_components/intuis` dans `<config>/custom_components/`
2. Redémarre Home Assistant

### Configuration

1. **Paramètres → Appareils et services → + Ajouter une intégration**
2. Cherche **Intuis Connect**
3. Renseigne l'e-mail et le mot de passe de ton compte Intuis Connect (les mêmes que dans l'appli mobile)

---

## Entités créées

### Par pièce

| Type | Entité | Description |
| --- | --- | --- |
| **Climate** | `climate.<pièce>` | Thermostat complet (mesure, consigne, Auto/Manuel, preset Hors gel) |
| **Switch** | `switch.<pièce>_fenetre_ouverte` | État fenêtre ouverte, pilotable (lecture **et** écriture) |
| **Sensor** ⚠️ | `sensor.<pièce>_consommation_electrique_du_jour` | Consommation du jour en kWh (endpoint non officiel) |

### Niveau maison

| Type | Entité | Description |
| --- | --- | --- |
| **Select** | `select.mode_de_la_maison` | Programmation / Hors gel / Absent |
| **Select** | `select.planning_actif` | Choix du planning de chauffe actif |

---

## Modes climate & presets

### Modes HVAC

| Mode | Description |
| --- | --- |
| **Auto** | Le radiateur suit le planning/mode de la maison |
| **Heat** | Consigne manuelle fixe (durée par défaut de l'appli) |

### Presets

| Preset | Description |
| --- | --- |
| **home** | Retour au mode programmé (planning de la maison) |
| **hg** | Hors gel pour cette pièce uniquement |

---

## Services

### `intuis.set_manual_temperature`

Applique une consigne manuelle **avec une durée choisie de 1h à 12h**, au lieu de la durée par défaut de l'appli Intuis Connect. C'est la réponse directe au besoin « je veux définir la température ET sa durée » pour chaque radiateur.

```yaml
service: intuis.set_manual_temperature
target:
  entity_id: climate.salon
data:
  temperature: 21.5
  duration_hours: 4
```

Passé le délai, le radiateur repasse automatiquement en mode programmé (Auto), exactement comme le fait l'appli mobile à l'expiration d'une dérogation manuelle.

---

## Suivi de consommation ⚠️

Repose sur un endpoint non documenté (`/api/gethomemeasure`), repéré via les retours de la communauté HACF (flow Node-RED "Intuis connect sans HomeKit"). Netatmo réserve normalement cet endpoint aux applications "de confiance" (webapp/appli native) ; cette intégration s'en sort en réutilisant le client OAuth de l'appli mobile elle-même — ça fonctionne en pratique, mais rien ne garantit que ça continue.

- Consommation **par pièce**, pas par radiateur individuel
- Rafraîchie toutes les 15 min (indépendamment des thermostats, à 60s)
- Si les valeurs semblent fausses, active les logs `debug` sur `custom_components.intuis` et ajuste `ENERGY_MEASURE_TYPES` dans `const.py` si besoin (tarif unique / heures pleines-creuses / pas de contrat)

---

## Exemples de tableau de bord

### Carte thermostat

```yaml
type: thermostat
entity: climate.salon
```

### Bouton "boost 2h" avec la consigne à durée choisie

```yaml
type: button
icon: mdi:fire
name: Boost salon 2h
tap_action:
  action: call-service
  service: intuis.set_manual_temperature
  target:
    entity_id: climate.salon
  data:
    temperature: 22
    duration_hours: 2
```

### Sélecteur de mode maison

```yaml
type: entities
entities:
  - entity: select.mode_de_la_maison
  - entity: select.planning_actif
```

### Historique de consommation

```yaml
type: history-graph
entities:
  - entity: sensor.salon_consommation_electrique_du_jour
hours_to_show: 168
```

---

## Dépannage

### Le thermostat ne répond pas

- Vérifie les logs Home Assistant pour une erreur d'API
- Vérifie que les identifiants Intuis Connect sont toujours valides (pas de mot de passe changé, pas de 2FA)
- Supprime puis rajoute l'intégration pour forcer une réauthentification

### La consommation reste à 0

- L'endpoint est expérimental (voir plus haut) : active les logs `debug`
- Vérifie que le radiateur a effectivement chauffé dans la journée en cours

### Une pièce manque

- Vérifie dans les logs `debug` le contenu de la réponse `/api/homesdata`
- Redémarre Home Assistant après tout changement de configuration côté appli Intuis

---

## Détails techniques

- **Intervalle de rafraîchissement** : 60s pour les thermostats, 15 min pour la consommation
- **API** : endpoints cloud Netatmo/Intuis (`app.muller-intuitiv.net`), OAuth password grant avec rafraîchissement automatique
- **Source du protocole** : reverse engineering documenté par le plugin Jeedom [`jeedom-plugin-MullerIntuitiv`](https://github.com/shun84/jeedom-plugin-mullerintuitiv) et le [flow Node-RED de la communauté HACF](https://forum.hacf.fr/t/integration-radiateurs-intuis-connect-sans-homekit/41313)

---

## Projets connexes

Si tu cherches davantage de fonctionnalités (édition des plannings, détection de présence, calendrier, import d'historique de consommation...), regarde [antoine-pyre/intuis-connect](https://github.com/antoine-pyre/intuis-connect), une intégration Intuis plus complète, développée indépendamment.

---

## Licence

MIT — voir [LICENSE](LICENSE).

## Crédits

Développé pour un usage personnel, à partir du protocole documenté par [`jeedom-plugin-MullerIntuitiv`](https://github.com/shun84/jeedom-plugin-mullerintuitiv) et la communauté [HACF](https://forum.hacf.fr/t/integration-radiateurs-intuis-connect-sans-homekit/41313).

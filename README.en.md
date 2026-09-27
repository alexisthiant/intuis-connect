<p align="center">
  <img src="brands/intuis/icon@2x.png" width="110" alt="Intuis Connect logo">
</p>

# Intuis Connect – Home Assistant Integration (unofficial)

[🇫🇷 Français](README.md) | 🇬🇧 English

> **Control your Intuis / Muller Intuitiv (Legrand) electric radiators** directly from Home Assistant, without going through HomeKit — per-room thermostats, whole-installation control, a writable open-window state, and consumption tracking.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/alexisthiant/intuis-connect)](https://github.com/alexisthiant/intuis-connect/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

⚠️ Not affiliated with Intuis / Muller / Legrand. Based on a non-public cloud API; see [Technical details](#technical-details).

---

## Features at a Glance

| Feature | Description |
| --- | --- |
| **Per-room thermostats** | One `climate.*` per radiator/room: measured temperature, setpoint, Auto/Manual mode |
| **Manual setpoint with custom duration** | Dedicated service to set a temperature **and its duration (1 to 12h)**, instead of the app's fixed duration |
| **Whole-home control** | Schedule / Frost protection / Away selectors, plus active schedule selection — like the app's "Home" widget |
| **Writable open-window state** | A `switch.*` per room, not just a sensor: automatable with a real window sensor |
| **Consumption tracking** ⚠️ experimental | Daily electricity consumption `sensor.*` (kWh) per room, compatible with the Energy dashboard |

---

## Installation

> Requires a recent Home Assistant (2024.1+); HACS optional but recommended.

### One-Click Install

[![Open your Home Assistant instance and add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=alexisthiant&repository=intuis-connect&category=integration)

### Via HACS (custom repository)

1. HACS → the three dots **⋮** → **Custom repositories**
2. URL: `https://github.com/alexisthiant/intuis-connect` — category **Integration**
3. Search for "Intuis Connect" in HACS → **Download** → restart Home Assistant

### Manual Install

1. Copy the `custom_components/intuis` folder into `<config>/custom_components/`
2. Restart Home Assistant

### Configuration

1. **Settings → Devices & Services → + Add Integration**
2. Search for **Intuis Connect**
3. Enter the email and password of your Intuis Connect account (the same ones used in the mobile app)

---

## Entities Created

### Per Room

| Type | Entity | Description |
| --- | --- | --- |
| **Climate** | `climate.<room>` | Full thermostat (measured temperature, setpoint, Auto/Manual, Frost preset) |
| **Number** | `number.<room>_duree_de_consigne_manuelle` | Duration (1-12h) automatically applied when you adjust temperature from the regular thermostat |
| **Switch** | `switch.<room>_open_window` | Open-window state, controllable (read **and** write) |
| **Sensor** ⚠️ | `sensor.<room>_daily_energy` | Today's consumption in kWh (unofficial endpoint) |

### Home Level

| Type | Entity | Description |
| --- | --- | --- |
| **Select** | `select.mode_de_la_maison` | Schedule / Frost protection / Away |
| **Select** | `select.planning_actif` | Active heating schedule selection |

---

## Climate Modes & Presets

### HVAC Modes

| Mode | Description |
| --- | --- |
| **Auto** | The radiator follows the home's schedule/mode |
| **Heat** | Fixed manual setpoint (app's default duration) |

### Presets

| Preset | Description |
| --- | --- |
| **home** | Back to scheduled mode (home's schedule) |
| **hg** | Frost protection for this room only |

---

## Services

### `intuis.set_manual_temperature`

Applies a manual setpoint **with a duration you choose, from 1h to 12h**, for a one-off adjustment, without changing the room's usual setting.

```yaml
service: intuis.set_manual_temperature
target:
  entity_id: climate.salon
data:
  temperature: 21.5
  duration_hours: 4
```

Once the duration expires, the radiator automatically switches back to scheduled mode (Auto), exactly like the mobile app does when a manual override expires.

### Managing duration day-to-day: `number.<room>_duree_de_consigne_manuelle`

So you don't have to call that service every time, each room also has a **Manual setpoint duration** slider (1-12h, visible on the dashboard like any other setting). Once set, this duration is used automatically every time you change the temperature from the regular thermostat (the card's dial, or the `climate.set_temperature` service) — the service above stays available for a different one-off duration, without touching this setting.

---

## Consumption Tracking ⚠️

Relies on an undocumented endpoint (`/api/gethomemeasure`), identified through the HACF community's feedback (the "Intuis connect without HomeKit" Node-RED flow). Netatmo normally reserves this endpoint for "trusted" applications (webapp/native app); this integration gets away with it by reusing the mobile app's own OAuth client — it works in practice, but nothing guarantees it will keep working.

- Consumption is **per room**, not per individual radiator
- Refreshed every 15 min (independently from the thermostats, which poll every 60s)
- If values look wrong, enable `debug` logs on `custom_components.intuis` and adjust `ENERGY_MEASURE_TYPES` in `const.py` if needed (single rate / peak-off-peak / no contract)

---

## Dashboard Examples

### Thermostat Card

```yaml
type: thermostat
entity: climate.salon
```

### "2h boost" button with a custom-duration setpoint

```yaml
type: button
icon: mdi:fire
name: Living room boost 2h
tap_action:
  action: call-service
  service: intuis.set_manual_temperature
  target:
    entity_id: climate.salon
  data:
    temperature: 22
    duration_hours: 2
```

### Home Mode Selector

```yaml
type: entities
entities:
  - entity: select.mode_de_la_maison
  - entity: select.planning_actif
```

### Consumption History

```yaml
type: history-graph
entities:
  - entity: sensor.salon_consommation_electrique_du_jour
hours_to_show: 168
```

---

## Troubleshooting

### The thermostat doesn't respond

- Check the Home Assistant logs for an API error
- Check that your Intuis Connect credentials are still valid (no password change, no 2FA)
- Remove and re-add the integration to force re-authentication

### Consumption stays at 0

- The endpoint is experimental (see above): enable `debug` logs
- Check that the radiator actually heated at some point today

### A room is missing

- Check the `/api/homesdata` response content in `debug` logs
- Restart Home Assistant after any configuration change on the Intuis app side

---

## Technical Details

- **Refresh interval**: 60s for thermostats, 15 min for consumption
- **API**: Netatmo/Intuis cloud endpoints (`app.muller-intuitiv.net`), OAuth password grant with automatic refresh
- **Protocol source**: reverse engineering documented by the Jeedom plugin [`jeedom-plugin-MullerIntuitiv`](https://github.com/shun84/jeedom-plugin-mullerintuitiv) and the [HACF community's Node-RED flow](https://forum.hacf.fr/t/integration-radiateurs-intuis-connect-sans-homekit/41313)

---

## Related Projects

If you're looking for more features (schedule editing, presence detection, calendar, consumption history import...), check out [antoine-pyre/intuis-connect](https://github.com/antoine-pyre/intuis-connect), a more complete Intuis integration developed independently.

---

## License

MIT — see [LICENSE](LICENSE).

## Credits

Built for personal use, based on the protocol documented by [`jeedom-plugin-MullerIntuitiv`](https://github.com/shun84/jeedom-plugin-mullerintuitiv) and the [HACF](https://forum.hacf.fr/t/integration-radiateurs-intuis-connect-sans-homekit/41313) community.

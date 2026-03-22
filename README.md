# ha-uconnect — Home Assistant UConnect Integration (T-Mobile)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/ncecowboy/ha-uconnect.svg)](https://github.com/ncecowboy/ha-uconnect/releases)
[![License](https://img.shields.io/github/license/ncecowboy/ha-uconnect.svg)](LICENSE)

A [Home Assistant](https://www.home-assistant.io/) custom integration for **Stellantis vehicles** (Jeep, RAM, Dodge, Chrysler, Fiat, Alfa Romeo, Maserati) equipped with the **T-Mobile UConnect** telematics dongle. It polls the UConnect cloud API to expose vehicle telemetry as Home Assistant entities and supports remote commands where the vehicle hardware allows.

> **Note:** This integration requires an active UConnect account and a vehicle with T-Mobile connectivity (UConnect dongle).  
> It does **not** support SiriusXM Guardian (older Mopar system).

---

## Table of Contents

1. [Features](#features)
2. [Supported Brands & Regions](#supported-brands--regions)
3. [Requirements](#requirements)
4. [Installation via HACS](#installation-via-hacs)
5. [Manual Installation](#manual-installation)
6. [Configuration](#configuration)
7. [Entities](#entities)
   - [Sensors](#sensors)
   - [Binary Sensors](#binary-sensors)
   - [Device Tracker](#device-tracker)
   - [Locks](#locks)
   - [Switches](#switches)
   - [Buttons](#buttons)
   - [Select](#select)
8. [Services](#services)
9. [API Data Model](#api-data-model)
10. [Advanced: Extrapolated Battery SOC](#advanced-extrapolated-battery-soc)
11. [Options](#options)
12. [Troubleshooting](#troubleshooting)
13. [Contributing](#contributing)
14. [License](#license)

---

## Features

- 🚗 **Vehicle telemetry** — odometer, driving range, tire pressures, oil level, fuel level, battery voltage
- 🔋 **EV / PHEV support** — HV battery state of charge, charging status, charger type, time-to-full
- 🛰️ **GPS location tracking** — live device tracker with Home Assistant zone support
- 🔒 **Remote commands** — lock/unlock doors & trunk, start/stop engine, HVAC, preconditioning, lights, horn, charging
- 📊 **Extrapolated SOC** — real-time battery estimate between API polls with self-learning charge/drain rate
- 🔔 **Warnings** — low fuel, tire pressure warnings per wheel
- 🔄 **Automatic re-authentication** — detects expired sessions and prompts for reauthentication
- ✅ **HACS compatible** — install and update through the Home Assistant Community Store

---

## Supported Brands & Regions

| # | Brand | Region |
|---|-------|--------|
| 1 | Fiat | EU |
| 2 | Fiat | US |
| 3 | RAM | US |
| 4 | Dodge | US |
| 5 | Jeep | EU |
| 6 | Jeep | US ✅ (primary T-Mobile target) |
| 7 | Maserati | Asia |
| 8 | Maserati | EU |
| 9 | Maserati | US / Canada |
| 10 | Chrysler | Canada |
| 11 | Chrysler | US |
| 12 | Alfa Romeo | Asia |
| 13 | Alfa Romeo | EU |
| 14 | Alfa Romeo | US / Canada |
| 15 | Fiat | Asia |
| 16 | Fiat | Canada |
| 17 | Jeep | Asia |

> Brands marked ✅ are most commonly used with the T-Mobile UConnect dongle.  
> Other brands are supported but may have limited testing.

---

## Requirements

- Home Assistant **2023.1** or newer
- A Stellantis vehicle with an active **UConnect** (T-Mobile) subscription
- Your UConnect account **email**, **password**, and optionally a **security PIN**
- Python library: `py-uconnect==0.3.11` (installed automatically)

---

## Installation via HACS

The easiest way to install this integration is through [HACS](https://hacs.xyz/).

1. In Home Assistant, go to **HACS → Integrations**.
2. Click the **⋮ menu** (top right) and select **Custom repositories**.
3. Add `https://github.com/ncecowboy/ha-uconnect` as an **Integration** repository.
4. Search for **UConnect (T-Mobile)** and click **Download**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & Services → Add Integration** and search for **UConnect**.

---

## Manual Installation

1. Download the [latest release](https://github.com/ncecowboy/ha-uconnect/releases).
2. Copy the `custom_components/uconnect` folder into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and search for **UConnect**.

---

## Configuration

The integration is configured entirely through the Home Assistant UI (no YAML required).

### Initial Setup

1. Navigate to **Settings → Devices & Services → + Add Integration**.
2. Search for **UConnect (T-Mobile)**.
3. Fill in:

| Field | Description |
|-------|-------------|
| **Username / Email** | Your UConnect account email |
| **Password** | Your UConnect account password |
| **Brand + Region** | Select the brand and region that matches your vehicle |
| **Security PIN** | Optional PIN required for remote commands |
| **Disable TLS verification** | Enable only if you receive SSL certificate errors |

4. Click **Submit**. The integration will attempt to log in and discover your vehicles.
5. On success, your vehicle(s) will appear as devices in Home Assistant.

---

## Entities

All entities are prefixed with `<Make> <Model/Nickname>` (e.g., `Jeep Grand Cherokee`).  
Entities are only created when the vehicle reports the corresponding data point.

### Sensors

| Entity | Description | Unit |
|--------|-------------|------|
| Odometer | Total distance driven | mi / km |
| Driving Range | Estimated range remaining | mi / km |
| Driving Range (Gas) | Gas-only range (PHEV) | mi / km |
| Driving Range (Total) | Combined EV+gas range (PHEV) | mi / km |
| HV Battery Charge | State of charge | % |
| HV Battery Charge (Extrapolated) | Real-time SOC estimate between polls | % |
| Charger Type | Active charger level (L2, L3, etc.) | — |
| 12V Battery | Auxiliary battery voltage | V |
| Time to Charge L2 | Minutes until full at L2 | min |
| Time to Charge L3 | Minutes until full at L3 | min |
| Front Left Tire Pressure | Tyre pressure — front left | psi / bar |
| Front Right Tire Pressure | Tyre pressure — front right | psi / bar |
| Rear Left Tire Pressure | Tyre pressure — rear left | psi / bar |
| Rear Right Tire Pressure | Tyre pressure — rear right | psi / bar |
| Oil Level | Engine oil level | % |
| Fuel Remaining | Fuel tank level | % |
| Distance to Service | Distance until next service | mi / km |
| Days till Service Needed | Days until next service | days |
| Last Info Update At | Timestamp of last vehicle info | timestamp |
| Last Status Update At | Timestamp of last status data | timestamp |
| Last Location Update At | Timestamp of last GPS fix | timestamp |
| Charging Rate | Learned EV charging rate (diagnostic) | %/h |

### Binary Sensors

| Entity | Description | Device Class |
|--------|-------------|--------------|
| Ignition | Engine / ignition state | power |
| EV Running | EV motor running | power |
| Door Driver | Driver door lock state | lock |
| Door Passenger | Passenger door lock state | lock |
| Door Rear Left | Rear-left door lock state | lock |
| Door Rear Right | Rear-right door lock state | lock |
| Trunk | Trunk lock state | lock |
| Window Driver | Driver window open/closed | window |
| Window Passenger | Passenger window open/closed | window |
| EV Charger | Charger plugged in | plug |
| Charging | Actively charging | battery_charging |
| Tire Pressure Front Left Warning | Front-left tyre pressure alert | problem |
| Tire Pressure Front Right Warning | Front-right tyre pressure alert | problem |
| Tire Pressure Rear Left Warning | Rear-left tyre pressure alert | problem |
| Tire Pressure Rear Right Warning | Rear-right tyre pressure alert | problem |
| Low Fuel | Low fuel warning | problem |

### Device Tracker

A **device tracker** entity is created for each vehicle that reports a GPS location.  
It integrates with Home Assistant zones (e.g., "home", "work") automatically.

### Locks

> Requires **Add command entities** option to be enabled.

| Entity | Description |
|--------|-------------|
| Doors Lock | Lock / unlock all doors |

### Switches

> Requires **Add command entities** option to be enabled.

| Entity | Description |
|--------|-------------|
| Engine | Remote start / stop |
| Precondition | Preconditioning on / off |
| HVAC | Air conditioning on / off |
| Comfort | Comfort mode on / off |
| Doors Lock | Door lock toggle |
| Charging | Start charging (EV) |
| Lock Trunk | Trunk lock toggle |

### Buttons

> Command buttons require **Add command entities** option to be enabled.  
> "Reset Battery Learning" is always available on EV/PHEV vehicles.

| Button | Description |
|--------|-------------|
| Refresh Location | Request a new GPS fix |
| Deep Refresh | Force battery level update from vehicle |
| Charge Now | Initiate EV charging |
| Lights | Flash the lights |
| Lights & Horn | Flash lights + sound horn |
| Update Data | Pull fresh data from the UConnect cloud |
| Reset Battery Learning | Reset learned charging/drain rates |

### Select

> Requires **Add command entities** option to be enabled.

| Entity | Description |
|--------|-------------|
| Charging Level Pref | Set preferred EV charge target level (L1–L5) |

---

## Services

The following Home Assistant services are registered under the `uconnect` domain.  
All services accept an optional `device_id` (required when multiple vehicles are configured).

```yaml
service: uconnect.update
service: uconnect.engine_on
service: uconnect.engine_off
service: uconnect.comfort_on / comfort_off
service: uconnect.hvac_on / hvac_off
service: uconnect.precond_on / precond_off
service: uconnect.lights
service: uconnect.lights_horn
service: uconnect.doors_lock / doors_unlock
service: uconnect.trunk_lock / trunk_unlock
service: uconnect.liftgate_lock / liftgate_unlock
service: uconnect.charge_now
service: uconnect.deep_refresh
service: uconnect.refresh_location
```

### Example Automation — Lock Doors When Leaving Home

```yaml
automation:
  alias: "Lock car when leaving home"
  trigger:
    - platform: zone
      entity_id: person.me
      zone: zone.home
      event: leave
  action:
    - service: uconnect.doors_lock
      data:
        device_id: !input vehicle_device
```

---

## API Data Model

This integration communicates with the **Stellantis UConnect cloud API** (the same backend used by the official mobile app). The underlying Python library is [`py-uconnect`](https://github.com/hass-uconnect/py-uconnect).

The API follows the same data model as the [Stellantis / Groupe PSA B2C Web API](https://developer.groupe-psa.io/webapi/b2c/api-reference/references/), providing the following resource categories:

| Category | Fields |
|----------|--------|
| **Status** | ignition, EV running, doors, windows, tyre pressures, warnings |
| **Energy** | state of charge, charging status, charger type, time to full, fuel level, battery voltage |
| **Location** | latitude, longitude, last updated timestamp |
| **Maintenance** | distance to service, days to service, oil level |
| **Telemetry** | odometer, driving range (EV, gas, combined) |

> Not all fields are available on all vehicles. Data availability depends on vehicle hardware, the active UConnect subscription, and regional API capabilities.

---

## Advanced: Extrapolated Battery SOC

For EV and PHEV vehicles, a second **HV Battery Charge (Extrapolated)** sensor is created. Because the UConnect API only updates roughly every 5 minutes (configurable), the real battery level can drift significantly between polls — especially during active charging or highway driving.

The extrapolated sensor:

1. **Records** the actual SOC and timestamp at each API update.
2. **Calculates** how much SOC should have changed based on elapsed time and a learned rate.
3. **Learns** the actual charging rate and drain rate using an exponential moving average — improving accuracy over time.
4. **Persists** the learned rates across Home Assistant restarts using `RestoreEntity`.
5. **Triggers a Deep Refresh** automatically after the vehicle has been idle for 1 hour (to resync).

To reset the learned parameters (e.g., after a battery replacement or when accuracy degrades), press the **Reset Battery Learning** button.

A companion **Charging Rate** diagnostic sensor (disabled by default) shows the current learned charging rate in `%/h`.

---

## Options

After initial setup, click **Configure** on the integration card to adjust:

| Option | Default | Description |
|--------|---------|-------------|
| Poll interval | 5 min | How often to fetch data from UConnect (1–999 min) |
| Security PIN | _(from setup)_ | Override the PIN used for remote commands |
| Add command entities | Off | Adds Lock, Switch, Button, Select entities for remote control |

---

## Troubleshooting

### "Authentication failed" during setup
- Verify your UConnect email and password are correct.
- Ensure your vehicle uses **UConnect** (T-Mobile), not the older SiriusXM Guardian system.
- Check the Home Assistant logs at **Settings → System → Logs** for details.

### No entities appear after setup
- Check the logs for errors during the first data fetch.
- Ensure your vehicle is powered on or has recently been active (some API endpoints require the vehicle to "wake up").
- Try increasing the poll interval to reduce rate-limiting.

### Remote commands fail
- Confirm the correct **Security PIN** is entered in the integration options.
- Not all commands are supported by all vehicles — only supported commands appear as entities.
- Check the vehicle's UConnect subscription includes remote commands.

### TLS / SSL errors
- Enable **Disable TLS certificate verification** in the integration settings as a workaround (not recommended for production use).

### Extrapolated SOC is inaccurate
- Press **Reset Battery Learning** to clear old learned rates.
- After a few charge cycles, accuracy improves automatically.

---

## Contributing

Contributions, bug reports, and feature requests are welcome!

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-feature`.
3. Commit your changes: `git commit -m "Add my feature"`.
4. Push: `git push origin feature/my-feature`.
5. Open a Pull Request.

Please open an [issue](https://github.com/ncecowboy/ha-uconnect/issues) before starting significant work.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

*This integration is not affiliated with or endorsed by Stellantis, UConnect, or T-Mobile.*

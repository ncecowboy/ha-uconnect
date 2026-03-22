# ha-uconnect — Home Assistant UConnect Integration (T-Mobile)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/ncecowboy/ha-uconnect.svg)](https://github.com/ncecowboy/ha-uconnect/releases)
[![License](https://img.shields.io/github/license/ncecowboy/ha-uconnect.svg)](LICENSE)

A [Home Assistant](https://www.home-assistant.io/) custom integration for **Stellantis vehicles** (Jeep, RAM, Dodge, Chrysler, Fiat, Alfa Romeo, Maserati) that communicate through the **UConnect cloud API**. It is compatible with **both** factory-installed 4G telematics modules **and** the [T-Mobile 4G OBD Adapter](#t-mobile-4g-obd-adapter-compatibility) — the aftermarket OBD-II dongle that re-enables UConnect connected services for vehicles originally equipped with 3G modems.

> **Note:** This integration requires an active UConnect account. It works with any hardware that routes through the UConnect cloud — including the T-Mobile 4G OBD Adapter.  
> It does **not** support the older SiriusXM Guardian (Mopar 3G) system.

---

## Table of Contents

1. [Features](#features)
2. [T-Mobile 4G OBD Adapter Compatibility](#t-mobile-4g-obd-adapter-compatibility)
3. [Supported Brands & Regions](#supported-brands--regions)
4. [Requirements](#requirements)
5. [Installation via HACS](#installation-via-hacs)
6. [Manual Installation](#manual-installation)
7. [Configuration](#configuration)
8. [Entities](#entities)
   - [Sensors](#sensors)
   - [Binary Sensors](#binary-sensors)
   - [Device Tracker](#device-tracker)
   - [Locks](#locks)
   - [Switches](#switches)
   - [Buttons](#buttons)
   - [Select](#select)
9. [Services](#services)
10. [API Data Model](#api-data-model)
11. [Advanced: Extrapolated Battery SOC](#advanced-extrapolated-battery-soc)
12. [Options](#options)
13. [Troubleshooting](#troubleshooting)
14. [Contributing](#contributing)
15. [License](#license)

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

## T-Mobile 4G OBD Adapter Compatibility

### ✅ Yes — This Integration Works with the T-Mobile 4G OBD Adapter

The T-Mobile 4G OBD Adapter is an aftermarket OBD-II dongle designed for Stellantis vehicles that originally shipped with 3G UConnect modems. When the 3G network was sunset, the OBD adapter allowed these vehicles to continue using connected services via T-Mobile's 4G LTE network.

**This integration is fully compatible with the OBD adapter.** Here's why:

- The OBD adapter connects to T-Mobile's 4G LTE network and forwards all vehicle data and commands through the **same Stellantis UConnect cloud API** used by factory-installed modems and the official Uconnect mobile app.
- This integration uses the [`py-uconnect`](https://github.com/hass-uconnect/py-uconnect) library to communicate with that same UConnect cloud — so whether your vehicle's cellular connectivity comes from a factory module or the T-Mobile OBD adapter, the integration works identically.

```
Vehicle CAN-Bus
    │
    └─► T-Mobile 4G OBD Adapter (OBD-II port)
              │ 4G LTE
              ▼
        T-Mobile Network
              │
              ▼
      UConnect Cloud API  ◄─── This integration (py-uconnect)
              │
              ▼
        Uconnect App (official)
```

### Supported Vehicle Models and Years

The T-Mobile 4G OBD Adapter targets Stellantis vehicles originally equipped with UConnect Access (3G). The following models are commonly supported:

| Brand | Model | Years |
|-------|-------|-------|
| **Jeep** | Grand Cherokee (WK2) | 2014–2021 |
| **Jeep** | Cherokee (KL) | 2015–2023 |
| **Jeep** | Wrangler (JK) | 2015–2018 |
| **Jeep** | Wrangler (JL / JLU) | 2018–2023 |
| **Jeep** | Compass (MP) | 2017–2023 |
| **Jeep** | Renegade (BU) | 2015–2023 |
| **Jeep** | Gladiator (JT) | 2020–2023 |
| **Ram** | 1500 Classic (DS) | 2013–2022 |
| **Ram** | 1500 (DT) | 2019–2023 |
| **Ram** | 2500 / 3500 | 2013–2023 |
| **Dodge** | Charger | 2015–2023 |
| **Dodge** | Challenger | 2015–2023 |
| **Dodge** | Durango | 2015–2023 |
| **Chrysler** | 300 | 2015–2023 |
| **Chrysler** | Pacifica / Pacifica Hybrid | 2017–2023 |
| **Chrysler** | Voyager | 2020–2023 |

> **Note:** Exact eligibility depends on your vehicle's specific Uconnect hardware version and trim level. Vehicles must have UConnect Access (or equivalent) and an active UConnect subscription. Use your VIN at [driveuconnect.com](https://www.driveuconnect.com/) to confirm eligibility.

### Feature Availability with the OBD Adapter

All features this integration provides are supported through the OBD adapter with one exception:

| Feature | OBD Adapter Support |
|---------|-------------------|
| Vehicle telemetry (odometer, range, tire pressure, fuel, etc.) | ✅ Full support |
| Door / window / ignition status | ✅ Full support |
| GPS location tracking | ✅ Full support |
| Remote lock / unlock | ✅ Full support (PIN required) |
| Remote engine start / stop | ✅ Full support (PIN required, if vehicle equipped) |
| HVAC / preconditioning | ✅ Full support (PIN required, if vehicle equipped) |
| Lights / horn | ✅ Full support |
| EV / PHEV charging controls | ✅ Full support (if vehicle equipped) |
| In-dash SOS / 911 emergency call | ❌ Not supported (requires factory head-unit modem) |
| In-dash navigation "Send & Go" | ❌ Not supported (requires factory head-unit modem) |

### OBD Adapter Setup (Outside This Integration)

Before using this integration, your OBD adapter must already be activated and working with the official Uconnect app:

1. Plug the T-Mobile 4G OBD Adapter into the OBD-II port (under the dashboard, driver's side).
2. Turn the ignition to **Run/On** (engine does not need to start).
3. Wait up to **15 minutes** for the adapter LED to turn solid green — this confirms 4G activation.
4. Confirm the adapter is working by opening the official **Uconnect app** and verifying vehicle status appears.
5. Once working in the Uconnect app, configure this Home Assistant integration using the same account credentials.

---

## Supported Brands & Regions

The brands and regions below correspond to the UConnect cloud API endpoints used by the `py-uconnect` library. Select the entry that matches your vehicle's brand and the country where it was sold.

| # | Brand | Region | T-Mobile OBD Adapter |
|---|-------|--------|----------------------|
| 1 | Fiat | EU | — |
| 2 | Fiat | US | — |
| 3 | RAM | US | ✅ Primary target |
| 4 | Dodge | US | ✅ Primary target |
| 5 | Jeep | EU | — |
| 6 | Jeep | US | ✅ Primary target |
| 7 | Maserati | Asia | — |
| 8 | Maserati | EU | — |
| 9 | Maserati | US / Canada | — |
| 10 | Chrysler | Canada | — |
| 11 | Chrysler | US | ✅ Primary target |
| 12 | Alfa Romeo | Asia | — |
| 13 | Alfa Romeo | EU | — |
| 14 | Alfa Romeo | US / Canada | — |
| 15 | Fiat | Asia | — |
| 16 | Fiat | Canada | — |
| 17 | Jeep | Asia | — |

> **✅ Primary target** — these US brands are the ones the T-Mobile 4G OBD Adapter was designed for.  
> All other brands connect to the same UConnect cloud architecture and are fully supported by the integration, but are not typically paired with the T-Mobile OBD hardware.

---

## Requirements

- Home Assistant **2023.1** or newer
- A Stellantis vehicle with an active **UConnect** subscription, connected through one of:
  - A **factory-installed 4G telematics module** (newer models), or
  - The **T-Mobile 4G OBD Adapter** (older models with original 3G UConnect)
- Your UConnect account **email**, **password**, and optionally a **security PIN**
- The OBD adapter (if used) must already be activated and working with the official Uconnect app before setting up this integration
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

### T-Mobile 4G OBD Adapter — Specific Issues

#### Adapter LED is not solid green
- The adapter needs up to 15 minutes after first plug-in to activate on the T-Mobile network.
- Ensure the vehicle ignition is in the **Run/On** position during activation.
- If the LED never turns solid green, contact T-Mobile support — the SIM activation may need to be reset.

#### Official Uconnect app works but this integration cannot connect
- The integration uses the same credentials as the Uconnect app. If the app works, authentication should succeed.
- Try logging out of the Uconnect app and back in to refresh your session, then retry the integration setup.
- Verify you selected the correct **Brand + Region** (e.g., *Jeep US*, *RAM US*, *Dodge US*, or *Chrysler US* for OBD adapter users in the United States).

#### Odometer shows incorrect values or "malfunction" alerts appear
- This is a known issue with some OBD adapter firmware versions on certain Dodge and Ram models (particularly 2014–2016). The integration faithfully reports whatever the UConnect cloud API provides.
- Check the T-Mobile adapter firmware version via the Uconnect app; an update may resolve the discrepancy.
- If values are consistently wrong, compare against the vehicle's instrument cluster and report the discrepancy to T-Mobile/UConnect support.

#### Vehicle data stops updating after a long idle period
- The OBD adapter may enter a sleep/low-power state when the vehicle has been parked and off for an extended time.
- Starting the vehicle or turning the ignition to **Run/On** will wake the adapter and trigger a data sync.
- Use the **Update Data** button entity (if enabled) or the `uconnect.update` service to manually request a refresh after the vehicle wakes.

#### Remote commands (lock, start, etc.) time out with OBD adapter
- The OBD adapter must have cellular connectivity for remote commands to reach the vehicle.
- Commands sent while the vehicle is in an area with poor T-Mobile coverage may fail or be delayed.
- The adapter processes commands when the vehicle is parked with ignition off; allow up to 60 seconds for command confirmation.
- Ensure the UConnect subscription plan includes remote services (not all plans include remote start/unlock).

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

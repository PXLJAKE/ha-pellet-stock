# Pellet Stock Manager for Home Assistant

[![CI](https://github.com/PXLJAKE/ha-pellet-stock/actions/workflows/ci.yml/badge.svg)](https://github.com/PXLJAKE/ha-pellet-stock/actions/workflows/ci.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)

Pellet Stock Manager keeps track of your wood pellet storage in Home Assistant. It shows how much is left, how long it will last, what heating costs per month and what a kWh costs. It works with any pellet boiler or stove, whatever the brand, because it reads sensors your heating already has in Home Assistant.

<img src="docs/images/card-light.png" alt="Dashboard card with silo, stock, range, key figures, 12-month chart and deliveries" width="360">

## Features

- **Any heating.** Consumption can come from a kg counter (daily or total), an energy counter in kWh, or burner runtime (an on/off entity or an hours counter).
- **Stock and range.** The range is the remaining stock divided by the average use of the last 14 full days. Each value has a plain-language **"Why?"** explanation.
- **Costs.**
  - The average price uses the moving average of your deliveries.
  - Cost per month and per year.
  - Price per kWh for the Energy dashboard.
- **Deliveries.** You can enter deliveries from the card or with an action, and correct or delete wrong entries.
- **History from day one.** Past daily consumption can be taken over from the long-term statistics Home Assistant already keeps for your sensor, so the charts and the range work right after setup.
- **Low stock warning.** A binary sensor and the event `pellet_stock_low_stock` let you build your own notifications.
- **Fill level or scale (optional).** A measured or calculated level is compared with the stock, and one button press takes it over.
- **Dashboard card** (included, no extra resource to add):
  - Silo graphic and key figures.
  - 12-month chart.
  - A popup with **months, weeks and days**: tap a month or week to see its days.
- **Light on your system.**
  - Event-driven, with no polling.
  - Data is written at most every 15 minutes, which is kind to SD cards. Deliveries are saved right away.
  - History is not stored in the recorder; the card loads it when it needs it.
- **German and English.**

| Analysis popup | On a phone |
|---|---|
| <img src="docs/images/popup-months.png" alt="Popup with monthly bar chart and table" width="480"> | <img src="docs/images/popup-week-phone.png" alt="Days of one week on a phone" width="220"> |

## Installation

### HACS

1. In HACS, open the menu (⋮), choose **Custom repositories**, and add `https://github.com/PXLJAKE/ha-pellet-stock` with the type **Integration**.
2. Search for **Pellet Stock Manager** and download it.
3. Restart Home Assistant.

### Manual

1. Copy `custom_components/pellet_stock` into the `custom_components` folder of your Home Assistant configuration.
2. Restart Home Assistant.

Home Assistant 2026.10 or newer is required.

## Setup

Go to **Settings → Devices & services → Add integration** and choose **Pellet Stock Manager**. The assistant has four steps, and every field explains what it does:

1. **Name and source.** Choose where the consumption comes from.
2. **Source details.**
   - The sensor.
   - The calorific value (default 4.8 kWh/kg for ENplus A1 pellets).
   - The largest plausible step (default 10 kg). Bigger jumps are ignored, for example after a restart.
   - For energy sensors, the boiler efficiency.
   - For runtime, kg per burner hour.
3. **Storage.**
   - Capacity.
   - Minimum stock in percent (default 10 %).
   - Optional fill level or scale sensor.
4. **Start values.**
   - The current stock, suggested from the fill level sensor if you have one.
   - The price per tonne.
   - Whether to take over the history from the Home Assistant statistics (on by default for sensors).

You can change everything later under **Configure**, and stock and history are kept. Each storage gets its own entry, so you can add as many as you need.

## Entities

| Entity | Description |
|---|---|
| Stock | Pellets left, in kg |
| Fill level | Stock as a percentage of the capacity |
| Range | Days the stock lasts. The `reason` attribute explains the calculation |
| Average daily consumption | Average over the last 14 full days |
| Consumption today | kg used today |
| Total consumption | kg used since setup. The `reason` attribute explains every automatic decision |
| Energy | kWh in the pellets used, for the Energy dashboard |
| Price per kWh | Average pellet price divided by the calorific value |
| Average price per tonne | Moving average of your deliveries |
| Cost this month / Cost this year | Cost of the pellets used |
| Last delivery | Date of the last delivery. The ten most recent are listed as attributes |
| Minimum stock reached | On when the stock is below the minimum |
| Difference to measured level | Only with a fill level sensor: calculated stock minus measured level |
| Take measured fill level | Only with a fill level sensor: sets the stock to the measured value |

## Actions

| Action | Fields |
|---|---|
| `pellet_stock.add_delivery` | `config_entry_id`, `kg`, `price` (total, optional), `date` (optional), `note` (optional) |
| `pellet_stock.correct_stock` | `config_entry_id`, `stock_kg` |
| `pellet_stock.delete_delivery` | `config_entry_id`, `delivery_id` (from the attributes of *Last delivery*) |
| `pellet_stock.import_history` | `config_entry_id`. Takes over past daily consumption from the statistics, once per storage |

Each action returns a response, for example the new stock.

## Low stock automation

The event `pellet_stock_low_stock` fires once when the stock drops below the minimum. It carries `entry_id`, `name`, `stock_kg`, `min_stock_kg` and `reason`.

```yaml
triggers:
  - trigger: event
    event_type: pellet_stock_low_stock
actions:
  - action: notify.notify
    data:
      title: "Order pellets"
      message: "{{ trigger.event.data.reason }}"
```

## Dashboard card

The card is loaded automatically. To add it:

1. Edit a dashboard and choose **Add card**.
2. Search for **Pellet Stock** and pick your storage.

Tap the card to open the analysis popup.

```yaml
type: custom:pellet-stock-card
device: <device id>          # chosen in the visual editor
title: Pellet silo           # optional
show_stats: true
show_chart: true             # last 12 months
show_history: true
show_add_button: true
history_count: 3
```

<img src="docs/images/card-dark-wide.png" alt="Card in the dark theme on a wide screen" width="720">

## Privacy and resources

- All data stays in Home Assistant. Nothing is sent to the internet.
- Diagnostics hide your delivery notes.
- The card is a single file of about 13 KB (gzipped) with no dependencies.

## Contributing

Issues and pull requests are welcome, see [CONTRIBUTING.md](CONTRIBUTING.md). Changes are listed in the [CHANGELOG](CHANGELOG.md).

## License

[Apache License 2.0](LICENSE)

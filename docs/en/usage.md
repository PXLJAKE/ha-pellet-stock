# Usage

## Entities

Each storage is a device with these entities:

| Entity | Description |
|---|---|
| Stock | Pellets left, in kg |
| Fill level | Stock as a percentage of the storage size |
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
| Take measured fill level | Only with a fill level sensor: a button that sets the stock to the measured value |

## The "Why?" explanations

Every automatic decision is explained in plain language, in the `reason` attribute and on the card.

**Range.** The range is the stock divided by the average use of the last 14 full days. In the first hours, today's use is extrapolated to a full day, and the explanation says so. Without about 6 hours of use there is no range yet.

**Consumption sensor.** The explanation of *Total consumption* says what happened to the last sensor value, for example:

- "Counted 0.42 kg (sensor rose to 12.30)."
- "Ignored a jump of 25.00 kg because it is above the limit of 10.0 kg per step (e.g. restart or measuring error)."
- "Counter was reset (e.g. new day), nothing counted."
- "Home Assistant restarted while the burner was running. The time Home Assistant was off is not counted."

## Deliveries

Enter a delivery on the card with **Add delivery**, or with the action `pellet_stock.add_delivery`. The stock goes up and the average price is updated as a moving average: the value of what was left plus the value of the delivery, divided by the new stock.

If you also enter deliveries on the boiler itself, nothing is counted twice. The integration only reads the consumption from the boiler.

## Actions

| Action | Fields |
|---|---|
| `pellet_stock.add_delivery` | `config_entry_id`, `kg`, `price` (what the whole delivery cost, optional), `date` (optional, today if empty), `note` (optional) |
| `pellet_stock.correct_stock` | `config_entry_id`, `stock_kg` (what is really in the storage now) |
| `pellet_stock.delete_delivery` | `config_entry_id`, `delivery_id` (from the attributes of *Last delivery*) |
| `pellet_stock.import_history` | `config_entry_id`, `replace` (optional). Takes over past daily consumption from the statistics, once per storage. With `replace`, an earlier import is removed and read again |

Each action returns a response, for example the new stock. You find them under **Developer tools → Actions**, where you pick the storage from a list.

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

You can also use the binary sensor *Minimum stock reached* as a trigger.

## Energy dashboard

The *Energy* sensor counts the kWh in the pellets used, and *Price per kWh* is the matching price. You can select the *Energy* sensor in the settings of the Energy dashboard.

!!! info "Open point"
    Which section of the Energy dashboard fits pellets best is not documented yet. Home Assistant has no pellet category.

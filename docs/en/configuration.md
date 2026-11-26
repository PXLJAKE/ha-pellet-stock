# Configuration

Everything is set in the Home Assistant interface. You can change all settings later under **Settings → Devices & services → Pellet Stock Manager → Configure**. Stock, deliveries and history are kept when you change settings.

## Step 1: name and source

| Field | What it does |
|---|---|
| Name | Shown as the device name, for example "Pellet silo". Two storages cannot have the same name. |
| Where does the consumption come from? | Pick what your heating already reports in Home Assistant. |

The three sources:

| Source | Use it when |
|---|---|
| A sensor counts pellets in kg | Your boiler reports used pellets in kg. A running total and a daily counter that resets at midnight both work. |
| A sensor counts energy in kWh | Your boiler or a heat meter counts energy. Pellets are the energy divided by the calorific value. |
| Burner runtime | You only know when the burner runs: an on/off entity, or a sensor with burner hours. Pellets are the runtime times kg per hour. |

## Step 2: source details

| Field | Default | What it does |
|---|---|---|
| Sensor | | The entity that is read. |
| Calorific value | 4.8 kWh/kg | Energy in one kg of pellets. 4.8 kWh/kg is typical for ENplus A1 pellets; your delivery note may say more. Used for the energy sensor and the price per kWh. |
| Largest plausible step | 10 kg | Bigger jumps between two sensor values are ignored, for example after a restart or a measuring error. |
| Boiler efficiency | 100 % | Only for energy sensors. Leave 100 % if the sensor counts the energy in the pellets, as most boilers do. If it measures the heat that is given off, enter the boiler efficiency, for example 90 %. |
| Pellets per burner hour | 2 kg/h | Only for burner runtime. How many kg the burner uses per hour at its usual output. It is in the manual (fuel consumption at nominal load), or you can work it out from a delivery. |

## Step 3: storage

| Field | Default | What it does |
|---|---|---|
| Storage size | 5000 kg | How many kg fit into the full storage. |
| Minimum stock | 10 % | Below this share of the storage size, the sensor "Minimum stock reached" turns on and the event `pellet_stock_low_stock` fires. |
| Fill level or scale sensor | none | Optional. A sensor that measures what is really in the storage (scale, ultrasound, radar; in kg or %). It is only compared with the calculated stock. You take it over with a button, never automatically. |

!!! note "A calculated level is not a measurement"
    Some boilers report a "storage level" that they calculate from the consumption themselves. Comparing it with the stock tells you nothing new, because both come from the same counter. The option is meant for real measurements.

## Step 4: start values

| Field | Default | What it does |
|---|---|---|
| Current stock | | Your best estimate of what is in the storage today. With a fill level sensor, its value is suggested. You can correct it later. |
| Price per tonne | 0 | What you paid for these pellets, including delivery. Used for cost and price per kWh. 0 means unknown. |
| Take over history from Home Assistant | on | Only offered when the source is a sensor. Reads the past daily consumption from the long-term statistics of the sensor, so the charts are filled from the first day. The stock is not changed. |

## How the history import works

Home Assistant keeps long-term statistics for sensors with a state class. The import reads them once and turns them into daily consumption:

- Sensors with a running total: the daily change is the consumption.
- Other sensors, such as daily counters that reset at midnight: the hourly values are followed like a counter. Every rise is consumption, and a drop is a reset.

Days with more than 500 kg are treated as faulty and skipped. Up to ten years are read. Daily values are kept for the last 400 days; older days only count in the monthly and yearly totals. The cost of imported days uses your average price, because older prices are not known.

The import runs once per storage. If you set up the storage before this feature existed, run the action `pellet_stock.import_history` once, see [Usage](usage.md#actions).

An on/off burner entity has no long-term statistics, so there is nothing to take over for it.

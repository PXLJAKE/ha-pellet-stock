# Troubleshooting

## The card is missing

The card is loaded when Home Assistant starts. After installing or updating:

1. Restart Home Assistant.
2. Reload the browser page without the cache (on a PC: Ctrl+Shift+R).
3. In the Companion app: **Settings → Companion app → Troubleshooting → Reset frontend cache**.

If a dashboard shows "Custom element doesn't exist: pellet-stock-card", the browser still has an old page. The same steps help.

## The range is unknown

A range needs about 6 hours of use. The `reason` attribute of the *Range* sensor says what is missing, for example "Not enough data yet" or "Nothing was used in the last 14 days".

## The stock does not go down

Look at the `reason` attribute of *Total consumption*. It explains what happened to the last sensor value:

- **"Ignored a jump …"**: the step was bigger than the *largest plausible step*. If your boiler reports in big steps, raise the value under **Configure**.
- **"Sensor unavailable"**: the source sensor has no value at the moment.
- **"Sensor value unchanged"**: the boiler has not reported new consumption.

## The stock is wrong

Set it with the action `pellet_stock.correct_stock`, or with the button *Take measured fill level* if you have a fill level sensor. History and deliveries are kept.

## The history import brings nothing

- **"There are no long-term statistics for the sensor"**: Home Assistant only keeps statistics for sensors with a state class. Check under **Developer tools → Statistics** whether your sensor is listed.
- **"The history was already taken over"**: the import runs once per storage, so nothing is counted twice.
- The action `pellet_stock.import_history` is missing: you have a version before 0.2.0. Update and restart.

## A delivery is wrong

Delete it with `pellet_stock.delete_delivery`. The `delivery_id` is in the attributes of the *Last delivery* sensor. Then enter it again.

## Report a problem

Download the diagnostics under **Settings → Devices & services → Pellet Stock Manager → ⋮ → Download diagnostics** and open an [issue on GitHub](https://github.com/PXLJAKE/ha-pellet-stock/issues). Delivery notes are hidden in the diagnostics.

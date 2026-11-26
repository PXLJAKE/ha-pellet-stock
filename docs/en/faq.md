# FAQ

## Does it work with my boiler?

Yes, if your heating has one of these in Home Assistant: a kg counter, a kWh counter, an on/off entity for the burner, or a burner hours sensor. The integration does not talk to the boiler itself, so the brand does not matter.

## My sensor resets to zero every day. Is that a problem?

No. A daily counter that resets at midnight is recognised, also when Home Assistant misses the zero at midnight.

## My boiler already shows a stock. Should I connect that sensor?

Enter its value once as the current stock. A stock that the boiler calculates itself comes from the same consumption, so using it as a fill level sensor adds nothing. The fill level option is for real measurements such as a scale, ultrasound or radar.

## I also enter deliveries on the boiler. Does that clash?

No. The integration only reads the consumption. A delivery you enter on the boiler does not change that value.

## Can I get my old consumption into the charts?

Yes, if the source is a sensor with long-term statistics. See [How the history import works](configuration.md#how-the-history-import-works).

## How is the range calculated?

Stock divided by the average use of the last 14 full days. The `reason` attribute of the *Range* sensor shows the numbers.

## How is the price calculated?

As a moving average. A delivery mixes with what is left in the storage: the value of the rest plus the value of the delivery, divided by the new stock.

## Can I have more than one storage?

Yes. Each storage is its own entry with its own device, entities and card.

## Does it need the internet?

No. All data stays in Home Assistant.

## Which languages are there?

English and German. The card follows the language of Home Assistant.

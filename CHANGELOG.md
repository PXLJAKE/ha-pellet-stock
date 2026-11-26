# Changelog

All notable changes are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Setup assistant in four steps: name and consumption source (kg counter,
  energy counter with calorific value and efficiency, or burner runtime with
  kg per hour), source details, storage (capacity, minimum stock, optional
  fill level or scale sensor) and start values. All settings can be changed
  later; stock and history are kept.
- Event-driven calculation (no polling): plausibility filter for sensor jumps,
  daily counter resets and small backward steps; data saved at most every
  15 minutes.
- Sensors: stock, fill level, range, average daily consumption, consumption
  today, total consumption, energy (Energy dashboard), price per kWh, average
  price per tonne, cost this month and this year, difference to measured level.
- Binary sensor "Minimum stock reached" and event `pellet_stock_low_stock`.
- Button to take the measured fill level as stock.
- Actions `add_delivery` (amount, total price, date, note), `correct_stock`
  and `delete_delivery`, plus a "Last delivery" sensor with the ten most
  recent deliveries as attributes. Deliveries are saved immediately.
- Dashboard card `custom:pellet-stock-card` (served by the integration, no
  manual resource): silo graphic with fill level, stock, range with "Why?",
  key figures, delivery history and an "Add delivery" form. Visual editor,
  light/dark theme, phone to desktop. About 5 KB gzipped, no dependencies.
- Analysis popup: tap the card to open overview, months, weeks and
  deliveries. Bar charts for consumption or cost per month (tap a month for
  its days) and for the last 26 weeks (tap a week for its days), with
  tooltips, tables and yearly totals. Optional 12-month chart in the card.
  Data comes on demand over the WebSocket command `pellet_stock/data`, so
  no history is stored in the recorder. The card is about 13 KB gzipped.
- Take over past consumption from the Home Assistant long-term statistics of
  the source sensor: an option in the setup assistant (on by default for
  sensors) and the action `import_history`. Running totals use the daily
  change, daily resetting counters the daily maximum. The stock is not
  changed, costs of these days use the average price, and the range can use
  the imported days right away. Runs only once per storage.
- Icon set for all entities and actions, brand icon (light and dark) shipped
  with the integration, integration categories in the manifest.
- README with installation, setup, entities, actions, automation example and
  screenshots.

### Fixed

- Burner runtime source: a run that was still open when Home Assistant
  restarted no longer counts the time Home Assistant was off. The "Why?"
  text says so.
- Actions reject amounts, stock and prices above 100,000.
- Daily counters: when Home Assistant misses the zero at midnight and the
  first value of the new day is already small (e.g. 4.0 yesterday, 0.5
  today), this is now recognised as a reset instead of a measuring glitch, so
  no consumption is lost.
- Plain-language "reason" attributes (German/English) for range, minimum stock
  and every decision about the consumption sensor.
- Project scaffold: integration skeleton with a setup assistant (name only),
  diagnostics with redacted free text, German and English texts, tests, CI
  (ruff, pytest, hassfest, HACS validation) and Dependabot.

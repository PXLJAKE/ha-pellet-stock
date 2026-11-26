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
- Plain-language "reason" attributes (German/English) for range, minimum stock
  and every decision about the consumption sensor.
- Project scaffold: integration skeleton with a setup assistant (name only),
  diagnostics with redacted free text, German and English texts, tests, CI
  (ruff, pytest, hassfest, HACS validation) and Dependabot.

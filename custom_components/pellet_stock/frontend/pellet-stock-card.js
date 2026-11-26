/*
 * Pellet Stock Card for Home Assistant.
 *
 *   type: custom:pellet-stock-card
 *   device: <device_id>        # pellet storage
 *   title: "Pelletsilo"        # optional
 *
 * Tap the card to open a popup with overview, months (tap a month for its
 * days), weeks (tap a week for its days) and deliveries.
 * Plain web component, no framework and no build step, so it loads fast.
 * Analysis data comes on demand from the WebSocket API `pellet_stock/data`.
 */
const VERSION = "0.2.0";
const DOMAIN = "pellet_stock";
const REFRESH_MS = 5 * 60 * 1000;

// Validated series colour (CVD-safe), separate steps for light and dark.
const PALETTE = { light: "#2a78d6", dark: "#3987e5" };

const T = {
  en: {
    stock: "Stock", range: "Range", days: "days", perDay: "per day", today: "Today",
    pricePerKwh: "Price per kWh", costMonth: "This month", costYear: "This year",
    low: "Minimum stock reached", deliveries: "Deliveries", noDeliveries: "No deliveries yet",
    addDelivery: "Add delivery", amount: "Amount (kg)", price: "Total price",
    date: "Date", save: "Save", cancel: "Cancel", why: "Why?",
    noDevice: "Choose a pellet storage in the card settings.",
    notFound: "Pellet storage not found.", saved: "Delivery saved",
    rangeUnknown: "not yet known", close: "Close", details: "Show details",
    tabOverview: "Overview", tabMonths: "Months", tabWeeks: "Weeks", tabDeliveries: "Deliveries",
    month: "Month", week: "Week", day: "Day", year: "Year", years: "Years",
    consumption: "Consumption", cost: "Cost", avgDay: "Avg per day", energy: "Energy",
    back: "Back to", daysOf: "Days of", loading: "Loading …", noData: "No consumption recorded yet.",
    last12: "Last 12 months", kw: "CW", total: "Total consumption", capacity: "Capacity",
    minStock: "Minimum stock", since: "Counting since", historyFrom: "History from HA statistics since", pricePerTonne: "Ø price per tonne",
    monthKg: "Used this month", costMonthLong: "Cost this month", costYearLong: "Cost this year", qty: "Amount", tapHint: "Tap a bar for details.", note: "Note",
    weeksOf: "Days of week",
  },
  de: {
    stock: "Bestand", range: "Reichweite", days: "Tage", perDay: "pro Tag", today: "Heute",
    pricePerKwh: "Preis pro kWh", costMonth: "Diesen Monat", costYear: "Dieses Jahr",
    low: "Mindestbestand erreicht", deliveries: "Lieferungen", noDeliveries: "Noch keine Lieferungen",
    addDelivery: "Lieferung eintragen", amount: "Menge (kg)", price: "Gesamtpreis",
    date: "Datum", save: "Speichern", cancel: "Abbrechen", why: "Warum?",
    noDevice: "Wähle in den Karteneinstellungen ein Pelletlager.",
    notFound: "Pelletlager nicht gefunden.", saved: "Lieferung gespeichert",
    rangeUnknown: "noch unbekannt", close: "Schließen", details: "Details anzeigen",
    tabOverview: "Übersicht", tabMonths: "Monate", tabWeeks: "Wochen", tabDeliveries: "Lieferungen",
    month: "Monat", week: "Woche", day: "Tag", year: "Jahr", years: "Jahre",
    consumption: "Verbrauch", cost: "Kosten", avgDay: "Ø pro Tag", energy: "Energie",
    back: "Zurück zu", daysOf: "Tage im", loading: "Lädt …", noData: "Noch kein Verbrauch erfasst.",
    last12: "Letzte 12 Monate", kw: "KW", total: "Gesamtverbrauch", capacity: "Lagergröße",
    minStock: "Mindestbestand", since: "Zählt seit", historyFrom: "Verlauf aus HA-Statistik ab", pricePerTonne: "Ø Preis pro Tonne",
    monthKg: "Verbrauch diesen Monat", costMonthLong: "Kosten diesen Monat", costYearLong: "Kosten dieses Jahr", qty: "Menge", tapHint: "Tippe auf einen Balken für Details.", note: "Notiz",
    weeksOf: "Tage der KW",
  },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

/** Today as YYYY-MM-DD in the browser's time zone (not UTC). */
const localIso = (d = new Date()) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

const langOf = (hass) => ((hass?.locale?.language || hass?.language || "en").startsWith("de") ? "de" : "en");
const colorOf = (hass) => (hass?.themes?.darkMode ? PALETTE.dark : PALETTE.light);

function makeFmt(hass, currency) {
  const locale = hass?.locale?.language || "en";
  const cur = currency || hass?.config?.currency || "EUR";
  const nf = {};
  const num = (v, dec = 0) => {
    if (v == null || v === "" || !Number.isFinite(Number(v))) return "–";
    nf[dec] ||= new Intl.NumberFormat(locale, { minimumFractionDigits: dec, maximumFractionDigits: dec });
    return nf[dec].format(Number(v));
  };
  let mf;
  const money = (v, dec = 2) => {
    if (v == null || !Number.isFinite(Number(v))) return "–";
    try {
      mf ||= {};
      mf[dec] ||= new Intl.NumberFormat(locale, { style: "currency", currency: cur, minimumFractionDigits: dec, maximumFractionDigits: dec });
      return mf[dec].format(Number(v));
    } catch (e) { return `${num(v, dec)} ${cur}`; }
  };
  const parse = (iso) => { const [y, m, d] = iso.split("-").map(Number); return new Date(y, (m || 1) - 1, d || 1); };
  const date = (iso, opts = { dateStyle: "medium" }) => (iso ? parse(iso).toLocaleDateString(locale, opts) : "–");
  const month = (key, style = "short") => parse(key).toLocaleDateString(locale, { month: style });
  const monthYear = (key) => parse(key).toLocaleDateString(locale, { month: "long", year: "numeric" });
  const perKwh = (v) => (v == null ? "–" : cur === "EUR" ? `${num(v * 100, 2)} ct/kWh` : `${money(v, 4)}/kWh`);
  let symbol = cur;
  try {
    symbol = new Intl.NumberFormat(locale, { style: "currency", currency: cur }).formatToParts(0).find((p) => p.type === "currency")?.value || cur;
  } catch (e) { /* keep code */ }
  return { num, money, date, month, monthYear, perKwh, currency: cur, symbol, locale };
}

/** Round axis scale: at most 5 ticks with steps 1, 2, 2.5, 5 × 10^n. */
function niceScale(v) {
  const max = v > 0 ? v : 1;
  const raw = max / 4;
  const pow = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * pow).find((s) => s >= raw);
  return { top: Math.ceil(max / step - 1e-9) * step, step };
}

function topRoundedBar(x, y, w, h, r = 4) {
  if (h <= 0) return "";
  r = Math.min(r, h, w / 2);
  return `M${x},${y + h}L${x},${y + r}Q${x},${y} ${x + r},${y}L${x + w - r},${y}Q${x + w},${y} ${x + w},${y + r}L${x + w},${y + h}Z`;
}

/**
 * Bar chart. rows: [{label, value, partial}]; partial bars (running period)
 * are drawn lighter. Returns HTML with an SVG and a tooltip box.
 */
function barChart(rows, { width, height, color, fmt, unitFmt, clickable }) {
  const left = 44, right = 6, top = 8, bottom = 22;
  const plotW = Math.max(width - left - right, 40);
  const plotH = height - top - bottom;
  const scale = niceScale(Math.max(...rows.map((r) => r.value || 0), 0));
  const y0 = top + plotH;
  const band = plotW / Math.max(rows.length, 1);
  const barW = Math.max(Math.min(26, band * 0.64), 2);
  const labelEvery = Math.max(1, Math.ceil(rows.length / Math.max(Math.floor(plotW / 30), 1)));
  let svg = "";
  for (let v = 0; v <= scale.top + 1e-9; v += scale.step) {
    const y = y0 - (v / scale.top) * plotH;
    svg += `<line x1="${left}" x2="${left + plotW}" y1="${y}" y2="${y}" class="${v === 0 ? "axis" : "grid"}"/>`;
    svg += `<text x="${left - 6}" y="${y + 3.5}" text-anchor="end" class="tick">${esc(unitFmt(v, scale.step))}</text>`;
  }
  rows.forEach((r, i) => {
    const x = left + i * band + (band - barW) / 2;
    const h = ((r.value || 0) / scale.top) * plotH;
    if (h > 0) svg += `<path d="${topRoundedBar(x, y0 - h, barW, h)}" fill="${color}" opacity="${r.partial ? 0.55 : 1}"/>`;
    if (i % labelEvery === 0) svg += `<text x="${x + barW / 2}" y="${y0 + 14}" text-anchor="middle" class="tick">${esc(r.label)}</text>`;
    svg += `<rect class="hit${clickable && r.clickable !== false ? " clickable" : ""}" data-i="${i}" x="${left + i * band}" y="${top}" width="${band}" height="${plotH}" fill="transparent"/>`;
  });
  return `<div class="chart"><svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img">${svg}</svg><div class="tooltip" hidden></div></div>`;
}

function bindChart(root, rows, { tip, onClick }) {
  root.querySelectorAll(".chart").forEach((chart) => {
    const box = chart.querySelector(".tooltip");
    chart.querySelectorAll(".hit").forEach((hit) => {
      const r = rows[Number(hit.dataset.i)];
      const show = () => {
        box.innerHTML = tip(r);
        box.hidden = false;
        const cb = chart.getBoundingClientRect(), hb = hit.getBoundingClientRect();
        const x = hb.left - cb.left + hb.width / 2, w = box.offsetWidth;
        box.style.left = `${x + 12 + w <= cb.width ? x + 12 : Math.max(x - 12 - w, 0)}px`;
        box.style.top = "0px";
      };
      hit.addEventListener("pointerenter", show);
      hit.addEventListener("pointerleave", () => { box.hidden = true; });
      hit.addEventListener("click", (e) => {
        e.stopPropagation();
        if (onClick && r.clickable !== false) onClick(r); else show();
      });
    });
  });
}

function fetchData(hass, device, month) {
  const msg = { type: `${DOMAIN}/data`, device_id: device };
  if (month) msg.month = month;
  return hass.callWS(msg);
}

// ─── Shared styles ───────────────────────────────────────────────────────────

const BASE_CSS = `
  :host { display: block; }
  .chart { position: relative; width: 100%; overflow: hidden; }
  .chart svg { display: block; max-width: 100%; height: auto; overflow: visible; }
  .chart .tick { font-size: 10px; fill: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
  .chart .grid { stroke: var(--divider-color); stroke-width: 1; opacity: .6; }
  .chart .axis { stroke: var(--divider-color); stroke-width: 1; }
  .chart .hit.clickable { cursor: pointer; }
  .chart .hit:hover { fill: var(--primary-text-color); fill-opacity: .05; }
  .tooltip { position: absolute; pointer-events: none; z-index: 2; min-width: 140px;
    background: var(--card-background-color, #fff); color: var(--primary-text-color);
    border: 1px solid var(--divider-color); border-radius: 8px; padding: 6px 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,.15); font-size: 12px; }
  .tt-title { font-weight: 600; margin-bottom: 4px; }
  .tt-row { display: flex; gap: 6px; }
  .tt-row b { margin-left: auto; padding-left: 12px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .muted { color: var(--secondary-text-color); }
  .section-title { font-size: .75em; font-weight: 600; letter-spacing: .04em; text-transform: uppercase;
    color: var(--secondary-text-color); margin: 16px 0 4px; }
  button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border: none;
    border-radius: 18px; padding: 8px 16px; font: inherit; cursor: pointer; }
  button.flat, button.link { background: none; border: none; color: var(--primary-color); font: inherit; cursor: pointer; padding: 8px 12px; }
  button.link { padding: 0; font-size: .9em; }
  form { display: grid; gap: 8px; margin-top: 12px; min-width: 0; }
  label { display: grid; gap: 4px; font-size: .85em; color: var(--secondary-text-color); }
  input { box-sizing: border-box; width: 100%; min-width: 0; font: inherit; padding: 8px 10px; border-radius: 8px;
    border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); }
  .row { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; }
  .actions { margin-top: 12px; display: flex; justify-content: flex-end; align-items: center; gap: 8px; }
  .err { color: var(--error-color); font-size: .85em; }
  .ok { color: var(--success-color, var(--primary-color)); font-size: .85em; }
`;

/** Delivery form shared by card and popup. */
function deliveryForm(t, fmt, err) {
  const now = new Date();
  const iso = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  return `<form>
      <div class="row">
        <label>${t.amount}<input name="kg" type="number" min="0.1" step="0.1" required inputmode="decimal"></label>
        <label>${t.price} (${esc(fmt.currency)})<input name="price" type="number" min="0" step="0.01" inputmode="decimal"></label>
      </div>
      <label>${t.date}<input name="date" type="date" value="${iso}"></label>
      ${err ? `<div class="err">${esc(err)}</div>` : ""}
      <div class="actions"><button type="button" class="flat" data-cancel>${t.cancel}</button>
        <button type="submit" class="primary">${t.save}</button></div>
    </form>`;
}

async function submitDelivery(hass, entryId, form) {
  const data = new FormData(form);
  const service = { config_entry_id: entryId, kg: Number(data.get("kg")) };
  if (data.get("price")) service.price = Number(data.get("price"));
  if (data.get("date")) service.date = data.get("date");
  await hass.callService(DOMAIN, "add_delivery", service);
}

// ─── Card ────────────────────────────────────────────────────────────────────

const CARD_CSS = `
  ha-card { padding: 16px; container-type: inline-size; cursor: pointer; }
  ha-card:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  .head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 12px; }
  .title { font-size: 1.15em; font-weight: 500; color: var(--primary-text-color); }
  .badge { font-size: .8em; padding: 2px 10px; border-radius: 12px; color: var(--error-color);
    background: color-mix(in srgb, var(--error-color) 14%, transparent); white-space: nowrap; }
  .main { display: grid; grid-template-columns: 88px 1fr; gap: 16px; align-items: center; }
  @container (max-width: 260px) { .main { grid-template-columns: 1fr; justify-items: center; } }
  .silo { width: 88px; height: auto; display: block; }
  .silo-body { fill: none; stroke: var(--divider-color); stroke-width: 2; }
  .big { font-size: 2em; line-height: 1.1; color: var(--primary-text-color); }
  .unit { font-size: .5em; color: var(--secondary-text-color); margin-left: 4px; }
  .sub { color: var(--secondary-text-color); font-size: .9em; }
  .range { margin-top: 8px; font-size: 1.05em; color: var(--primary-text-color); }
  .why { background: none; border: none; padding: 0; margin-left: 6px; color: var(--primary-color);
    font: inherit; font-size: .85em; cursor: pointer; }
  .reason { margin-top: 6px; font-size: .85em; color: var(--secondary-text-color); line-height: 1.4; }
  .stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 16px; }
  @container (min-width: 560px) { .stats { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
  .stat { padding: 8px 10px; border-radius: 10px; background: var(--secondary-background-color); }
  .stat .v { font-size: 1.05em; color: var(--primary-text-color); white-space: nowrap; }
  .stat .l { font-size: .78em; color: var(--secondary-text-color); }
  ul { list-style: none; margin: 0; padding: 0; }
  li { display: grid; grid-template-columns: 1fr auto minmax(5.5em, auto); gap: 16px; padding: 6px 0; text-align: right;
    border-bottom: 1px solid var(--divider-color); font-size: .92em; color: var(--primary-text-color); }
  li:last-child { border-bottom: none; }
  li .d { color: var(--secondary-text-color); text-align: left; }
`;

class PelletStockCard extends HTMLElement {
  static getConfigForm() {
    return {
      schema: [
        { name: "device", required: true, selector: { device: { integration: DOMAIN } } },
        { name: "title", selector: { text: {} } },
        {
          type: "grid", name: "", schema: [
            { name: "show_stats", default: true, selector: { boolean: {} } },
            { name: "show_chart", default: true, selector: { boolean: {} } },
            { name: "show_history", default: true, selector: { boolean: {} } },
            { name: "show_add_button", default: true, selector: { boolean: {} } },
            { name: "history_count", default: 3, selector: { number: { min: 1, max: 10, mode: "box" } } },
          ],
        },
      ],
      computeLabel: (s) => {
        const de = langOf(document.querySelector("home-assistant")?.hass) === "de";
        return {
          device: de ? "Pelletlager" : "Pellet storage",
          title: de ? "Titel (optional)" : "Title (optional)",
          show_stats: de ? "Kennzahlen anzeigen" : "Show key figures",
          show_chart: de ? "Diagramm letzte 12 Monate" : "Chart of the last 12 months",
          show_history: de ? "Lieferungen anzeigen" : "Show deliveries",
          show_add_button: de ? "Knopf „Lieferung eintragen“" : "\"Add delivery\" button",
          history_count: de ? "Anzahl Lieferungen" : "Number of deliveries",
        }[s.name];
      },
    };
  }

  static getStubConfig(hass) {
    const dev = Object.values(hass.entities || {}).find((e) => e.platform === DOMAIN)?.device_id;
    return dev ? { device: dev } : {};
  }

  setConfig(config) {
    const changed = config.device !== this._config?.device;
    this._config = { show_stats: true, show_chart: true, show_history: true, show_add_button: true, history_count: 3, ...config };
    if (changed) { this._data = null; this._fetchedAt = 0; }
    this._showForm = false;
    this._showWhy = false;
    this._render();
  }

  set hass(hass) {
    const old = this._hass;
    this._hass = hass;
    if (this._dialog) this._dialog.hass = hass;
    const stockId = this._entities().stock;
    // Fetch the analysis again when the stock changed (at most once a minute) or every 5 minutes.
    const stockChanged = old && stockId && old.states[stockId] !== hass.states[stockId];
    if (stockChanged && Date.now() - (this._fetchedAt || 0) > 60000) this._fetchedAt = 0;
    this._maybeFetch();
    if (this._showForm && this.shadowRoot) return; // do not interrupt typing
    if (!old || this._ids().some((id) => old.states[id] !== hass.states[id]) || !this.shadowRoot
      || old.themes?.darkMode !== hass.themes?.darkMode) {
      this._render();
    }
  }

  connectedCallback() {
    if (!this._ro && window.ResizeObserver) {
      this._ro = new ResizeObserver(() => {
        const w = Math.round(this.clientWidth);
        if (Math.abs(w - (this._width || 0)) > 8) { this._width = w; if (this._config?.show_chart) this._render(); }
      });
    }
    this._ro?.observe(this);
  }

  disconnectedCallback() { this._ro?.disconnect(); }

  getCardSize() { return 4 + (this._config?.show_chart ? 3 : 0) + (this._config?.show_history ? 2 : 0); }

  getGridOptions() { return { columns: 6, min_columns: 4, rows: "auto" }; }

  _t(key) { return T[langOf(this._hass)][key]; }

  _entities() {
    const map = {};
    const dev = this._config?.device;
    if (!this._hass || !dev) return map;
    for (const e of Object.values(this._hass.entities || {})) {
      if (e.device_id === dev && e.platform === DOMAIN && e.translation_key) map[e.translation_key] = e.entity_id;
    }
    return map;
  }

  _ids() { return Object.values(this._entities()); }

  _state(key) {
    const id = this._entities()[key];
    return id ? this._hass.states[id] : undefined;
  }

  _maybeFetch() {
    if (!this._hass || !this._config?.device || this._loading) return;
    if (Date.now() - (this._fetchedAt || 0) < REFRESH_MS) return;
    this._loading = true;
    fetchData(this._hass, this._config.device)
      .then((d) => { this._data = d; })
      .catch(() => { /* card still works from entity states */ })
      .finally(() => {
        this._loading = false;
        this._fetchedAt = Date.now();
        if (this._dialog && this._data) this._dialog.data = this._data;
        if (!this._showForm) this._render();
      });
  }

  _openDialog() {
    if (this._dialog || !this._config.device) return;
    const dlg = document.createElement("pellet-stock-dialog");
    this._dialog = dlg;
    dlg.setup(this, this._hass, this._config, this._data);
    if (!this._data) { this._fetchedAt = 0; this._maybeFetch(); }
  }

  _silo(percent, low) {
    const p = Math.max(0, Math.min(100, Number(percent) || 0));
    const top = 124 - 118 * (p / 100);
    const color = low ? "var(--error-color)" : colorOf(this._hass);
    const f = makeFmt(this._hass);
    return `<svg class="silo" viewBox="0 0 80 130" role="img" aria-label="${f.num(p)} %">
        <defs><clipPath id="c"><path d="M8 6 h64 v92 l-22 26 h-20 l-22 -26 z"/></clipPath></defs>
        <g clip-path="url(#c)">
          <rect x="0" y="0" width="80" height="130" fill="var(--secondary-background-color)"/>
          <rect x="0" y="${top}" width="80" height="130" fill="${color}" opacity=".9"/>
        </g>
        <path class="silo-body" d="M8 6 h64 v92 l-22 26 h-20 l-22 -26 z"/>
        <text x="40" y="60" text-anchor="middle" font-size="15" fill="var(--primary-text-color)">${f.num(p)}%</text>
      </svg>`;
  }

  _val(key, digits = 0) {
    const s = this._state(key);
    if (!s || ["unknown", "unavailable"].includes(s.state)) return null;
    return Number(s.state);
  }

  _chart(fmt) {
    const months = (this._data?.months || []).slice(-12);
    if (!months.length) return "";
    const current = localIso().slice(0, 7);
    this._rows = months.map((m) => ({
      key: m.period, label: fmt.month(m.period), tip: fmt.monthYear(m.period),
      value: m.kg, kg: m.kg, cost: m.cost, partial: m.period === current,
    }));
    const width = Math.max((this.clientWidth || 360) - 32, 240);
    return `<div class="section-title">${this._t("last12")}</div>
      ${barChart(this._rows, { width, height: 140, color: colorOf(this._hass), fmt, unitFmt: (v) => `${fmt.num(v)}` })}`;
  }

  _render() {
    if (!this._config || !this._hass) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const root = this.shadowRoot;
    const f = makeFmt(this._hass, this._data?.currency);
    const ents = this._entities();
    let body;
    if (!this._config.device) {
      body = `<div class="sub">${this._t("noDevice")}</div>`;
    } else if (!ents.stock) {
      body = `<div class="sub">${this._t("notFound")}</div>`;
    } else {
      const low = this._state("low_stock")?.state === "on";
      const range = this._val("range");
      const reason = this._state("range")?.attributes?.reason || "";
      const dev = this._hass.devices?.[this._config.device];
      const name = this._config.title || dev?.name_by_user || dev?.name || "Pellets";
      const deliveries = (this._state("last_delivery")?.attributes?.deliveries || []).slice(0, this._config.history_count);
      const stat = (v, l) => `<div class="stat"><div class="v">${v}</div><div class="l">${l}</div></div>`;
      body = `
        <div class="head"><div class="title">${esc(name)}</div>${low ? `<span class="badge">${this._t("low")}</span>` : ""}</div>
        <div class="main">
          ${this._silo(this._val("fill_level"), low)}
          <div>
            <div class="big">${f.num(this._val("stock"))}<span class="unit">kg</span></div>
            <div class="sub">${this._t("stock")}</div>
            <div class="range">${this._t("range")}: ${range != null ? `≈ ${f.num(range)} ${this._t("days")}` : this._t("rangeUnknown")}
              ${reason ? `<button class="why" data-why>${this._t("why")}</button>` : ""}</div>
            ${this._showWhy && reason ? `<div class="reason">${esc(reason)}</div>` : ""}
          </div>
        </div>
        ${this._config.show_stats ? `<div class="stats">
          ${stat(this._val("avg_daily_consumption") != null ? `${f.num(this._val("avg_daily_consumption"), 1)} kg` : "–", this._t("avgDay"))}
          ${stat(f.perKwh(this._val("price_per_kwh")), this._t("pricePerKwh"))}
          ${stat(f.money(this._val("cost_month")), this._t("costMonth"))}
          ${stat(f.money(this._val("cost_year")), this._t("costYear"))}
        </div>` : ""}
        ${this._config.show_chart ? this._chart(f) : ""}
        ${this._config.show_history ? `<div class="section-title">${this._t("deliveries")}</div>
          ${deliveries.length ? `<ul>${deliveries.map((d) => `<li><span class="d">${f.date(d.date)}</span>
            <span>${f.num(d.kg)} kg</span><span>${d.price ? f.money(d.price) : ""}</span></li>`).join("")}</ul>`
            : `<div class="sub">${this._t("noDeliveries")}</div>`}` : ""}
        ${this._config.show_add_button ? (this._showForm ? deliveryForm(T[langOf(this._hass)], f, this._err) : `
          <div class="actions">${this._msg ? `<span class="ok">${this._msg}</span>` : ""}
            <button class="primary" data-open>${this._t("addDelivery")}</button></div>`) : ""}`;
    }
    root.innerHTML = `<style>${BASE_CSS}${CARD_CSS}</style>
      <ha-card tabindex="0" role="button" aria-label="${this._t("details")}">${body}</ha-card>`;
    const card = root.querySelector("ha-card");
    card.addEventListener("click", (e) => {
      if (e.target.closest("button, form, input, .chart")) return;
      this._openDialog();
    });
    card.addEventListener("keydown", (e) => {
      if ((e.key === "Enter" || e.key === " ") && e.target === card) { e.preventDefault(); this._openDialog(); }
    });
    root.querySelector("[data-why]")?.addEventListener("click", () => { this._showWhy = !this._showWhy; this._render(); });
    root.querySelector("[data-open]")?.addEventListener("click", () => { this._showForm = true; this._msg = ""; this._render(); });
    root.querySelector("[data-cancel]")?.addEventListener("click", () => { this._showForm = false; this._render(); });
    root.querySelector("form")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      try {
        await submitDelivery(this._hass, this._entryId(), ev.target);
        this._showForm = false; this._err = ""; this._msg = this._t("saved"); this._fetchedAt = 0;
      } catch (e) { this._err = e?.message || String(e); }
      this._render();
      this._maybeFetch();
    });
    if (this._rows && this._config.show_chart) {
      bindChart(root, this._rows, {
        tip: (r) => `<div class="tt-title">${esc(r.tip)}</div>
          <div class="tt-row">${this._t("consumption")}<b>${f.num(r.kg)} kg</b></div>
          <div class="tt-row">${this._t("cost")}<b>${f.money(r.cost)}</b></div>`,
        onClick: (r) => { this._openDialog(); this._dialog?.openMonth(r.key); },
      });
    }
  }

  _entryId() { return this._hass.devices?.[this._config.device]?.config_entries?.[0]; }
}

// ─── Popup ───────────────────────────────────────────────────────────────────

const DIALOG_CSS = `
  :host { position: fixed; inset: 0; z-index: 9999; display: flex; align-items: center; justify-content: center;
    font-family: var(--paper-font-body1_-_font-family, var(--ha-font-family-body, system-ui, sans-serif)); }
  .backdrop { position: absolute; inset: 0; background: rgba(0,0,0,.45); }
  .panel { position: relative; width: min(780px, calc(100vw - 16px)); max-height: calc(100vh - 32px);
    display: flex; flex-direction: column; border-radius: 16px; overflow: hidden;
    background: var(--card-background-color, #fff); color: var(--primary-text-color); box-shadow: 0 10px 40px rgba(0,0,0,.35); }
  @media (max-width: 600px) { :host { align-items: flex-end; } .panel { width: 100vw; max-height: 92vh; border-radius: 16px 16px 0 0; } }
  .dhead, .tabs { flex-shrink: 0; }
  .dhead { display: flex; align-items: center; padding: 14px 16px 6px; }
  .dtitle { font-size: 1.15em; font-weight: 600; flex: 1; }
  .close { background: none; border: none; font-size: 1.1em; cursor: pointer; color: var(--secondary-text-color); padding: 6px 8px; border-radius: 8px; }
  .close:focus:not(:focus-visible) { outline: none; }
  .close:hover { background: var(--secondary-background-color); }
  .tabs { display: flex; gap: 4px; padding: 0 12px; border-bottom: 1px solid var(--divider-color); overflow-x: auto; }
  .tabs button { background: none; border: none; padding: 10px 12px; cursor: pointer; font: inherit; font-size: .95em; white-space: nowrap;
    color: var(--secondary-text-color); border-bottom: 2px solid transparent; margin-bottom: -1px; }
  .tabs button.active { color: var(--primary-text-color); border-bottom-color: var(--primary-color); font-weight: 600; }
  .body { padding: 14px 16px 20px; overflow-y: auto; flex: 1; min-height: 0; }
  @media (max-width: 520px) { .opt { display: none; } }
  .msg { padding: 24px 0; text-align: center; color: var(--secondary-text-color); }
  .bigv { font-size: 2.1em; font-weight: 700; line-height: 1.15; }
  .track { height: 8px; border-radius: 4px; background: var(--divider-color); overflow: hidden; margin: 8px 0 6px; }
  .fill { height: 100%; border-radius: 4px; }
  .grid4 { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 8px; margin: 10px 0; }
  .st { background: var(--secondary-background-color); border-radius: 10px; padding: 10px 12px; }
  .st .l { font-size: .78em; color: var(--secondary-text-color); }
  .st .v { font-size: 1.15em; font-weight: 600; margin-top: 2px; }
  .st .s { font-size: .75em; color: var(--secondary-text-color); margin-top: 2px; }
  .why { background: var(--secondary-background-color); border-radius: 10px; padding: 10px 12px; font-size: .9em; line-height: 1.45; }
  .facts { font-size: .85em; margin-top: 8px; }
  .facts div { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; border-bottom: 1px solid var(--divider-color); }
  .facts span { color: var(--secondary-text-color); }
  .chips { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; align-items: center; }
  .chip { border: 1px solid var(--divider-color); background: none; color: var(--primary-text-color);
    border-radius: 16px; padding: 4px 12px; cursor: pointer; font: inherit; font-size: .85em; }
  .chip.active { background: var(--primary-color); border-color: var(--primary-color); color: var(--text-primary-color, #fff); }
  .spacer { flex: 1; }
  .hint { font-size: .8em; color: var(--secondary-text-color); margin: 2px 0 4px; }
  .table-wrap { overflow-x: auto; margin-top: 10px; }
  table { width: 100%; border-collapse: collapse; font-size: .85em; font-variant-numeric: tabular-nums; }
  th, td { padding: 7px 8px; text-align: right; white-space: nowrap; border-bottom: 1px solid var(--divider-color); }
  th:first-child, td:first-child { text-align: left; }
  th { font-weight: 600; color: var(--secondary-text-color); font-size: .9em; }
  tfoot td { font-weight: 600; border-bottom: none; }
  tr.clickable { cursor: pointer; }
  tr.clickable:hover td { background: var(--secondary-background-color); }
  td.note { text-align: left; white-space: normal; color: var(--secondary-text-color); }
`;

class PelletStockDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = "overview";
    this._metric = "kg";
    this._onKey = (e) => { if (e.key === "Escape") this.close(); };
  }

  setup(card, hass, config, data) {
    this._card = card;
    this._hass = hass;
    this._config = config;
    this._data = data;
    document.body.appendChild(this);
    document.addEventListener("keydown", this._onKey);
    this._render();
    this.shadowRoot.querySelector(".close")?.focus();
  }

  set hass(h) { this._hass = h; }
  set data(d) { if (d) { this._data = d; if (!this._showForm) this._render(); } }

  close() {
    document.removeEventListener("keydown", this._onKey);
    this.remove();
    if (this._card) this._card._dialog = null;
  }

  openMonth(key) {
    this._tab = "months";
    this._year = key.slice(0, 4);
    this._month = key;
    this._days = null;
    this._render();
    fetchData(this._hass, this._config.device, key)
      .then((d) => { if (this._month === key) { this._days = d.days || []; this._render(); } })
      .catch(() => { if (this._month === key) { this._days = []; this._render(); } });
  }

  _t() { return T[langOf(this._hass)]; }
  _fmt() { return makeFmt(this._hass, this._data?.currency); }
  _width() {
    const b = this.shadowRoot.querySelector(".body");
    return Math.max((b ? b.clientWidth : Math.min(window.innerWidth - 16, 760)) - 40, 260);
  }

  _render() {
    const t = this._t();
    const title = (this._config.title || "").trim() || this._data?.name || "Pellets";
    const tabs = [["overview", t.tabOverview], ["months", t.tabMonths], ["weeks", t.tabWeeks], ["deliveries", t.tabDeliveries]];
    const scrollTop = this.shadowRoot.querySelector(".body")?.scrollTop || 0;
    this.shadowRoot.innerHTML = `<style>${BASE_CSS}${DIALOG_CSS}</style>
      <div class="backdrop"></div>
      <div class="panel" role="dialog" aria-modal="true" aria-label="${esc(title)}">
        <div class="dhead"><div class="dtitle">${esc(title)}</div><button class="close" aria-label="${t.close}">✕</button></div>
        <div class="tabs" role="tablist">${tabs.map(([id, l]) =>
          `<button role="tab" data-tab="${id}" aria-selected="${this._tab === id}" class="${this._tab === id ? "active" : ""}">${l}</button>`).join("")}</div>
        <div class="body"></div>
      </div>`;
    const root = this.shadowRoot;
    root.querySelector(".backdrop").addEventListener("click", () => this.close());
    root.querySelector(".close").addEventListener("click", () => this.close());
    root.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => {
      this._tab = b.dataset.tab; this._month = null; this._week = null; this._showForm = false; this._render();
    }));
    const body = root.querySelector(".body");
    body.innerHTML = this._data ? this[`_tab_${this._tab}`]() : `<div class="msg">${t.loading}</div>`;
    if (this._data) this[`_bind_${this._tab}`]?.(body);
    body.scrollTop = scrollTop;
  }

  _metricChips() {
    const t = this._t();
    return `<span class="spacer"></span>
      <button class="chip${this._metric === "kg" ? " active" : ""}" data-metric="kg">kg</button>
      <button class="chip${this._metric === "cost" ? " active" : ""}" data-metric="cost">${esc(this._fmt().symbol)}</button>`;
  }

  _bindMetric(body) {
    body.querySelectorAll("[data-metric]").forEach((b) =>
      b.addEventListener("click", () => { this._metric = b.dataset.metric; this._render(); }));
  }

  _tipFn() {
    const t = this._t(), f = this._fmt(), cv = this._data.calorific_value || 4.8;
    return (r) => `<div class="tt-title">${esc(r.tip)}</div>
      <div class="tt-row">${t.consumption}<b>${f.num(r.kg, 1)} kg</b></div>
      <div class="tt-row">${t.energy}<b>${f.num(r.kg * cv)} kWh</b></div>
      <div class="tt-row">${t.cost}<b>${f.money(r.cost)}</b></div>
      ${r.n > 1 ? `<div class="tt-row">${t.avgDay}<b>${f.num(r.kg / r.n, 1)} kg</b></div>` : ""}`;
  }

  _unitFmt() {
    const f = this._fmt();
    return this._metric === "cost" ? (v) => f.money(v, 0) : (v) => f.num(v);
  }

  _rowsWithMetric(rows) {
    return rows.map((r) => ({ ...r, value: this._metric === "cost" ? r.cost : r.kg }));
  }

  // ── Overview ────────────────────────────────────────────────────────────────

  _tab_overview() {
    const t = this._t(), f = this._fmt(), k = this._data.kpis || {};
    const pct = k.capacity_kg ? Math.max(0, Math.min(100, (k.stock_kg / k.capacity_kg) * 100)) : 0;
    const color = k.low_stock ? "var(--error-color)" : colorOf(this._hass);
    const st = (l, v, s = "") => `<div class="st"><div class="l">${l}</div><div class="v">${v}</div>${s ? `<div class="s">${s}</div>` : ""}</div>`;
    return `
      <div class="l muted">${t.stock}</div>
      <div class="bigv">${f.num(k.stock_kg)} kg</div>
      <div class="track"><div class="fill" style="width:${pct}%;background:${color}"></div></div>
      <div class="muted" style="font-size:.85em">${f.num(pct)} % · ${t.capacity} ${f.num(k.capacity_kg)} kg · ${t.minStock} ${f.num(k.min_stock_kg)} kg
        ${k.low_stock ? ` · <b style="color:var(--error-color)">${t.low}</b>` : ""}</div>
      <div class="grid4">
        ${st(t.range, k.range_days != null ? `≈ ${f.num(k.range_days)} ${t.days}` : t.rangeUnknown)}
        ${st(t.avgDay, k.avg_kg_per_day != null ? `${f.num(k.avg_kg_per_day, 1)} kg` : "–")}
        ${st(t.today, `${f.num(k.today_kg, 1)} kg`)}
        ${st(t.monthKg, `${f.num(k.month_kg)} kg`)}
        ${st(t.costMonthLong, f.money(k.month_cost))}
        ${st(t.costYearLong, f.money(k.year_cost))}
        ${st(t.pricePerTonne, k.price_per_tonne != null ? f.money(k.price_per_tonne) : "–")}
        ${st(t.pricePerKwh, f.perKwh(k.price_per_kwh))}
      </div>
      ${k.range_reason ? `<div class="section-title">${t.why}</div><div class="why">${esc(k.range_reason)}</div>` : ""}
      <div class="facts">
        <div><span>${t.total}</span><b>${f.num(k.total_kg)} kg</b></div>
        <div><span>${t.since}</span><b>${k.tracking_since ? f.date(k.tracking_since.slice(0, 10)) : "–"}</b></div>
        ${k.history_from ? `<div><span>${t.historyFrom}</span><b>${f.date(k.history_from)}</b></div>` : ""}
      </div>`;
  }

  // ── Months → days ──────────────────────────────────────────────────────────

  _years() { return [...new Set((this._data.months || []).map((m) => m.period.slice(0, 4)))].sort(); }

  _tab_months() {
    const t = this._t(), f = this._fmt();
    if (!(this._data.months || []).length) return `<div class="msg">${t.noData}</div>`;
    if (this._month) return this._daysView();
    const years = this._years();
    if (!this._year || !years.includes(this._year)) this._year = years[years.length - 1];
    const byKey = Object.fromEntries(this._data.months.map((m) => [m.period, m]));
    const current = localIso().slice(0, 7);
    const months = Array.from({ length: 12 }, (_, i) => {
      const key = `${this._year}-${String(i + 1).padStart(2, "0")}`;
      const m = byKey[key];
      const [y, mo] = key.split("-").map(Number);
      const n = key === current ? new Date().getDate() : new Date(y, mo, 0).getDate();
      return { key, label: f.month(key, "narrow"), tip: f.monthYear(key), kg: m?.kg || 0, cost: m?.cost || 0,
        has: !!m, clickable: !!m, partial: key === current, n };
    });
    this._rows = this._rowsWithMetric(months);
    const year = (this._data.years || []).find((y) => y.period === this._year) || { kg: 0, cost: 0 };
    const cv = this._data.calorific_value || 4.8;
    return `
      <div class="chips">${years.map((y) => `<button class="chip${y === this._year ? " active" : ""}" data-year="${y}">${y}</button>`).join("")}${this._metricChips()}</div>
      <div class="hint">${t.tapHint}</div>
      ${barChart(this._rows, { width: this._width(), height: 190, color: colorOf(this._hass), fmt: f, unitFmt: this._unitFmt(), clickable: true })}
      <div class="table-wrap"><table>
        <thead><tr><th>${t.month}</th><th>${t.consumption}</th><th class="opt">${t.energy}</th><th>${t.avgDay}</th><th>${t.cost}</th></tr></thead>
        <tbody>${months.filter((m) => m.has).map((m) => `<tr class="clickable" data-month="${m.key}">
          <td>${esc(f.month(m.key, "long"))}</td><td>${f.num(m.kg)} kg</td><td class="opt">${f.num(m.kg * cv)} kWh</td>
          <td>${f.num(m.kg / m.n, 1)} kg</td><td><b>${f.money(m.cost)}</b></td></tr>`).join("")}</tbody>
        <tfoot><tr><td>${this._year}</td><td>${f.num(year.kg)} kg</td><td class="opt">${f.num(year.kg * cv)} kWh</td><td></td><td>${f.money(year.cost)}</td></tr></tfoot>
      </table></div>
      ${years.length > 1 ? `<div class="section-title">${t.years}</div><div class="table-wrap"><table>
        <thead><tr><th>${t.year}</th><th>${t.consumption}</th><th class="opt">${t.energy}</th><th>${t.cost}</th></tr></thead>
        <tbody>${this._data.years.map((y) => `<tr><td>${y.period}</td><td>${f.num(y.kg)} kg</td><td class="opt">${f.num(y.kg * cv)} kWh</td><td><b>${f.money(y.cost)}</b></td></tr>`).join("")}</tbody>
      </table></div>` : ""}`;
  }

  _daysView() {
    const t = this._t(), f = this._fmt();
    const back = `<button class="link" data-back>‹ ${t.back} ${this._year}</button>`;
    const title = `<div class="section-title">${t.daysOf} ${esc(f.monthYear(this._month))}</div>`;
    if (!this._days) return `${back}${title}<div class="msg">${t.loading}</div>`;
    const [y, m] = this._month.split("-").map(Number);
    const n = new Date(y, m, 0).getDate();
    const byKey = Object.fromEntries(this._days.map((d) => [d.period, d]));
    const today = localIso();
    const days = Array.from({ length: n }, (_, i) => {
      const key = `${this._month}-${String(i + 1).padStart(2, "0")}`;
      const d = byKey[key];
      return { key, label: String(i + 1), tip: f.date(key, { weekday: "short", day: "2-digit", month: "long" }),
        kg: d?.kg || 0, cost: d?.cost || 0, has: !!d, partial: key === today, n: 1, clickable: false };
    });
    this._rows = this._rowsWithMetric(days);
    return `${back}${title}
      <div class="chips">${this._metricChips()}</div>
      ${barChart(this._rows, { width: this._width(), height: 190, color: colorOf(this._hass), fmt: f, unitFmt: this._unitFmt() })}
      ${this._dayTable(days.filter((d) => d.has))}`;
  }

  _dayTable(days) {
    const t = this._t(), f = this._fmt(), cv = this._data.calorific_value || 4.8;
    if (!days.length) return `<div class="msg">${t.noData}</div>`;
    return `<div class="table-wrap"><table>
      <thead><tr><th>${t.day}</th><th>${t.consumption}</th><th class="opt">${t.energy}</th><th>${t.cost}</th></tr></thead>
      <tbody>${days.map((d) => `<tr><td>${esc(f.date(d.key, { weekday: "short", day: "2-digit", month: "2-digit" }))}</td>
        <td>${f.num(d.kg, 1)} kg</td><td class="opt">${f.num(d.kg * cv)} kWh</td><td>${f.money(d.cost)}</td></tr>`).join("")}</tbody>
    </table></div>`;
  }

  _bind_months(body) {
    this._bindMetric(body);
    body.querySelectorAll("[data-year]").forEach((b) => b.addEventListener("click", () => { this._year = b.dataset.year; this._render(); }));
    body.querySelectorAll("tr[data-month]").forEach((tr) => tr.addEventListener("click", () => this.openMonth(tr.dataset.month)));
    body.querySelector("[data-back]")?.addEventListener("click", () => { this._month = null; this._render(); });
    if (this._rows) bindChart(body, this._rows, { tip: this._tipFn(), onClick: this._month ? null : (r) => this.openMonth(r.key) });
  }

  // ── Weeks → days ───────────────────────────────────────────────────────────

  _tab_weeks() {
    const t = this._t(), f = this._fmt();
    const weeks = this._data.weeks || [];
    if (!weeks.some((w) => w.kg > 0)) return `<div class="msg">${t.noData}</div>`;
    if (this._week) {
      const w = weeks.find((x) => x.period === this._week);
      const days = (w?.days || []).map((d) => ({
        key: d.period, label: f.date(d.period, { weekday: "short" }), tip: f.date(d.period, { weekday: "long", day: "2-digit", month: "long" }),
        kg: d.kg, cost: d.cost, has: true, n: 1, clickable: false,
      }));
      this._rows = this._rowsWithMetric(days);
      return `<button class="link" data-back>‹ ${t.back} ${t.tabWeeks}</button>
        <div class="section-title">${t.weeksOf} ${esc(w.period.split("-W")[1])} · ${f.date(w.start)}</div>
        <div class="chips">${this._metricChips()}</div>
        ${barChart(this._rows, { width: this._width(), height: 190, color: colorOf(this._hass), fmt: f, unitFmt: this._unitFmt() })}
        ${this._dayTable(days.filter((d) => d.key <= localIso()))}`;
    }
    const cv = this._data.calorific_value || 4.8;
    const rows = weeks.map((w, i) => ({
      key: w.period, label: `${w.period.split("-W")[1]}`, tip: `${t.kw} ${w.period.split("-W")[1]} · ${f.date(w.start, { day: "2-digit", month: "2-digit" })}`,
      kg: w.kg, cost: w.cost, n: i === weeks.length - 1 ? ((new Date().getDay() + 6) % 7) + 1 : 7,
      partial: i === weeks.length - 1, clickable: true,
    }));
    this._rows = this._rowsWithMetric(rows);
    return `<div class="chips"><span class="muted" style="font-size:.85em">${t.kw}</span>${this._metricChips()}</div>
      <div class="hint">${t.tapHint}</div>
      ${barChart(this._rows, { width: this._width(), height: 190, color: colorOf(this._hass), fmt: f, unitFmt: this._unitFmt(), clickable: true })}
      <div class="table-wrap"><table>
        <thead><tr><th>${t.week}</th><th>${t.consumption}</th><th class="opt">${t.energy}</th><th>${t.avgDay}</th><th>${t.cost}</th></tr></thead>
        <tbody>${[...rows].reverse().filter((r) => r.kg > 0).map((r) => `<tr class="clickable" data-week="${r.key}">
          <td>${esc(r.tip)}</td><td>${f.num(r.kg, 1)} kg</td><td class="opt">${f.num(r.kg * cv)} kWh</td><td>${f.num(r.kg / r.n, 1)} kg</td><td><b>${f.money(r.cost)}</b></td></tr>`).join("")}</tbody>
      </table></div>`;
  }

  _bind_weeks(body) {
    this._bindMetric(body);
    body.querySelectorAll("tr[data-week]").forEach((tr) => tr.addEventListener("click", () => { this._week = tr.dataset.week; this._render(); }));
    body.querySelector("[data-back]")?.addEventListener("click", () => { this._week = null; this._render(); });
    if (this._rows) bindChart(body, this._rows, { tip: this._tipFn(), onClick: this._week ? null : (r) => { this._week = r.key; this._render(); } });
  }

  // ── Deliveries ─────────────────────────────────────────────────────────────

  _tab_deliveries() {
    const t = this._t(), f = this._fmt();
    const list = this._data.deliveries || [];
    const sumKg = list.reduce((a, d) => a + d.kg, 0), sumP = list.reduce((a, d) => a + (d.price || 0), 0);
    return `${this._showForm ? deliveryForm(t, f, this._err)
        : `<div class="actions" style="margin-top:0">${this._msg ? `<span class="ok">${this._msg}</span>` : ""}<button class="primary" data-open>${t.addDelivery}</button></div>`}
      ${list.length ? `<div class="table-wrap"><table>
        <thead><tr><th>${t.date}</th><th>${t.qty}</th><th>${t.price}</th><th class="opt">${t.pricePerTonne}</th><th class="opt">${t.note}</th></tr></thead>
        <tbody>${list.map((d) => `<tr><td>${f.date(d.date)}</td><td>${f.num(d.kg)} kg</td><td>${d.price ? f.money(d.price) : "–"}</td>
          <td class="opt">${d.price ? f.money((d.price / d.kg) * 1000) : "–"}</td><td class="note opt">${esc(d.note || "")}</td></tr>`).join("")}</tbody>
        <tfoot><tr><td></td><td>${f.num(sumKg)} kg</td><td>${f.money(sumP)}</td><td class="opt">${sumP ? f.money((sumP / sumKg) * 1000) : ""}</td><td class="opt"></td></tr></tfoot>
      </table></div>` : `<div class="msg">${t.noDeliveries}</div>`}`;
  }

  _bind_deliveries(body) {
    body.querySelector("[data-open]")?.addEventListener("click", () => { this._showForm = true; this._msg = ""; this._render(); });
    body.querySelector("[data-cancel]")?.addEventListener("click", () => { this._showForm = false; this._render(); });
    body.querySelector("form")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      try {
        await submitDelivery(this._hass, this._card?._entryId() || this._data.entry_id, ev.target);
        this._showForm = false; this._err = ""; this._msg = this._t().saved;
        this._data = await fetchData(this._hass, this._config.device);
      } catch (e) { this._err = e?.message || String(e); }
      this._render();
    });
  }
}

if (!customElements.get("pellet-stock-card")) {
  customElements.define("pellet-stock-card", PelletStockCard);
  customElements.define("pellet-stock-dialog", PelletStockDialog);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "pellet-stock-card",
    name: "Pellet Stock",
    description: "Silo, stock, range, monthly and weekly analysis and deliveries of a pellet storage.",
    preview: true,
    documentationURL: "https://github.com/PXLJAKE/ha-pellet-stock",
  });
  console.info(`%c PELLET-STOCK-CARD %c ${VERSION} `, "background:#2a78d6;color:#fff", "");
}

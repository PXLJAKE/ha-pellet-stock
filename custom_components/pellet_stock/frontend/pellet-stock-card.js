/*
 * Pellet Stock Card for Home Assistant.
 * Plain web component, no framework and no build step, so it loads fast.
 * Uses Home Assistant theme variables, works in light and dark mode.
 */
const VERSION = "0.1.0";
const DOMAIN = "pellet_stock";

const T = {
  en: {
    stock: "Stock", range: "Range", days: "days", perDay: "per day",
    pricePerKwh: "Price per kWh", costMonth: "This month", costYear: "This year",
    low: "Minimum stock reached", deliveries: "Deliveries", noDeliveries: "No deliveries yet",
    addDelivery: "Add delivery", amount: "Amount (kg)", price: "Total price",
    date: "Date", save: "Save", cancel: "Cancel", why: "Why?",
    noDevice: "Choose a pellet storage in the card settings.",
    notFound: "Pellet storage not found.", saved: "Delivery saved",
    rangeUnknown: "not yet known", today: "Today",
  },
  de: {
    stock: "Bestand", range: "Reichweite", days: "Tage", perDay: "pro Tag",
    pricePerKwh: "Preis pro kWh", costMonth: "Diesen Monat", costYear: "Dieses Jahr",
    low: "Mindestbestand erreicht", deliveries: "Lieferungen", noDeliveries: "Noch keine Lieferungen",
    addDelivery: "Lieferung eintragen", amount: "Menge (kg)", price: "Gesamtpreis",
    date: "Datum", save: "Speichern", cancel: "Abbrechen", why: "Warum?",
    noDevice: "Wähle in den Karteneinstellungen ein Pelletlager.",
    notFound: "Pelletlager nicht gefunden.", saved: "Lieferung gespeichert",
    rangeUnknown: "noch unbekannt", today: "Heute",
  },
};

const STYLE = `
  :host { display: block; }
  ha-card { padding: 16px; container-type: inline-size; }
  .head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 12px; }
  .title { font-size: 1.15em; font-weight: 500; color: var(--primary-text-color); }
  .badge { font-size: .8em; padding: 2px 10px; border-radius: 12px; color: var(--error-color);
    background: color-mix(in srgb, var(--error-color) 14%, transparent); white-space: nowrap; }
  .main { display: grid; grid-template-columns: 88px 1fr; gap: 16px; align-items: center; }
  @container (max-width: 260px) { .main { grid-template-columns: 1fr; justify-items: center; } }
  svg { width: 88px; height: auto; display: block; }
  .silo-body { fill: none; stroke: var(--divider-color); stroke-width: 2; }
  .silo-fill { transition: y .6s ease, height .6s ease; }
  .big { font-size: 2em; font-weight: 400; line-height: 1.1; color: var(--primary-text-color); cursor: pointer; }
  .unit { font-size: .5em; color: var(--secondary-text-color); margin-left: 4px; }
  .sub { color: var(--secondary-text-color); font-size: .9em; }
  .range { margin-top: 8px; font-size: 1.05em; color: var(--primary-text-color); cursor: pointer; }
  .why { background: none; border: none; padding: 0; margin-left: 6px; color: var(--primary-color);
    font: inherit; font-size: .85em; cursor: pointer; }
  .reason { margin-top: 6px; font-size: .85em; color: var(--secondary-text-color); line-height: 1.4; }
  .stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 16px; }
  @container (min-width: 560px) { .stats { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
  .stat { padding: 8px 10px; border-radius: 10px; background: var(--secondary-background-color); cursor: pointer; }
  .stat .v { font-size: 1.05em; color: var(--primary-text-color); }
  .stat .l { font-size: .78em; color: var(--secondary-text-color); }
  h4 { margin: 18px 0 6px; font-size: .9em; font-weight: 500; color: var(--secondary-text-color); }
  ul { list-style: none; margin: 0; padding: 0; }
  li { display: grid; grid-template-columns: 1fr auto minmax(5.5em, auto); gap: 16px; padding: 6px 0; text-align: right;
    border-bottom: 1px solid var(--divider-color); font-size: .92em; color: var(--primary-text-color); }
  li:last-child { border-bottom: none; }
  li .d { color: var(--secondary-text-color); text-align: left; }
  .actions { margin-top: 12px; display: flex; justify-content: flex-end; }
  button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border: none;
    border-radius: 18px; padding: 8px 16px; font: inherit; cursor: pointer; }
  button.flat { background: none; border: none; color: var(--primary-color); font: inherit; cursor: pointer; padding: 8px 12px; }
  form { display: grid; gap: 8px; margin-top: 12px; min-width: 0; }
  label { display: grid; gap: 4px; font-size: .85em; color: var(--secondary-text-color); }
  input { box-sizing: border-box; width: 100%; min-width: 0; font: inherit; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--divider-color);
    background: var(--card-background-color); color: var(--primary-text-color); }
  .row { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; }
  .err { color: var(--error-color); font-size: .85em; }
  .ok { color: var(--success-color, var(--primary-color)); font-size: .85em; }
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
            { name: "show_history", default: true, selector: { boolean: {} } },
            { name: "show_add_button", default: true, selector: { boolean: {} } },
            { name: "history_count", default: 5, selector: { number: { min: 1, max: 10, mode: "box" } } },
          ],
        },
      ],
      computeLabel: (s) => {
        const de = (document.querySelector("home-assistant")?.hass?.locale?.language || "").startsWith("de");
        const labels = {
          device: de ? "Pelletlager" : "Pellet storage",
          title: de ? "Titel (optional)" : "Title (optional)",
          show_stats: de ? "Kennzahlen anzeigen" : "Show key figures",
          show_history: de ? "Lieferungen anzeigen" : "Show deliveries",
          show_add_button: de ? "Knopf „Lieferung eintragen“" : "\"Add delivery\" button",
          history_count: de ? "Anzahl Lieferungen" : "Number of deliveries",
        };
        return labels[s.name];
      },
    };
  }

  static getStubConfig(hass) {
    const dev = Object.values(hass.entities || {}).find((e) => e.platform === DOMAIN)?.device_id;
    return dev ? { device: dev } : {};
  }

  setConfig(config) {
    this._config = { show_stats: true, show_history: true, show_add_button: true, history_count: 5, ...config };
    this._showForm = false;
    this._showWhy = false;
    this._render();
  }

  set hass(hass) {
    const old = this._hass;
    this._hass = hass;
    // Re-render only when one of our entities changed (keeps the card cheap).
    // Never while the delivery form is open, so typing is not interrupted.
    if (this._showForm && this.shadowRoot) return;
    if (!old || this._ids().some((id) => old.states[id] !== hass.states[id]) || !this.shadowRoot) {
      this._render();
    }
  }

  getCardSize() { return this._config?.show_history ? 6 : 4; }

  getGridOptions() { return { columns: 6, min_columns: 4, rows: "auto" }; }

  _t(key) {
    const lang = (this._hass?.locale?.language || "en").startsWith("de") ? "de" : "en";
    return T[lang][key];
  }

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

  _num(value, digits = 0) {
    const n = Number(value);
    if (value === undefined || value === null || Number.isNaN(n)) return "–";
    return new Intl.NumberFormat(this._hass.locale?.language || "en", {
      maximumFractionDigits: digits, minimumFractionDigits: digits,
    }).format(n);
  }

  _fmt(key, digits = 0) {
    const s = this._state(key);
    if (!s || ["unknown", "unavailable"].includes(s.state)) return "–";
    return `${this._num(s.state, digits)} ${s.attributes.unit_of_measurement || ""}`.trim();
  }

  _pricePerKwh() {
    const s = this._state("price_per_kwh");
    if (!s || ["unknown", "unavailable"].includes(s.state)) return "–";
    // Cent per kWh reads easier than 0.0935 EUR/kWh.
    if ((this._hass.config?.currency || "") === "EUR") return `${this._num(s.state * 100, 2)} ct/kWh`;
    return this._fmt("price_per_kwh", 3);
  }

  _date(iso) {
    return new Intl.DateTimeFormat(this._hass.locale?.language || "en", { dateStyle: "medium" })
      .format(new Date(`${iso}T12:00:00`));
  }

  _moreInfo(key) {
    const entityId = this._entities()[key];
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true }));
  }

  _silo(percent, low) {
    const p = Math.max(0, Math.min(100, Number(percent) || 0));
    const top = 124 - 118 * (p / 100);
    const color = low ? "var(--error-color)" : "var(--primary-color)";
    return `
      <svg viewBox="0 0 80 130" role="img" aria-label="${this._num(p)} %">
        <defs><clipPath id="c"><path d="M8 6 h64 v92 l-22 26 h-20 l-22 -26 z"/></clipPath></defs>
        <g clip-path="url(#c)">
          <rect x="0" y="0" width="80" height="130" fill="var(--secondary-background-color)"/>
          <rect class="silo-fill" x="0" y="${top}" width="80" height="130" fill="${color}" opacity=".85"/>
        </g>
        <path class="silo-body" d="M8 6 h64 v92 l-22 26 h-20 l-22 -26 z"/>
        <text x="40" y="60" text-anchor="middle" font-size="15" fill="var(--primary-text-color)">${this._num(p)}%</text>
      </svg>`;
  }

  _render() {
    if (!this._config || !this._hass) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const root = this.shadowRoot;
    const ents = this._entities();
    let body;
    if (!this._config.device) {
      body = `<div class="sub">${this._t("noDevice")}</div>`;
    } else if (!ents.stock) {
      body = `<div class="sub">${this._t("notFound")}</div>`;
    } else {
      const low = this._state("low_stock")?.state === "on";
      const stock = this._state("stock");
      const fill = this._state("fill_level")?.state;
      const range = this._state("range");
      const rangeText = range && !["unknown", "unavailable"].includes(range.state)
        ? `≈ ${this._num(range.state)} ${this._t("days")}` : this._t("rangeUnknown");
      const reason = range?.attributes?.reason || "";
      const name = this._config.title || this._hass.devices?.[this._config.device]?.name_by_user
        || this._hass.devices?.[this._config.device]?.name || "Pellets";
      const deliveries = (this._state("last_delivery")?.attributes?.deliveries || [])
        .slice(0, this._config.history_count);
      const currency = this._hass.config?.currency || "";

      body = `
        <div class="head"><div class="title">${esc(name)}</div>${low ? `<span class="badge">${this._t("low")}</span>` : ""}</div>
        <div class="main">
          ${this._silo(fill, low)}
          <div>
            <div class="big" data-more="stock">${this._num(stock?.state)}<span class="unit">kg</span></div>
            <div class="sub">${this._t("stock")}</div>
            <div class="range"><span data-more="range">${this._t("range")}: ${rangeText}</span>
              ${reason ? `<button class="why" data-why>${this._t("why")}</button>` : ""}</div>
            ${this._showWhy && reason ? `<div class="reason">${esc(reason)}</div>` : ""}
          </div>
        </div>
        ${this._config.show_stats ? `
        <div class="stats">
          <div class="stat" data-more="avg_daily_consumption"><div class="v">${this._fmt("avg_daily_consumption", 1).replace("kg/d", "kg")}</div><div class="l">Ø ${this._t("perDay")}</div></div>
          <div class="stat" data-more="price_per_kwh"><div class="v">${this._pricePerKwh()}</div><div class="l">${this._t("pricePerKwh")}</div></div>
          <div class="stat" data-more="cost_month"><div class="v">${this._fmt("cost_month", 2)}</div><div class="l">${this._t("costMonth")}</div></div>
          <div class="stat" data-more="cost_year"><div class="v">${this._fmt("cost_year", 2)}</div><div class="l">${this._t("costYear")}</div></div>
        </div>` : ""}
        ${this._config.show_history ? `
        <h4>${this._t("deliveries")}</h4>
        ${deliveries.length ? `<ul>${deliveries.map((d) => `
          <li><span class="d">${this._date(d.date)}</span><span>${this._num(d.kg)} kg</span>
          <span>${d.price ? `${this._num(d.price, 2)} ${esc(currency)}` : ""}</span></li>`).join("")}</ul>`
          : `<div class="sub">${this._t("noDeliveries")}</div>`}` : ""}
        ${this._config.show_add_button ? (this._showForm ? this._form(currency) : `
        <div class="actions">${this._msg ? `<span class="ok">${this._msg}</span>` : ""}
          <button class="primary" data-open>${this._t("addDelivery")}</button></div>`) : ""}
      `;
    }
    root.innerHTML = `<style>${STYLE}</style><ha-card>${body}</ha-card>`;
    root.querySelectorAll("[data-more]").forEach((el) =>
      el.addEventListener("click", () => this._moreInfo(el.dataset.more)));
    root.querySelector("[data-why]")?.addEventListener("click", () => { this._showWhy = !this._showWhy; this._render(); });
    root.querySelector("[data-open]")?.addEventListener("click", () => { this._showForm = true; this._msg = ""; this._render(); });
    root.querySelector("[data-cancel]")?.addEventListener("click", () => { this._showForm = false; this._render(); });
    root.querySelector("form")?.addEventListener("submit", (ev) => this._submit(ev));
  }

  _form(currency) {
    const today = new Date();
    const iso = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    return `
      <form>
        <div class="row">
          <label>${this._t("amount")}<input name="kg" type="number" min="0.1" step="0.1" required inputmode="decimal"></label>
          <label>${this._t("price")} (${esc(currency)})<input name="price" type="number" min="0" step="0.01" inputmode="decimal"></label>
        </div>
        <label>${this._t("date")}<input name="date" type="date" value="${iso}"></label>
        ${this._err ? `<div class="err">${esc(this._err)}</div>` : ""}
        <div class="actions"><button type="button" class="flat" data-cancel>${this._t("cancel")}</button>
          <button type="submit" class="primary">${this._t("save")}</button></div>
      </form>`;
  }

  async _submit(ev) {
    ev.preventDefault();
    const data = new FormData(ev.target);
    const entryId = this._hass.devices?.[this._config.device]?.config_entries?.[0];
    const service = { config_entry_id: entryId, kg: Number(data.get("kg")) };
    if (data.get("price")) service.price = Number(data.get("price"));
    if (data.get("date")) service.date = data.get("date");
    try {
      await this._hass.callService(DOMAIN, "add_delivery", service);
      this._showForm = false;
      this._err = "";
      this._msg = this._t("saved");
    } catch (e) {
      this._err = e?.message || String(e);
    }
    this._render();
  }
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

if (!customElements.get("pellet-stock-card")) {
  customElements.define("pellet-stock-card", PelletStockCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "pellet-stock-card",
    name: "Pellet Stock",
    description: "Silo, stock, range and deliveries of a pellet storage.",
    preview: true,
    documentationURL: "https://github.com/PXLJAKE/ha-pellet-stock",
  });
  console.info(`%c PELLET-STOCK-CARD %c ${VERSION} `, "background:#5a7d5a;color:#fff", "");
}

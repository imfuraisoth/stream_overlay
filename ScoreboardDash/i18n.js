// ── i18n: shared translation machinery ────────────────────────────
// Translations live in per-language files (lang/en.js, lang/ja.js, ...),
// each self-registering window.I18N.<code> = { ... }. This file holds only
// the logic: t(), language selection, and dynamic loading of the active
// language file.
//
// Load order on each page:
//   1. lang/en.js   (static -- the always-present fallback baseline)
//   2. i18n.js      (this file -- then it loads the active language itself)
// English is always loaded so t() never returns blank while another language
// file is still arriving.
//
// Language is stored in localStorage:
//   sc_lang          global UI language (operator pages + nav)
//   sc_lang_overlay  optional override for OVERLAY pages only
//
// Adding a language: create lang/<code>.js (copy en.js, translate), and add
// <code> to KNOWN_LANGS below so it appears in the picker.
(function () {
  window.I18N = window.I18N || {};

  // Languages offered in the picker. The file lang/<code>.js must exist.
  var KNOWN_LANGS = ["en", "ja"];

  var LANG_KEY = "sc_lang";
  var OVERLAY_LANG_KEY = "sc_lang_overlay";

  function getLang() { return localStorage.getItem(LANG_KEY) || "en"; }
  function getOverlayLang() { return localStorage.getItem(OVERLAY_LANG_KEY) || getLang(); }
  function activeLang() { return window.IS_OVERLAY ? getOverlayLang() : getLang(); }

  function t(key) {
    var lang = activeLang();
    var dict = window.I18N[lang];
    if (dict && dict[key] != null) return dict[key];
    var en = window.I18N.en;
    if (en && en[key] != null) return en[key];
    return key;
  }

  // Dynamically load a language file if it isn't already registered.
  // Calls cb() once available (or immediately if already present / English).
  var _loading = {};
  function ensureLang(code, cb) {
    cb = cb || function () {};
    if (!code || code === "en" || window.I18N[code]) { cb(); return; }
    if (_loading[code]) { _loading[code].push(cb); return; }
    _loading[code] = [cb];
    // Resolve path relative to where i18n.js was loaded from, so it works
    // from any page depth and on file://.
    var base = i18nBasePath();
    var s = document.createElement("script");
    s.src = base + "lang/" + code + ".js";
    s.onload = function () {
      (_loading[code] || []).forEach(function (fn) { try { fn(); } catch (e) {} });
      _loading[code] = null;
    };
    s.onerror = function () {
      console.log("i18n: could not load language file for '" + code + "', falling back to English");
      (_loading[code] || []).forEach(function (fn) { try { fn(); } catch (e) {} });
      _loading[code] = null;
    };
    (document.head || document.documentElement).appendChild(s);
  }

  // Figure out the directory i18n.js was served from (handles root vs
  // subfolder pages and file://). Falls back to "" (same dir).
  function i18nBasePath() {
    var scripts = document.getElementsByTagName("script");
    for (var i = 0; i < scripts.length; i++) {
      var src = scripts[i].getAttribute("src") || "";
      if (/(^|\/)i18n\.js(\?|$)/.test(src)) {
        return src.replace(/i18n\.js(\?.*)?$/, "");
      }
    }
    return "";
  }

  function setLang(code) {
    localStorage.setItem(LANG_KEY, code);
    ensureLang(code, function () {
      applyTranslations(document);
      if (typeof window.renderNav === "function") window.renderNav();
      if (typeof window.onLangChange === "function") window.onLangChange();
    });
  }
  function setOverlayLang(code) {
    if (code == null || code === "") localStorage.removeItem(OVERLAY_LANG_KEY);
    else localStorage.setItem(OVERLAY_LANG_KEY, code);
    ensureLang(code || getLang(), function () {
      applyTranslations(document);
      if (typeof window.onLangChange === "function") window.onLangChange();
    });
  }

  function applyTranslations(root) {
    root = root || document;
    var els = root.querySelectorAll("[data-i18n]");
    els.forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      if (key) el.textContent = t(key);
    });
    var attrEls = root.querySelectorAll("[data-i18n-attr]");
    attrEls.forEach(function (el) {
      el.getAttribute("data-i18n-attr").split(";").forEach(function (pair) {
        var bits = pair.split(":");
        if (bits.length === 2) el.setAttribute(bits[0].trim(), t(bits[1].trim()));
      });
    });
  }

  function availableLangs() { return KNOWN_LANGS.slice(); }

  window.t = t;
  window.getLang = getLang;
  window.getOverlayLang = getOverlayLang;
  window.setLang = setLang;
  window.setOverlayLang = setOverlayLang;
  window.applyTranslations = applyTranslations;
  window.availableLangs = availableLangs;
  window.ensureLang = ensureLang;
  window.langName = function (code) { return t("lang_" + code); };

  // On startup: ensure the active language file is loaded, then translate.
  function init() {
    ensureLang(activeLang(), function () {
      applyTranslations(document);
      // If the active language arrived asynchronously (non-English), let
      // pages that build UI in JS re-render now that strings are available.
      if (activeLang() !== "en" && typeof window.onLangChange === "function") {
        window.onLangChange();
      }
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
    // Also kick off the language-file load immediately (don't wait for DOM)
    ensureLang(activeLang(), function () {});
  } else {
    init();
  }
})();
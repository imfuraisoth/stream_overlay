// ── Language: English (en) ──────────────────────────────────────────────────
// Self-registering language file. Loaded as a plain <script> so it works
// on both http:// (operator pages) and file:// (OBS overlays) with no fetch.
// To add a new language, copy this file, change the code below, and translate
// the values. Keys missing here fall back to English (lang/en.js).
window.I18N = window.I18N || {};
window.I18N.en = {
      // language names (shown in the picker)
      lang_en: "English",
      lang_ja: "日本語 (Japanese)",

      // nav
      nav_commentators: "Commentators",
      nav_dashboard: "Event Dashboard",
      nav_top8: "Top 8",
      nav_crewbattle: "Crew Battle",
      nav_stations: "Stations",
      nav_players: "Players",
      nav_games: "Games & Assets",
      nav_imports: "Match Imports",

      // theme panel
      theme_title: "Theme",
      theme_presets: "Presets",
      theme_custom: "Custom Colors",
      theme_reset: "Reset to Default",
      lang_section: "Language",
      lang_ui: "Interface",
      lang_overlay: "Overlay",
      lang_overlay_follow: "Same as interface",

      // crew battle operator
      cb_status_loading: "Loading…",
      cb_status_loaded: "Loaded.",
      cb_status_saved: "Saved.",
      cb_status_savefail: "Save failed.",
      cb_status_loadfail: "Could not load.",
      cb_reset: "Reset Battle",
      cb_pagesize: "Page size",
      cb_captain_label: "Captain label",
      cb_vice_label: "Vice label",
      cb_back: "▲ Back",
      cb_advance: "Advance ▼",
      cb_add_player: "Add player…",
      cb_add: "Add",
      cb_page: "Page",
      cb_manual: "(manual)",
      cb_team1_default: "East",
      cb_team2_default: "West",
      cb_captain_default: "Captain",
      cb_vice_default: "Vice",
      cb_remaining: "remaining",
      cb_remaining_label: "Remaining label",
      cb_game: "Game",
      cb_game_pick: "-- pick game --",
      cb_character: "Character",
      cb_char_none: "-- none --",
      cb_pack: "Pack",
      cb_reset_confirm: "Reset the whole crew battle? This clears both rosters.",
      cb_hint: "The current player (highlighted) is who's up. Players above are defeated (dimmed on stream), players below are waiting. Use Advance \u25bc when the current player loses, or Back \u25b2 to undo. The last two players show the Captain / Vice role labels (editable per team) prefixed on stream. Reorder with the row \u25b2\u25bc; click a name to jump the current pointer to it. Changes save automatically.",

      // crew battle overlay
      cb_ov_left: "left",
};
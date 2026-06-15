// ── Language: Japanese (ja) -- FGC terms flagged for review ──────────────────────────────────────────────────
// Self-registering language file. Loaded as a plain <script> so it works
// on both http:// (operator pages) and file:// (OBS overlays) with no fetch.
// To add a new language, copy this file, change the code below, and translate
// the values. Keys missing here fall back to English (lang/en.js).
window.I18N = window.I18N || {};
window.I18N.ja = {
      lang_en: "English",
      lang_ja: "日本語 (Japanese)",

      // nav  -- FGC/tournament terms: VERIFY with a native speaker.
      // Several use katakana-ized English as is common in the JP FGC scene.
      nav_commentators: "実況",            // FLAG: "commentary/commentators"
      nav_dashboard: "ダッシュボード",
      nav_top8: "Top 8",                   // FLAG: often left as "Top 8" in JP FGC
      nav_crewbattle: "団体戦",            // FLAG: "team battle" -- crew battle
      nav_stations: "台",                  // FLAG: "stations/setups" -- 台 = cabinets
      nav_players: "プレイヤー",
      nav_games: "ゲーム・素材",           // FLAG: "games & assets"
      nav_imports: "大会インポート",       // FLAG: "tournament import"

      // theme panel
      theme_title: "テーマ",
      theme_presets: "プリセット",
      theme_custom: "カスタムカラー",
      theme_reset: "デフォルトに戻す",
      lang_section: "言語",
      lang_ui: "インターフェース",
      lang_overlay: "オーバーレイ",
      lang_overlay_follow: "インターフェースと同じ",

      // crew battle operator
      cb_status_loading: "読み込み中…",
      cb_status_loaded: "読み込み完了。",
      cb_status_saved: "保存しました。",
      cb_status_savefail: "保存に失敗しました。",
      cb_status_loadfail: "読み込めませんでした。",
      cb_reset: "リセット",
      cb_pagesize: "ページサイズ",
      cb_captain_label: "大将ラベル",      // FLAG: 大将 = captain/general (team battle term)
      cb_vice_label: "副将ラベル",         // FLAG: 副将 = vice-captain
      cb_back: "▲ 戻る",
      cb_advance: "次へ ▼",
      cb_add_player: "プレイヤーを追加…",
      cb_add: "追加",
      cb_page: "ページ",
      cb_manual: "（手動）",
      cb_team1_default: "東軍",            // FLAG: "East army" -- common in JP East-vs-West
      cb_team2_default: "西軍",            // FLAG: "West army"
      cb_captain_default: "大将",          // FLAG: captain (team-battle honorific)
      cb_vice_default: "副将",             // FLAG: vice-captain
      cb_remaining: "残り",
      cb_remaining_label: "残りラベル",
      cb_game: "ゲーム",
      cb_game_pick: "-- ゲームを選択 --",
      cb_character: "キャラクター",
      cb_char_none: "-- なし --",
      cb_pack: "パック",
      cb_reset_confirm: "団体戦をリセットしますか？両チームの登録選手が消去されます。",
      cb_hint: "ハイライトされている選手が現在の出場者です。上の選手は敗退（配信では薄く表示）、下の選手は待機中です。現在の選手が敗れたら「次へ \u25bc」、取り消すには「戻る \u25b2」を使います。最後の2人には大将・副将のラベル（チームごとに編集可）が配信で表示されます。\u25b2\u25bc で並び替え、名前をクリックすると現在位置がそこに移動します。変更は自動保存されます。",

      cb_ov_left: "残り",
};
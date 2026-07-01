// ── SHARED NAVBAR ─────────────────────────────────────────────────
// Single source of truth for the operator-page navbar. Each page has a
// <div id="nav-root"></div> placeholder and loads this script. The nav is
// built here: order, labels, paths, and the active-item highlight are all
// computed in one place, so nav changes only happen in this file.
//
// i18n-ready: labels are looked up via window.t(key) when an i18n system is
// present, otherwise the English fallback in each item is used.
(function () {
  // Nav items in display order. Each: key (used for active match + i18n),
  // label fallback (English), and path relative to the site root.
  var ITEMS = [
    { key: 'commentators', label: 'Commentators',     path: 'commentators/commentators.html' },
    { key: 'index',        label: 'Event Dashboard',  path: 'index.html' },
    { key: 'top8',         label: 'Top 8',            path: 'top8/top8.html' },
    { key: 'crewbattle',   label: 'Crew Battle',      path: 'crewbattle/crewbattle.html' },
    { key: 'stations',     label: 'Stations',         path: 'stations/stations.html' },
    { key: 'players',      label: 'Players',          path: 'players/players.html' },
    { key: 'games',        label: 'Games & Assets',   path: 'playerinfo/characterselect.html' },
    { key: 'imports',      label: 'Match Imports',    path: 'imports/imports.html' },
    { key: 'seeding',      label: 'Seeding',          path: 'seeding/seeding.html' },
    { key: 'backup',       label: 'Data Backup',      path: 'backup/backup.html' }
  ];

  // i18n key per item (only used if window.t exists). Kept separate so the
  // string-table can name them however it likes.
  var I18N_KEYS = {
    commentators: 'nav_commentators', index: 'nav_dashboard', top8: 'nav_top8',
    crewbattle: 'nav_crewbattle', stations: 'nav_stations', players: 'nav_players',
    games: 'nav_games', imports: 'nav_imports', seeding: 'nav_seeding', backup: 'nav_backup'
  };

  function label(item) {
    if (typeof window.t === 'function') {
      var s = window.t(I18N_KEYS[item.key]);
      // t() should fall back to English itself; guard against it returning the
      // raw key if the string is missing.
      if (s && s !== I18N_KEYS[item.key]) return s;
    }
    return item.label;
  }

  // Determine how deep this page is, to build correct relative paths.
  // Root page (index.html) is at depth 0; every other page lives one folder
  // deep, so it needs a '../' prefix to reach the site root.
  function rootPrefix() {
    var path = location.pathname;
    // Normalize: strip the trailing filename
    var segs = path.split('/').filter(Boolean);
    // last segment is the .html file; the rest are folders under the app root.
    // app root contains index.html, so depth = number of folders below root.
    // We can't know the app's mount point reliably, so detect by filename:
    var file = segs.length ? segs[segs.length - 1] : '';
    // If we're at index.html (or '/' ), we're at root.
    if (file === '' || file === 'index.html') {
      // But index.html could be served at '/', so treat as root.
      // Exception: if index.html is itself inside a folder (not the app root),
      // that's not a case this app has.
      return '';
    }
    return '../';
  }

  // Identify the active item by matching the current filename to an item path.
  function activeKey() {
    var file = location.pathname.split('/').filter(Boolean).pop() || 'index.html';
    // match against the filename portion of each item's path
    for (var i = 0; i < ITEMS.length; i++) {
      var itemFile = ITEMS[i].path.split('/').pop();
      if (itemFile === file) return ITEMS[i].key;
    }
    // default: if at '/', it's the dashboard
    if (file === '' ) return 'index';
    return null;
  }

  function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  function build() {
    var prefix = rootPrefix();
    var active = activeKey();
    // Hamburger toggle (shown only on narrow widths via CSS) + a collapsible
    // items wrapper. On wide screens the wrapper is a normal inline row; on
    // narrow screens it becomes a dropdown toggled by the .nav-open class.
    var html = '<div class="top-navbar-container">';
    html += '<button class="nav-hamburger" aria-label="Menu" aria-expanded="false" onclick="window.toggleNavMenu()">\u2630</button>';
    html += '<div class="nav-items">';
    ITEMS.forEach(function (item, i) {
      if (item.key === active) {
        html += '<div class="header-item active">' + esc(label(item)) + '</div>';
      } else {
        html += '<div class="header-item"><a href="' + prefix + item.path + '">' + esc(label(item)) + '</a></div>';
      }
      if (i < ITEMS.length - 1) html += '<span class="header-sep">|</span>';
    });
    html += '</div>';   // .nav-items
    html += '</div>';   // .top-navbar-container
    return html;
  }

  // Toggle the dropdown open/closed on narrow widths.
  window.toggleNavMenu = function () {
    var c = document.querySelector('.top-navbar-container');
    var h = document.querySelector('.nav-hamburger');
    if (!c) return;
    var open = c.classList.toggle('nav-open');
    if (h) h.setAttribute('aria-expanded', open ? 'true' : 'false');
  };

  function render() {
    var root = document.getElementById('nav-root');
    if (!root) return;
    root.innerHTML = build();
    // The nav container is rebuilt from scratch here, which wipes anything
    // else injected into it (e.g. the theme button). Let listeners re-add.
    if (typeof window.onNavRendered === 'function') window.onNavRendered();
  }

  // Reserve the navbar's height up front so the page doesn't shift when the
  // nav injects. The navbar is 44px tall + 1px bottom border = 45px. We set
  // this as a min-height on the placeholder via an injected style rule (kept
  // here so the whole nav concern lives in one file). Once the real nav fills
  // the placeholder it occupies the same space, so there's no jump.
  function reserveSpace() {
    if (document.getElementById('nav-reserve-style')) return;
    var st = document.createElement('style');
    st.id = 'nav-reserve-style';
    // min-height (not height) so a wrapped two-row nav on narrow widths can
    // still grow rather than clip.
    st.textContent = '#nav-root { min-height: 45px; }';
    (document.head || document.documentElement).appendChild(st);
  }
  reserveSpace();

  // Expose a re-render hook so a language switch can rebuild the nav live.
  window.renderNav = render;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();
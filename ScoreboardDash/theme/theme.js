// ── THEME SYSTEM ──────────────────────────────────────────────────
// Apply saved theme immediately (called inline in <head> to prevent flash)
(function applyThemeEarly() {
    var saved = localStorage.getItem('sc_theme');
    if (!saved) return;
    try {
        var vars = JSON.parse(saved);
        var root = document.documentElement;
        Object.keys(vars).forEach(function(k) { root.style.setProperty(k, vars[k]); });
    } catch(e) {}
})();

var THEMES = {
    'HitConfirm Dark': {
        '--bg':      '#0e0d0b', '--bg2':    '#181714',
        '--bg3':     '#222018', '--bg4':    '#2c2a20',
        '--fg':      '#f0ece0', '--fg2':    '#9a9280',
        '--accent':  '#e8a020', '--accent2':'#c43030',
        '--green':   '#3aaa5c', '--blue':   '#2a7fd4',
        '--p1-color':'#c43030', '--p2-color':'#2a7fd4',
        '--p1-color':'#f43f5e', '--p2-color':'#38bdf8',
        '--p1-color':'#f87171', '--p2-color':'#58a6ff',
        '--p1-color':'#e8192c', '--p2-color':'#2a9fd4',
        '--p1-color':'#f87171', '--p2-color':'#86efac',
        '--purple':  '#8b5cf6', '--border': '#333028'
    },
    'Midnight Blue': {
        '--bg':      '#09090f', '--bg2':    '#10101a',
        '--bg3':     '#181825', '--bg4':    '#20202f',
        '--fg':      '#e8eaf6', '--fg2':    '#7880a0',
        '--accent':  '#38bdf8', '--accent2':'#f43f5e',
        '--green':   '#34d399', '--blue':   '#818cf8',
        '--purple':  '#a78bfa', '--border': '#2a2a40'
    },
    'Slate': {
        '--bg':      '#0d1117', '--bg2':    '#161b22',
        '--bg3':     '#1f2430', '--bg4':    '#282f3e',
        '--fg':      '#cdd9e5', '--fg2':    '#768390',
        '--accent':  '#2dd4bf', '--accent2':'#f87171',
        '--green':   '#3fb950', '--blue':   '#58a6ff',
        '--purple':  '#bc8cff', '--border': '#30363d'
    },
    'Blood Orange': {
        '--bg':      '#0d0a09', '--bg2':    '#171210',
        '--bg3':     '#201916', '--bg4':    '#2a211d',
        '--fg':      '#f0e8e0', '--fg2':    '#9a8070',
        '--accent':  '#f4622a', '--accent2':'#e8192c',
        '--green':   '#4caf50', '--blue':   '#2a9fd4',
        '--purple':  '#c084fc', '--border': '#3a2820'
    },
    'Forest': {
        '--bg':      '#090d0a', '--bg2':    '#101810',
        '--bg3':     '#162018', '--bg4':    '#1d2820',
        '--fg':      '#e0f0e0', '--fg2':    '#7a9a80',
        '--accent':  '#86efac', '--accent2':'#f87171',
        '--green':   '#4ade80', '--blue':   '#38bdf8',
        '--purple':  '#c084fc', '--border': '#243028'
    }
};

var THEME_VAR_LABELS = {
    '--bg':      'Background',
    '--bg2':     'Surface',
    '--bg3':     'Raised',
    '--bg4':     'Elevated',
    '--fg':      'Text',
    '--fg2':     'Muted Text',
    '--accent':  'Accent',
    '--accent2': 'Danger',
    '--green':   'Green',
    '--p1-color':'P1 Accent',
    '--p2-color':'P2 Accent',
    '--border':  'Border'
};

function getCurrentVars() {
    var style = getComputedStyle(document.documentElement);
    var vars = {};
    Object.keys(THEME_VAR_LABELS).forEach(function(k) {
        vars[k] = style.getPropertyValue(k).trim();
    });
    return vars;
}

function applyVars(vars) {
    var root = document.documentElement;
    Object.keys(vars).forEach(function(k) { root.style.setProperty(k, vars[k]); });
}

function saveTheme(vars) {
    // Save all vars including ones not in the customizer
    var style = getComputedStyle(document.documentElement);
    var full = {};
    ['--bg','--bg2','--bg3','--bg4','--fg','--fg2','--accent','--accent2',
     '--green','--blue','--purple','--p1-color','--p2-color','--border'].forEach(function(k) {
        full[k] = style.getPropertyValue(k).trim();
    });
    // Override with provided vars
    Object.assign(full, vars);
    localStorage.setItem('sc_theme', JSON.stringify(full));
}

function applyPreset(name) {
    var preset = THEMES[name];
    if (!preset) return;
    applyVars(preset);
    saveTheme(preset);
    renderPickers();
    // Highlight active preset button
    document.querySelectorAll('.theme-preset-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.preset === name);
    });
}

function renderPickers() {
    var container = document.getElementById('theme-pickers');
    if (!container) return;
    var style = getComputedStyle(document.documentElement);
    container.innerHTML = Object.keys(THEME_VAR_LABELS).map(function(k) {
        var val = style.getPropertyValue(k).trim();
        return '<div class="theme-picker-row">' +
            '<label>' + THEME_VAR_LABELS[k] + '</label>' +
            '<input type="color" data-var="' + k + '" value="' + val + '" ' +
            'oninput="onPickerChange(this)">' +
            '</div>';
    }).join('');
}

function onPickerChange(input) {
    var k = input.dataset.var;
    document.documentElement.style.setProperty(k, input.value);
    // Clear active preset since we're customizing
    document.querySelectorAll('.theme-preset-btn').forEach(function(btn) {
        btn.classList.remove('active');
    });
    // Save after a short debounce
    clearTimeout(window._themeDebounce);
    window._themeDebounce = setTimeout(function() {
        var vars = {};
        vars[k] = input.value;
        saveTheme(vars);
    }, 300);
}

function resetTheme() {
    localStorage.removeItem('sc_theme');
    applyPreset('HitConfirm Dark');
}

// ── LANGUAGE PICKER ───────────────────────────────────────────────
function populateLangSelects() {
    if (typeof window.availableLangs !== 'function') return;  // i18n.js not loaded
    var langs = window.availableLangs();
    var ui = document.getElementById('lang-ui-select');
    if (ui) {
        ui.innerHTML = langs.map(function(c) {
            return '<option value="' + c + '">' + window.langName(c) + '</option>';
        }).join('');
        ui.value = window.getLang();
    }
}
function onUiLangChange(code) {
    if (typeof window.setLang === 'function') window.setLang(code);
    populateLangSelects();  // refresh labels (now in the new language)
}

function toggleThemePanel() {
    var panel = document.getElementById('theme-panel');
    if (!panel) return;
    var open = panel.classList.toggle('open');
    if (open) renderPickers();
}

// Inject the gear button into the nav. Idempotent: safe to call repeatedly
// (e.g. after nav.js rebuilds the navbar, which would otherwise wipe it).
function ensureThemeButton() {
    var nav = document.querySelector('.top-navbar-container');
    if (!nav) return;
    if (nav.querySelector('.theme-nav-btn')) return;  // already there
    var btn = document.createElement('button');
    btn.className = 'theme-nav-btn';
    btn.title = 'Customize theme';
    btn.textContent = 'Theme';
    btn.onclick = toggleThemePanel;
    // Prefer the collapsible items wrapper so the button folds into the
    // hamburger dropdown on narrow widths; fall back to the nav container.
    var host = nav.querySelector('.nav-items') || nav;
    host.appendChild(btn);
}

// nav.js calls this after it rebuilds the navbar -- re-add our button.
window.onNavRendered = ensureThemeButton;

// Build the panel HTML and inject into body
document.addEventListener('DOMContentLoaded', function() {
    ensureThemeButton();

    // Build panel
    var panel = document.createElement('div');
    panel.id = 'theme-panel';
    panel.innerHTML =
        '<div class="theme-panel-header">' +
            '<span class="theme-panel-title" data-i18n="theme_title">Theme</span>' +
            '<button class="theme-panel-close" onclick="toggleThemePanel()">×</button>' +
        '</div>' +
        '<div class="theme-panel-body">' +
            '<div class="theme-section-label" data-i18n="lang_section">Language</div>' +
            '<div class="theme-lang-row">' +
                '<label data-i18n="lang_ui">Interface</label>' +
                '<select id="lang-ui-select" onchange="onUiLangChange(this.value)"></select>' +
            '</div>' +
            '<div class="theme-section-label" style="margin-top:14px;" data-i18n="theme_presets">Presets</div>' +
            '<div class="theme-presets">' +
                Object.keys(THEMES).map(function(name) {
                    var t = THEMES[name];
                    return '<button class="theme-preset-btn" data-preset="' + name + '" ' +
                        'onclick="applyPreset(\'' + name.replace(/'/g, "\\'") + '\')" ' +
                        'style="--p-accent:' + t['--accent'] + ';--p-bg:' + t['--bg2'] + ';--p-border:' + t['--border'] + '">' +
                        '<span class="theme-preset-swatch"></span>' +
                        name + '</button>';
                }).join('') +
            '</div>' +
            '<div class="theme-section-label" style="margin-top:14px;" data-i18n="theme_custom">Custom Colors</div>' +
            '<div id="theme-pickers"></div>' +
            '<button class="theme-reset-btn" onclick="resetTheme()" data-i18n="theme_reset">Reset to Default</button>' +
        '</div>';
    document.body.appendChild(panel);

    // Mark active preset if any
    renderPickers();
    // Language picker: fill the selects and translate the panel's own labels.
    populateLangSelects();
    if (typeof window.applyTranslations === 'function') window.applyTranslations(panel);
    var saved = localStorage.getItem('sc_theme');
    if (saved) {
        try {
            var savedVars = JSON.parse(saved);
            Object.keys(THEMES).forEach(function(name) {
                var preset = THEMES[name];
                var match = Object.keys(preset).every(function(k) {
                    return !savedVars[k] || savedVars[k] === preset[k];
                });
                if (match) {
                    var btn = document.querySelector('[data-preset="' + name + '"]');
                    if (btn) btn.classList.add('active');
                }
            });
        } catch(e) {}
    } else {
        var defaultBtn = document.querySelector('[data-preset="HitConfirm Dark"]');
        if (defaultBtn) defaultBtn.classList.add('active');
    }

    // Close panel on outside click
    document.addEventListener('click', function(e) {
        var panel = document.getElementById('theme-panel');
        if (!panel || !panel.classList.contains('open')) return;
        if (!panel.contains(e.target) && !e.target.classList.contains('theme-nav-btn')) {
            panel.classList.remove('open');
        }
    });
});
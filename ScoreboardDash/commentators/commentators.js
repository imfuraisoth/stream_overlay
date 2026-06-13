const PLATFORM_ICONS = {
    twitter:   '../resources/twitter.png',
    bluesky:   '../resources/bsky.png',
    instagram: '../resources/instagram.png',
    facebook:  '../resources/facebook.png',
    twitch:    '../resources/twitch.png',
};
const PLATFORM_COLORS = { twitter: '#1d9bf0', bluesky: '#0085ff', instagram: '#e1306c', facebook: '#1877f2', twitch: '#9146ff' };

// ── NAME PICKERS ──────────────────────────────────────────────────
function populateComPickers(names) {
    // Populate select pickers
    document.querySelectorAll('select.name-picker').forEach(function(sel) {
        var existing = new Set(Array.from(sel.options).map(function(o) { return o.value; }).filter(Boolean));
        names.forEach(function(name) {
            if (name && !existing.has(name)) {
                var opt = document.createElement('option');
                opt.value = name; opt.textContent = name;
                sel.appendChild(opt);
            }
        });
    });
    // Also populate datalist for typing autocomplete
    var dl = document.getElementById('com_name_suggestions');
    if (dl) {
        var existing = new Set(Array.from(dl.options).map(function(o) { return o.value; }));
        names.forEach(function(name) {
            if (name && !existing.has(name)) {
                var opt = document.createElement('option');
                opt.value = name; dl.appendChild(opt);
            }
        });
    }
}

function pickName(inputId, sel, updateFn) {
    if (!sel.value) return;
    var input = document.getElementById(inputId);
    if (input) input.value = sel.value;
    sel.selectedIndex = 0;
    if (updateFn) updateFn();
}

// ── LOCAL PLAYER DB ───────────────────────────────────────────────
function _nameKeyedMap() {
    var m = new Map();
    function norm(k) { return String(k).trim().toLowerCase(); }
    return {
        get: function(k) { return k ? m.get(norm(k)) : undefined; },
        set: function(k, v) { if (k) m.set(norm(k), v); return this; },
        has: function(k) { return k ? m.has(norm(k)) : false; },
        clear: function() { m.clear(); },
        forEach: function(cb) { m.forEach(cb); },
        get size() { return m.size; }
    };
}

var _localPlayersMap = _nameKeyedMap(); // normalized name/alias -> player record
var jsonData = {};

function setPlatformSelect(selId, platform) {
    var sel = document.getElementById(selId);
    if (sel) sel.value = platform || '';
    // Update adjacent icon img if present
    var wrap = sel ? sel.closest('.social-preview-row') : null;
    var icon = wrap ? wrap.querySelector('.platform-icon-img') : null;
    if (icon) {
        if (platform && PLATFORM_ICONS[platform]) {
            icon.src = PLATFORM_ICONS[platform];
            icon.style.display = 'inline';
        } else {
            icon.style.display = 'none';
        }
    }
}

function loadLocalPlayers() {
    fetch('/getCommentatorPlayers')
        .then(function(r) { return r.json(); })
        .then(function(players) {
            if (!players || !players.length) return;
            players.forEach(function(p) {
                if (p && p.name) {
                    _localPlayersMap.set(p.name, p);
                    (p.aliases || []).forEach(function(a) { _localPlayersMap.set(a, p); });
                }
            });
            populateComPickers(players.map(function(p) { return p.name; }));
        })
        .catch(function(e) { console.log('loadLocalPlayers error:', e); });
}

// ── DATA LOAD ─────────────────────────────────────────────────────
function getDataFromServer() {
    fetch('/getdata')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            jsonData = data;
            if (!jsonData.com1Plat) jsonData.com1Plat = '';
            if (!jsonData.com2Plat) jsonData.com2Plat = '';
            updateElement('form_name_1',   data.com1);
            updateElement('form_name_2',   data.com2);
            updateElement('form_social_1', data.soc1);
            updateElement('form_social_2', data.soc2);
            // Restore platform badges from local DB
            var p1 = _localPlayersMap.get(data.com1);
            var p2 = _localPlayersMap.get(data.com2);
            setPlatformSelect('soc1_platform_sel', p1 ? (p1.social_platform || '') : '');
            setPlatformSelect('soc2_platform_sel', p2 ? (p2.social_platform || '') : '');
        })
        .catch(function(e) { console.log('getDataFromServer error:', e); });
}

function updateElement(id, value) {
    var el = document.getElementById(id);
    if (el && value !== undefined) el.value = value;
}

// ── SEND ──────────────────────────────────────────────────────────
function sendJSON() {
    fetch('/updatecommdata', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(jsonData)
    }).catch(function(e) { console.log('sendJSON error:', e); });
}

function sendJsonDataToEndpoint(data, endpoint) {
    fetch('/' + endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).catch(function(e) { console.log('sendJsonDataToEndpoint error:', e); });
}

// ── UPDATE FUNCTIONS ──────────────────────────────────────────────

function updateCom1() {
    jsonData.com1 = document.getElementById('form_name_1').value;
    var p = _localPlayersMap.get(jsonData.com1);
    if (p) {
        jsonData.soc1 = p.social_handle || '';
        document.getElementById('form_social_1').value = p.social_handle || '';
        setPlatformSelect('soc1_platform_sel', p.social_platform || '');
        jsonData.com1Plat = p.social_platform || '';
    } else {
        jsonData.soc1 = '';
        document.getElementById('form_social_1').value = '';
        setPlatformSelect('soc1_platform_sel', '');
        jsonData.com1Plat = '';
    }
    updateComHint(1);
    sendJSON();
}

function updateCom2() {
    jsonData.com2 = document.getElementById('form_name_2').value;
    var p = _localPlayersMap.get(jsonData.com2);
    if (p) {
        jsonData.soc2 = p.social_handle || '';
        document.getElementById('form_social_2').value = p.social_handle || '';
        setPlatformSelect('soc2_platform_sel', p.social_platform || '');
        jsonData.com2Plat = p.social_platform || '';
    } else {
        jsonData.soc2 = '';
        document.getElementById('form_social_2').value = '';
        setPlatformSelect('soc2_platform_sel', '');
        jsonData.com2Plat = '';
    }
    updateComHint(2);
    sendJSON();
}

function updateSoc1() {
    jsonData.soc1 = document.getElementById('form_social_1').value;
    updateComHint(1);
    sendJSON();
}

function updateSoc2() {
    jsonData.soc2 = document.getElementById('form_social_2').value;
    updateComHint(2);
    sendJSON();
}

function updatePlatform1() {
    var platform = document.getElementById('soc1_platform_sel').value;
    var existing = _localPlayersMap.get(jsonData.com1) || {};
    existing.social_platform = platform;
    if (jsonData.com1) _localPlayersMap.set(jsonData.com1, existing);
    jsonData.com1Plat = platform;
    updateComHint(1);
    sendJSON();
}

function updatePlatform2() {
    var platform = document.getElementById('soc2_platform_sel').value;
    var existing = _localPlayersMap.get(jsonData.com2) || {};
    existing.social_platform = platform;
    if (jsonData.com2) _localPlayersMap.set(jsonData.com2, existing);
    jsonData.com2Plat = platform;
    updateComHint(2);
    sendJSON();
}

function clearCom1() {
    document.getElementById('form_name_1').value   = '';
    document.getElementById('form_social_1').value = '';
    setPlatformSelect('soc1_platform_sel', '');
    jsonData.com1 = ''; jsonData.soc1 = ''; jsonData.com1Plat = '';
    sendJSON();
}

function clearCom2() {
    document.getElementById('form_name_2').value   = '';
    document.getElementById('form_social_2').value = '';
    setPlatformSelect('soc2_platform_sel', '');
    jsonData.com2 = ''; jsonData.soc2 = ''; jsonData.com2Plat = '';
    sendJSON();
}

function reverseCommentatorNames() {
    var c1 = document.getElementById('form_name_1').value;
    var c2 = document.getElementById('form_name_2').value;
    var s1 = document.getElementById('form_social_1').value;
    var s2 = document.getElementById('form_social_2').value;
    var p1 = document.getElementById('soc1_platform_sel').value;
    var p2 = document.getElementById('soc2_platform_sel').value;
    document.getElementById('form_name_1').value   = c2;
    document.getElementById('form_name_2').value   = c1;
    document.getElementById('form_social_1').value = s2;
    document.getElementById('form_social_2').value = s1;
    setPlatformSelect('soc1_platform_sel', p2);
    setPlatformSelect('soc2_platform_sel', p1);
    jsonData.com1 = c2; jsonData.com2 = c1;
    jsonData.soc1 = s2; jsonData.soc2 = s1;
    sendJSON();
}

// ── INIT ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    // Load all players into _localPlayersMap for social lookups,
    // then load commentator-flagged players into the pickers/datalist,
    // then fetch current scoreboard data.
    fetch('/getLocalPlayers')
        .then(function(r) { return r.json(); })
        .then(function(players) {
            if (players && players.length) {
                players.forEach(function(p) {
                if (p && p.name) {
                    _localPlayersMap.set(p.name, p);
                    (p.aliases || []).forEach(function(a) { _localPlayersMap.set(a, p); });
                }
            });
            }
            // Now load only commentator-flagged players into the pickers
            return fetch('/getCommentatorPlayers');
        })
        .then(function(r) { return r.json(); })
        .then(function(comPlayers) {
            if (comPlayers && comPlayers.length) {
                var names = comPlayers.map(function(p) { return p.name; });
                populateComPickers(names);
            }
            // Now fetch scoreboard — _localPlayersMap is ready
            return fetch('/getdata');
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            jsonData = data;
            if (!jsonData.com1Plat) jsonData.com1Plat = '';
            if (!jsonData.com2Plat) jsonData.com2Plat = '';
            updateElement('form_name_1',   data.com1);
            updateElement('form_name_2',   data.com2);
            updateElement('form_social_1', data.soc1);
            updateElement('form_social_2', data.soc2);
            var p1 = _localPlayersMap.get(data.com1);
            var p2 = _localPlayersMap.get(data.com2);
            setPlatformSelect('soc1_platform_sel', p1 ? (p1.social_platform || '') : '');
            setPlatformSelect('soc2_platform_sel', p2 ? (p2.social_platform || '') : '');
        })
        .catch(function(e) { console.log('init error:', e); });
});

// ── LIVE SYNC ────────────────────────────────────────────────────
if (window.liveSync) {
    liveSync.on('players', function() {
        loadLocalPlayers();
    });
}


// ════════════════════════════════════════════════════════════════
// EXPLICIT COMMENTATOR SAVE
// ════════════════════════════════════════════════════════════════
function updateComHint(n) {
    var el = document.getElementById('com' + n + 'MatchHint');
    if (!el) return;
    var name = (jsonData['com' + n] || '').trim();
    if (!name) { el.textContent = ''; el.className = 'player-match-hint'; return; }
    var rec = _localPlayersMap.get(name);
    if (rec && rec.id) {
        el.textContent = '\u2192 ' + rec.name + (rec.is_commentator ? '' : ' (not flagged commentator yet)');
        el.className = 'player-match-hint matched';
    } else {
        el.textContent = 'not in player DB';
        el.className = 'player-match-hint unmatched';
    }
}

function saveCommentatorCard(n) {
    var name = (jsonData['com' + n] || '').trim();
    if (!name) return;
    var body = {
        name: name,
        social_handle: jsonData['soc' + n] || '',
        social_platform: document.getElementById('soc' + n + '_platform_sel').value || '',
        is_commentator: true
    };
    var btn = document.getElementById('com' + n + 'SaveBtn');
    fetch('/saveLocalPlayer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    }).then(function(r) {
        if (!r.ok) throw new Error(r.status);
        if (btn) {
            btn.textContent = '\u2713 Saved';
            setTimeout(function() { btn.textContent = 'Save Commentator'; }, 1600);
        }
        updateComHint(n);
    }).catch(function(e) {
        console.log('saveCommentatorCard error:', e);
        if (btn) {
            btn.textContent = 'Save failed';
            setTimeout(function() { btn.textContent = 'Save Commentator'; }, 2000);
        }
    });
}
// ── LOCAL PLAYER DB ───────────────────────────────────────────────
var _localPlayersMap = new Map();
var jsonData = {};

function setPlatformSelect(selId, platform) {
    var sel = document.getElementById(selId);
    if (sel) sel.value = platform || '';
}

function loadLocalPlayers() {
    fetch('/getLocalPlayers')
        .then(function(r) { return r.json(); })
        .then(function(players) {
            if (!players || !players.length) return;
            players.forEach(function(p) { if (p && p.name) _localPlayersMap.set(p.name, p); });
            var dl = document.getElementById('com_name_suggestions');
            if (!dl) return;
            var existing = new Set(Array.from(dl.options).map(function(o) { return o.value; }));
            players.forEach(function(p) {
                var n = p.name;
                if (n && !existing.has(n)) {
                    var opt = document.createElement('option'); opt.value = n; dl.appendChild(opt);
                }
            });
        })
        .catch(function(e) { console.log('loadLocalPlayers error:', e); });
}

// ── DATA LOAD ─────────────────────────────────────────────────────
function getDataFromServer() {
    fetch('/getdata')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            jsonData = data;
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
function saveCommentatorToDb(name, social_handle, social_platform) {
    if (!name || !name.trim()) return;
    var existing = _localPlayersMap.get(name.trim()) || {};
    fetch('/saveLocalPlayer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: name.trim(),
            social_handle: social_handle || existing.social_handle || '',
            social_platform: social_platform !== undefined ? social_platform : (existing.social_platform || ''),
            team: existing.team || '',
            country: existing.country || ''
        })
    }).then(function() {
        existing.name = name.trim();
        if (social_handle) existing.social_handle = social_handle;
        _localPlayersMap.set(name.trim(), existing);
        // Add to datalist if new
        var dl = document.getElementById('com_name_suggestions');
        if (dl) {
            var existing_names = new Set(Array.from(dl.options).map(function(o) { return o.value; }));
            if (!existing_names.has(name.trim())) {
                var opt = document.createElement('option'); opt.value = name.trim(); dl.appendChild(opt);
            }
        }
    }).catch(function(e) { console.log('saveCommentatorToDb error:', e); });
}

function updateCom1() {
    jsonData.com1 = document.getElementById('form_name_1').value;
    var p = _localPlayersMap.get(jsonData.com1);
    if (p) {
        if (p.social_handle) {
            jsonData.soc1 = p.social_handle;
            document.getElementById('form_social_1').value = p.social_handle;
        }
        setPlatformSelect('soc1_platform_sel', p.social_platform || '');
    } else {
        setPlatformSelect('soc1_platform_sel', '');
    }
    saveCommentatorToDb(jsonData.com1, jsonData.soc1, document.getElementById('soc1_platform_sel').value);
    sendJSON();
}

function updateCom2() {
    jsonData.com2 = document.getElementById('form_name_2').value;
    var p = _localPlayersMap.get(jsonData.com2);
    if (p) {
        if (p.social_handle) {
            jsonData.soc2 = p.social_handle;
            document.getElementById('form_social_2').value = p.social_handle;
        }
        setPlatformSelect('soc2_platform_sel', p.social_platform || '');
    } else {
        setPlatformSelect('soc2_platform_sel', '');
    }
    saveCommentatorToDb(jsonData.com2, jsonData.soc2, document.getElementById('soc2_platform_sel').value);
    sendJSON();
}

function updateSoc1() {
    jsonData.soc1 = document.getElementById('form_social_1').value;
    saveCommentatorToDb(jsonData.com1, jsonData.soc1, document.getElementById('soc1_platform_sel').value);
    sendJSON();
}

function updateSoc2() {
    jsonData.soc2 = document.getElementById('form_social_2').value;
    saveCommentatorToDb(jsonData.com2, jsonData.soc2);
    sendJSON();
}

function updatePlatform1() {
    var platform = document.getElementById('soc1_platform_sel').value;
    var existing = _localPlayersMap.get(jsonData.com1) || {};
    existing.social_platform = platform;
    if (jsonData.com1) _localPlayersMap.set(jsonData.com1, existing);
    saveCommentatorToDb(jsonData.com1, jsonData.soc1, platform);
}

function updatePlatform2() {
    var platform = document.getElementById('soc2_platform_sel').value;
    var existing = _localPlayersMap.get(jsonData.com2) || {};
    existing.social_platform = platform;
    if (jsonData.com2) _localPlayersMap.set(jsonData.com2, existing);
    saveCommentatorToDb(jsonData.com2, jsonData.soc2, platform);
}

function clearCom1() {
    document.getElementById('form_name_1').value   = '';
    document.getElementById('form_social_1').value = '';
    setPlatformSelect('soc1_platform_sel', '');
    jsonData.com1 = ''; jsonData.soc1 = '';
    sendJSON();
}

function clearCom2() {
    document.getElementById('form_name_2').value   = '';
    document.getElementById('form_social_2').value = '';
    setPlatformSelect('soc2_platform_sel', '');
    jsonData.com2 = ''; jsonData.soc2 = '';
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
    // Load local players first, then fetch current scoreboard data
    // so _localPlayersMap is ready when we try to look up platform badges
    fetch('/getLocalPlayers')
        .then(function(r) { return r.json(); })
        .then(function(players) {
            if (players && players.length) {
                players.forEach(function(p) { if (p && p.name) _localPlayersMap.set(p.name, p); });
                var dl = document.getElementById('com_name_suggestions');
                if (dl) {
                    var existing = new Set(Array.from(dl.options).map(function(o) { return o.value; }));
                    players.forEach(function(p) {
                        if (p.name && !existing.has(p.name)) {
                            var opt = document.createElement('option'); opt.value = p.name; dl.appendChild(opt);
                        }
                    });
                }
            }
            // Now fetch scoreboard — _localPlayersMap is ready
            return fetch('/getdata');
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            jsonData = data;
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
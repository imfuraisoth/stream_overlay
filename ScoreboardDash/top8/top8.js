// ── NAME PICKERS ──────────────────────────────────────────────────
function rebuildT8NamePickers() {
    var source = localStorage.getItem('player_source') || 'both';
    var names = [];
    if (source === 'startgg' || source === 'both') {
        playersMap.forEach(function(_, name) { names.push(name); });
    }
    if (source === 'local' || source === 'both') {
        var _seen = new Set();
        _localPlayersByName.forEach(function(p) {
            if (p && p.name && !_seen.has(p.name)) { _seen.add(p.name); names.push(p.name); }
        });
    }
    names = names.filter(function(v,i,a) { return a.indexOf(v) === i; });
    names.sort(function(a,b) { return a.toLowerCase().localeCompare(b.toLowerCase()); });
    // Populate select pickers
    document.querySelectorAll('select.name-picker').forEach(function(sel) {
        sel.innerHTML = '<option value="">▾</option>';
        names.forEach(function(name) {
            var opt = document.createElement('option');
            opt.value = name; opt.textContent = name;
            sel.appendChild(opt);
        });
    });
    // Populate datalist for typing autocomplete
    var dl = document.getElementById('next_player_suggestions');
    if (dl) {
        dl.innerHTML = '';
        names.forEach(function(name) {
            var opt = document.createElement('option');
            opt.value = name; dl.appendChild(opt);
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

function pickBracketName(inputId, sel) {
    if (!sel.value) return;
    var input = document.getElementById(inputId);
    if (!input) { sel.selectedIndex = 0; return; }
    input.value = sel.value;
    sel.selectedIndex = 0;
    // Fire the input's onchange
    var evt = document.createEvent('Event');
    evt.initEvent('change', true, true);
    input.dispatchEvent(evt);
}

// Safe element helper — silently skips missing IDs from old SVG layout
// Maps old button IDs to new equivalents
const _idAliases = {
    'rectangle_button_18': 'button_start_top8',
};
function safeEl(id) {
    const mapped = _idAliases[id] || id;
    return document.getElementById(mapped) || { value: '', style: {}, innerText: '', textContent: '' };
}

var jsonData;
var lastRoundSuffix = [];
var lastNextRoundSuffix = [];

var roundSuffixMap = {
    1: ["w1", "w2"],
    2: ["w3", "w4"],
    3: ["l1", "l2"],
    4: ["l3", "l4"],
    5: ["w1_wf", "w2_wf"],
    6: ["l1_lq", "l2_lq"],
    7: ["l3_lq", "l4_lq"],
    8: ["l1_ls", "l2_ls"],
    9: ["l1_lf", "l2_lf"],
    10: ["w1_gf", "w2_gf"],
    11: ["w1_gf", "w2_gf"]
}

function getDataFromServer() {
    fetch('/getdata')
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            populateData(data);
        })
        .catch(function(err) {
            console.log('error: ' + err);
        });
    fetch('/getTop8CurrentNextData')
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            updateTop8StartedButton(data);
            highlightNextRoundForms(data.nextRound);
            highlightCurrentRoundForms(data.currentRound);
        })
        .catch(function(err) {
            console.log('error: ' + err);
        });
}

fetch('/getTop8PlayerData')
    .then(function(response) {
        return response.json();
    })
    .then(function(data) {
        populateTop8PlayerData(data);
    })
    .catch(function(err) {
        console.log('error: ' + err);
    });

function populateTop8PlayerData(data) {
    console.log(data);
    populateTop8Player("w1", data, "r1", "p1", true);
    populateTop8Player("w2", data, "r1", "p2", true);
    populateTop8Player("w3", data, "r2", "p1", true);
    populateTop8Player("w4", data, "r2", "p2", true);
    populateTop8Player("l1", data, "r3", "p1", true);
    populateTop8Player("l2", data, "r3", "p2", true);
    populateTop8Player("l3", data, "r4", "p1", true);
    populateTop8Player("l4", data, "r4", "p2", true);
    populateTop8Player("w1_wf", data, "r5", "p1");
    populateTop8Player("w2_wf", data, "r5", "p2");
    populateTop8Player("w1_gf", data, "r10", "p1");
    populateTop8Player("w2_gf", data, "r10", "p2");
    populateTop8Player("l1_lq", data, "r6", "p1");
    populateTop8Player("l2_lq", data, "r6", "p2");
    populateTop8Player("l3_lq", data, "r7", "p1");
    populateTop8Player("l4_lq", data, "r7", "p2");
    populateTop8Player("l1_ls", data, "r8", "p1");
    populateTop8Player("l2_ls", data, "r8", "p2");
    populateTop8Player("l1_lf", data, "r9", "p1");
    populateTop8Player("l2_lf", data, "r9", "p2");
}

function populateTop8Player(suffix, data, round, player, includeCountry) {
	updateElement("form_name_" + suffix, data[round][player]["name"]);
	updateElement("form_team_" + suffix, data[round][player]["team"]);
	updateElement("form_score_" + suffix, data[round][player]["score"]);
	if (includeCountry) {
		updateElement("dropdown_country_" + suffix, data[round][player]["country"]);
	}
	if (suffix == "w1_gf" || suffix == "w2_gf") {
	    // Adds score if there's a reset
	    updateElement("form_score_" + suffix + "2", data[round][player]["score2"]);
	}
}

function setAsNextRound(round, suffix1, suffix2) {
    fetch('/setNextRound', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'round=' + round
    }).then(function(response) {
        if (response.ok) {
            getJsonDataFromServerWithArgs('getTop8PlayerData', updateNextRoundForms, round, suffix1, suffix2);
        }
    }).catch(function(err) { console.log('error: ' + err); });
}

function updateNextRoundForms(top8PlayerData, round, suffix1, suffix2) {
    safeEl("form_next_round_team_1p").value = safeEl("form_team_" + suffix1).value;
    safeEl("form_next_round_name_1p").value = safeEl("form_name_" + suffix1).value;
    safeEl("dropdown_country_next1").value = top8PlayerData["r" + round]["p1"]["country"];
    safeEl("form_next_round_team_2p").value = safeEl("form_team_" + suffix2).value;
    safeEl("form_next_round_name_2p").value = safeEl("form_name_" + suffix2).value;
    safeEl("dropdown_country_next2").value = top8PlayerData["r" + round]["p2"]["country"];
    highlightNextRoundForms(round);
    jsonData.nextteam1 = safeEl("form_team_" + suffix1).value;
    jsonData.nextplayer1 = safeEl("form_name_" + suffix1).value;
    jsonData.nextteam2 = safeEl("form_team_" + suffix2).value;
    jsonData.nextplayer2 = safeEl("form_name_" + suffix2).value;
    jsonData.nextcountry1 = top8PlayerData["r" + round]["p1"]["country"];
    jsonData.nextcountry2 = top8PlayerData["r" + round]["p2"]["country"];
    sendJsonToEndpoint('updateNextPlayers');
}

function populateData(data) {
    console.log(data);
	updateElement("form_name_1p", data.p1Name);
	updateElement("form_name_2p", data.p2Name);
	updateElement("form_team_1p", data.p1Team);
	updateElement("form_team_2p", data.p2Team);
	updateElement("dropdown_round", data.round);
	updateElement("form_score_1p", data.p1Score);
	updateElement("form_score_2p", data.p2Score);
	updateElement("dropdown_country_current_1", data.p1Country);
	updateElement("dropdown_country_current_2", data.p2Country);
	updateElement("form_next_round_team_1p", data.nextteam1);
	updateElement("form_next_round_name_1p", data.nextplayer1);
	updateElement("form_next_round_team_2p", data.nextteam2);
	updateElement("form_next_round_name_2p", data.nextplayer2);
	updateElement("form_results_name_1p", data.resultplayer1);
	updateElement("form_results_score_1p", data.resultscore1);
	updateElement("form_results_name_2p", data.resultplayer2);
	updateElement("form_results_score_2p", data.resultscore2);
	jsonData = data;
	charBoot();
}

function updateElement(id, value) {
	if (value != null && String(value).length > 0) {
		safeEl(id).value = value;
	}
}

// ── LOCAL PLAYER PERSISTENCE (shared with Event Dashboard) ────────
var _localPlayersMap = new Map();     // id   -> player record
function _nameKeyedMap() {
    // Map keyed by normalized (trimmed, lowercased) names so lookups are
    // case-insensitive; records keep their display-cased .name
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

var _localPlayersByName = _nameKeyedMap(); // normalized name/alias -> player record

function saveLocalPlayerName(name, team, country) {
    // Auto-save retired: see savePlayerCard (explicit Save Player buttons).
}

function autoFillFromLocalDB(name, teamElId, countryElId) {
    var p = _localPlayersByName.get(name);
    if (!p) return false;
    if (p.team && teamElId)       safeEl(teamElId).value    = p.team;
    if (p.country && countryElId) safeEl(countryElId).value = p.country;
    return true;
}

function getSocialFromLocalDB(name) {
    var p = _localPlayersByName.get(name);
    return p ? { handle: p.social_handle || '', platform: p.social_platform || '' } : { handle: '', platform: '' };
}

function loadLocalPlayersIntoDatalist() {
    var source = localStorage.getItem('player_source') || 'both';
    if (source === 'local' || source === 'both') {
        fetch('/getLocalPlayers')
            .then(function(r) { return r.json(); })
            .then(function(players) {
                if (!players || !players.length) return;
                // Build lookup map for auto-fill
                players.forEach(function(p) {
                    if (!p || !p.name) return;
                    _localPlayersMap.set(p.id || p.name, p);
                    _localPlayersByName.set(p.name, p);
                    (p.aliases || []).forEach(function(a) { _localPlayersByName.set(a, p); });
                });
                // Populate pickers + datalist now that the maps are built
                rebuildT8NamePickers();
                refreshAllMatchHints();
                refreshH2H();
            })
            .catch(function(e) { console.log('loadLocalPlayers error:', e); });
    }
}

function setTop8PlayerSource(src) {
    localStorage.setItem('player_source', src);
    ['both','startgg','local'].forEach(function(s) {
        var btn = document.getElementById('t8srcBtn' + s.charAt(0).toUpperCase() + s.slice(1));
        if (btn) btn.classList.toggle('active', s === src);
    });
    rebuildT8NamePickers();
    if (src === 'local' || src === 'both') {
        loadLocalPlayersIntoDatalist();  // fresh fetch; rebuilds again when done
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadH2HEvents();
    var src = localStorage.getItem('player_source') || 'both';
    ['both','startgg','local'].forEach(function(s) {
        var btn = document.getElementById('t8srcBtn' + s.charAt(0).toUpperCase() + s.slice(1));
        if (btn) btn.classList.toggle('active', s === src);
    });
    loadLocalPlayersIntoDatalist();
});

// Re-translate static UI + refresh JS-set labels when language changes.
window.onLangChange = function(){
    if (window.applyTranslations) window.applyTranslations(document);
    // Refresh the H2H toggle button text (it's set in JS based on state).
    var btn = document.getElementById('h2hVisibleBtn');
    if (btn) btn.textContent = jsonData.h2hVisible ? window.t('t8_hide_stream') : window.t('t8_show_stream');
};

function updatePlayer1() {
    jsonData.p1Name = safeEl("form_name_1p").value;
    autoFillFromLocalDB(jsonData.p1Name, 'form_team_1p', 'dropdown_country_current_1');
    jsonData.p1Team    = safeEl("form_team_1p").value;
    jsonData.p1Country = safeEl("dropdown_country_current_1").value;
    var soc1 = getSocialFromLocalDB(jsonData.p1Name);
    jsonData.p1SocialHandle   = soc1.handle;
    jsonData.p1SocialPlatform = soc1.platform;
    saveLocalPlayerName(jsonData.p1Name, jsonData.p1Team, jsonData.p1Country);
    sendJsonToEndpoint('updateCurrentPlayers');
    charRestoreFor(1);
    updateMatchHint(1);
    refreshH2H();
}

function updatePlayer2() {
    jsonData.p2Name = safeEl("form_name_2p").value;
    autoFillFromLocalDB(jsonData.p2Name, 'form_team_2p', 'dropdown_country_current_2');
    jsonData.p2Team    = safeEl("form_team_2p").value;
    jsonData.p2Country = safeEl("dropdown_country_current_2").value;
    var soc2 = getSocialFromLocalDB(jsonData.p2Name);
    jsonData.p2SocialHandle   = soc2.handle;
    jsonData.p2SocialPlatform = soc2.platform;
    saveLocalPlayerName(jsonData.p2Name, jsonData.p2Team, jsonData.p2Country);
    sendJsonToEndpoint('updateCurrentPlayers');
    charRestoreFor(2);
    updateMatchHint(2);
    refreshH2H();
}

function updateTeam1() {
    jsonData.p1Team = safeEl("form_team_1p").value;
    saveLocalPlayerName(jsonData.p1Name, jsonData.p1Team, jsonData.p1Country);
    sendJsonToEndpoint('updateCurrentPlayers');
}

function updateTeam2() {
    jsonData.p2Team = safeEl("form_team_2p").value;
    saveLocalPlayerName(jsonData.p2Name, jsonData.p2Team, jsonData.p2Country);
    sendJsonToEndpoint('updateCurrentPlayers');
}

function updateNextPlayer1() {
    jsonData.nextplayer1 = safeEl("form_next_round_name_1p").value;
    autoFillFromLocalDB(jsonData.nextplayer1, 'form_next_round_team_1p', 'dropdown_country_next1');
    jsonData.nextteam1    = safeEl("form_next_round_team_1p").value;
    jsonData.nextcountry1 = safeEl("dropdown_country_next1").value;
    saveLocalPlayerName(jsonData.nextplayer1, jsonData.nextteam1, jsonData.nextcountry1);
    sendJsonToEndpoint('updateNextPlayers');
    charRestoreFor('1Next');
}

function updateNextPlayer2() {
    jsonData.nextplayer2 = safeEl("form_next_round_name_2p").value;
    autoFillFromLocalDB(jsonData.nextplayer2, 'form_next_round_team_2p', 'dropdown_country_next2');
    jsonData.nextteam2    = safeEl("form_next_round_team_2p").value;
    jsonData.nextcountry2 = safeEl("dropdown_country_next2").value;
    saveLocalPlayerName(jsonData.nextplayer2, jsonData.nextteam2, jsonData.nextcountry2);
    sendJsonToEndpoint('updateNextPlayers');
    charRestoreFor('2Next');
}

function updateNextTeam1() {
	jsonData.nextteam1 = safeEl("form_next_round_team_1p").value;
	sendJsonToEndpoint('updateNextPlayers');
}

function updateNextTeam2() {
	jsonData.nextteam2 = safeEl("form_next_round_team_2p").value;
	sendJsonToEndpoint('updateNextPlayers');
}

function updateScore1() {
	jsonData.p1Score = safeEl("form_score_1p").value;
	sendJsonToEndpoint('updateP1score');
}

function updateScore2() {
	jsonData.p2Score = safeEl("form_score_2p").value;
	sendJsonToEndpoint('updateP2score');
}

function updateRound() {
	jsonData.round = safeEl("dropdown_round").value;
	sendJsonToEndpoint('updateCurrentPlayers');
}

function reversePlayerNames() {
	var p1 = safeEl("form_name_1p").value;
	var p2 = safeEl("form_name_2p").value;
	var t1 = safeEl("form_team_1p").value;
	var t2 = safeEl("form_team_2p").value;
	var c1 = safeEl("dropdown_country_current_1").value;
	var c2 = safeEl("dropdown_country_current_2").value;
	safeEl("form_name_1p").value = p2;
	safeEl("form_name_2p").value = p1;
	safeEl("form_team_1p").value = t2;
	safeEl("form_team_2p").value = t1;
	safeEl("dropdown_country_current_1").value = c2;
	safeEl("dropdown_country_current_2").value = c1;
	jsonData.p1Name = p2;
	jsonData.p2Name = p1;
	jsonData.p1Team = t2;
	jsonData.p2Team = t1;
	jsonData.p1Country = c2;
	jsonData.p2Country = c1;
    var p1seed = jsonData.p1Seed;
    var p2seed = jsonData.p2Seed;
    jsonData.p1Seed = p2seed;
    jsonData.p2Seed = p1seed;
	sendJsonToEndpointWithCallback(reverseNames, 'updateCurrentPlayers');
}

function reverseNames() {
    callServer("reverseNames");
}

function reverseScores() {
    fetch('/getdata')
        .then(function(response) {
            return response.json();
        }).then(function (data) {
        updateElement("form_score_1p", data.p1Score);
        updateElement("form_score_2p", data.p2Score);
        var p1 = safeEl("form_score_1p").value;
        var p2 = safeEl("form_score_2p").value;
        safeEl("form_score_1p").value = p2;
        safeEl("form_score_2p").value = p1;
        jsonData.p1Score = p2;
        jsonData.p2Score = p1;
        sendJsonToEndpoint('updateCurrentScore');
    })
        .catch(function (err) {
        console.log('error: ' + err);
    });
}

function addScoreP1() {
	var score = parseInt(safeEl("form_score_1p").value);
	score++;
	jsonData.p1Score = score.toString();
	safeEl("form_score_1p").value = jsonData.p1Score;
	sendJsonToEndpoint('updateP1score');
}

function subtractScoreP1() {
	var score = parseInt(safeEl("form_score_1p").value);
	if (score <= 0) {
		return;
	}
	score--;
	jsonData.p1Score = score.toString();
	safeEl("form_score_1p").value = jsonData.p1Score;
	sendJsonToEndpoint('updateP1score');
}

function addScoreP2() {
	var score = parseInt(safeEl("form_score_2p").value);
	score++;
	jsonData.p2Score = score.toString();
	safeEl("form_score_2p").value = jsonData.p2Score;
	sendJsonToEndpoint('updateP2score');
}

function subtractScoreP2() {
	var score = parseInt(safeEl("form_score_2p").value);
	if (score <= 0) {
		return;
	}
	score--;
	jsonData.p2Score = score.toString();
	safeEl("form_score_2p").value = jsonData.p2Score;
	sendJsonToEndpoint('updateP2score');
}

function resetScores() {
	safeEl("form_score_1p").value = "0";
	safeEl("form_score_2p").value = "0";
	jsonData.p1Score = "0";
	jsonData.p2Score = "0";
        jsonData.p1Bracket = "";
	jsonData.p2Bracket = "";
	sendJsonToEndpoint('updateCurrentScore');
}

function resetAll() {
	safeEl("form_name_1p").value = "";
	safeEl("form_name_2p").value = "";
	safeEl("form_team_1p").value = "";
	safeEl("form_team_2p").value = "";
	safeEl("form_score_1p").value = "0";
	safeEl("form_score_2p").value = "0";
	safeEl("dropdown_country_current_1").value = "US";
	safeEl("dropdown_country_current_2").value = "US";
	safeEl("form_next_round_team_1p").value = "";
	safeEl("form_next_round_name_1p").value = "";
	safeEl("form_next_round_team_2p").value = "";
	safeEl("form_next_round_name_2p").value = "";
	safeEl("form_results_name_1p").value = "";
	safeEl("form_results_score_1p").value = "";
	safeEl("form_results_name_2p").value = "";
	safeEl("form_results_score_2p").value = "";
    safeEl("dropdown_country_w1").value = "US";
    safeEl("dropdown_country_w2").value = "US";
    safeEl("dropdown_country_w3").value = "US";
    safeEl("dropdown_country_w4").value = "US";
    safeEl("dropdown_country_l1").value = "US";
    safeEl("dropdown_country_l2").value = "US";
    safeEl("dropdown_country_l3").value = "US";
    safeEl("dropdown_country_l4").value = "US";
    safeEl("dropdown_country_next1").value = "US";
    safeEl("dropdown_country_next2").value = "US";
	safeEl("form_name_w1").value = "";
    safeEl("form_name_w2").value = "";
    safeEl("form_name_w3").value = "";
    safeEl("form_name_w4").value = "";
    safeEl("form_name_l1").value = "";
    safeEl("form_name_l2").value = "";
    safeEl("form_name_l3").value = "";
    safeEl("form_name_l4").value = "";
    safeEl("form_team_w1").value = "";
    safeEl("form_team_w2").value = "";
    safeEl("form_team_w3").value = "";
    safeEl("form_team_w4").value = "";
    safeEl("form_team_l1").value = "";
    safeEl("form_team_l2").value = "";
    safeEl("form_team_l3").value = "";
    safeEl("form_team_l4").value = "";
    safeEl("form_score_w1").value = "";
    safeEl("form_score_w2").value = "";
    safeEl("form_score_w3").value = "";
    safeEl("form_score_w4").value = "";
    safeEl("form_score_l1").value = "";
    safeEl("form_score_l2").value = "";
    safeEl("form_score_l3").value = "";
    safeEl("form_score_l4").value = "";
    safeEl("form_name_w1_wf").value = "";
    safeEl("form_team_w1_wf").value = "";
    safeEl("form_score_w1_wf").value = "";
    safeEl("form_score_w1_gf2").value = "";
    safeEl("form_name_w2_wf").value = "";
    safeEl("form_team_w2_wf").value = "";
    safeEl("form_score_w2_wf").value = "";
    safeEl("form_score_w2_gf2").value = "";
    safeEl("form_name_w1_gf").value = "";
    safeEl("form_team_w1_gf").value = "";
    safeEl("form_score_w1_gf").value = "";
    safeEl("form_name_w2_gf").value = "";
    safeEl("form_team_w2_gf").value = "";
    safeEl("form_score_w2_gf").value = "";
    safeEl("form_name_l1_lq").value = "";
    safeEl("form_team_l1_lq").value = "";
    safeEl("form_score_l1_lq").value = "";
    safeEl("form_name_l2_lq").value = "";
    safeEl("form_team_l2_lq").value = "";
    safeEl("form_score_l2_lq").value = "";
    safeEl("form_name_l3_lq").value = "";
    safeEl("form_team_l3_lq").value = "";
    safeEl("form_score_l3_lq").value = "";
    safeEl("form_name_l4_lq").value = "";
    safeEl("form_team_l4_lq").value = "";
    safeEl("form_score_l4_lq").value = "";
    safeEl("form_name_l1_ls").value = "";
    safeEl("form_team_l1_ls").value = "";
    safeEl("form_score_l1_ls").value = "";
    safeEl("form_name_l2_ls").value = "";
    safeEl("form_team_l2_ls").value = "";
    safeEl("form_score_l2_ls").value = "";
    safeEl("form_name_l1_lf").value = "";
    safeEl("form_team_l1_lf").value = "";
    safeEl("form_score_l1_lf").value = "";
    safeEl("form_name_l2_lf").value = "";
    safeEl("form_team_l2_lf").value = "";
    safeEl("form_score_l2_lf").value = "";
    safeEl("dropdown_round").value = "Casuals";

	jsonData.p1Name = "";
	jsonData.p2Name = "";
	jsonData.p1Team = "";
	jsonData.p2Team = "";
    jsonData.p1Seed = "";
    jsonData.p2Seed = "";
	jsonData.p1Score = "0";
	jsonData.p2Score = "0";
	jsonData.round = "";
	jsonData.p1Country = "US";
	jsonData.p2Country = "US";
	jsonData.nextplayer1 = "";
	jsonData.nextplayer2 = "";
	jsonData.nextteam1 = "";
	jsonData.nextteam2 = "";
    jsonData.nextcountry1 = "US";
    jsonData.nextcountry2 = "US";
	jsonData.resultplayer1 = "";
	jsonData.resultplayer2 = "";
	jsonData.resultscore1 = "";
	jsonData.resultscore2 = "";
	jsonData.maxScore = "";
	jsonData.round = "Casuals";
        jsonData.p1Bracket = "";
	jsonData.p2Bracket = "";
	CHAR_PLAYERS.forEach(function(p) {
		charApplyList(p, null, true);
		jsonData['p' + p + 'Character'] = '';
		jsonData['p' + p + 'CharacterPack'] = '';
		jsonData['p' + p + 'Palette'] = 0;
		jsonData['p' + p + 'CharacterFile'] = '';
	});
	setButtonColourAndText("rectangle_button_18", "#675267", "Start Top 8");
	updateAllData(resetTop8);
}

function countryDropdownCurrent(id, field) {
	var c = safeEl(id);
	jsonData[field] = c.options[c.selectedIndex].text;
	sendJsonToEndpoint('updateCurrentPlayers');
}

function countryDropdown(id, round, player) {
    var value = safeEl(id);
    updateTop8PlayerInfo(round, player, "country", value.options[value.selectedIndex].text)
}

function updateTop8PlayerInfo(round, player_id, field, value, position) {
    if (position != null && 'name' === field) {
        var team    = safeEl('form_team_' + position).value    || '';
        var country = safeEl('dropdown_country_' + position).value || '';
        // Auto-fill from local DB if available
        var localP = _localPlayersByName.get(value) || _localPlayersMap.get(value);
        if (localP) {
            if (localP.team) {
                safeEl('form_team_' + position).value = localP.team;
                team = localP.team;
                updateTop8PlayerInfoCallServer(round, player_id, 'team', localP.team);
            }
            if (localP.country) {
                safeEl('dropdown_country_' + position).value = localP.country;
                country = localP.country;
                updateTop8PlayerInfoCallServer(round, player_id, 'country', localP.country);
            }
        }
        saveLocalPlayerName(value, team, country);
        // Check to see if it's a part of our players map
        if (playersMap.has(value)) {
    	    player = playersMap.get(value);
            safeEl("form_team_" + position).value = player.team;
            updateTop8PlayerInfoCallServer(round, player_id, "team", player.team);
            safeEl("dropdown_country_" + position).value = player.country;
            updateTop8PlayerInfoCallServer(round, player_id, "country", player.country);
    	}
    }
    updateTop8PlayerInfoCallServer(round, player_id, field, value);
}

function updateTop8PlayerInfoCallServer(round, player, field, value) {
    fetch('/updateTop8playerInfo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'round=' + encodeURIComponent(round) + '&player=' + encodeURIComponent(player) + '&field=' + encodeURIComponent(field) + '&value=' + encodeURIComponent(value)
    }).catch(function(err) { console.log('error: ' + err); });
}

// ── Undo state ───────────────────────────────────────────────────
var _undoSnapshot = null;

function _captureSnapshot() {
    const fields = [
        'form_name_1p','form_team_1p','form_score_1p','dropdown_country_current_1',
        'form_name_2p','form_team_2p','form_score_2p','dropdown_country_current_2',
        'form_next_round_name_1p','form_next_round_team_1p','dropdown_country_next1',
        'form_next_round_name_2p','form_next_round_team_2p','dropdown_country_next2',
        'form_results_name_1p','form_results_score_1p',
        'form_results_name_2p','form_results_score_2p',
        'dropdown_round'
    ];
    const snap = { fields: {}, jsonData: JSON.parse(JSON.stringify(jsonData || {})) };
    fields.forEach(id => { snap.fields[id] = safeEl(id).value; });
    _undoSnapshot = snap;
    // Show the undo button
    const btn = document.getElementById('button_undo_round');
    if (btn) btn.style.display = '';
}

function undoNextRound() {
    fetch('/undoNextRound', { method: 'POST' })
        .then(function(response) {
            if (!response.ok) { alert(window.t('t8_nothing_undo')); return null; }
            return response.json();
        })
        .then(function(data) {
            if (!data) return;
            // Keep _undoSnapshot alive so confirmAndRefresh can use its jsonData
            // Hide undo, show confirm
            const undoBtn = document.getElementById('button_undo_round');
            const confirmBtn = document.getElementById('button_confirm_refresh');
            if (undoBtn) undoBtn.style.display = 'none';
            if (confirmBtn) confirmBtn.style.display = '';
            // Disable Next Round until confirmed
            safeEl('rectangle_button_7').disabled = true;
        })
        .catch(function(err) { console.log('Undo error: ' + err); });
}

function confirmAndRefresh() {
    const confirmBtn = document.getElementById('button_confirm_refresh');
    if (confirmBtn) confirmBtn.style.display = 'none';
    safeEl('rectangle_button_7').disabled = false;

    // Push the snapshot's jsonData directly to the server so scoreboard.json
    // has the correct player names/scores before we fetch
    if (_undoSnapshot && _undoSnapshot.jsonData) {
        fetch('/updatealldata', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(_undoSnapshot.jsonData)
        }).then(function() {
            // Now fetch clean state from server
            getDataFromServer();
            getJsonDataFromServer('getTop8PlayerData', populateTop8PlayerData);
        });
    } else {
        getDataFromServer();
        getJsonDataFromServer('getTop8PlayerData', populateTop8PlayerData);
    }
    _undoSnapshot = null;
}

function nextRound() {
    fetch('/getdata')
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (compareScores(data)) {
                _captureSnapshot();
                safeEl("form_results_score_1p").value = data.p1Score;
                safeEl("form_results_score_2p").value = data.p2Score;
                safeEl("form_results_name_1p").value = data.p1Name;
                safeEl("form_results_name_2p").value = data.p2Name;

                safeEl("form_results_score_1p").style.opacity  = 0.5;
                safeEl("form_results_score_2p").style.opacity  = 0.5;
                safeEl("form_results_name_1p").style.opacity  = 0.5;
                safeEl("form_results_name_2p").style.opacity  = 0.5;
                getJsonDataFromServer("getNextRoundData", updateCurrentAndNextInfoUpdatePlayerData)
            }
      })
    .catch(function (err) {
      console.log('error: ' + err);
    });
}

function compareScores(data) {
    if (data.p1Name.trim() === "" && data.p2Name.trim() === "") {
        // No names, just pass
        return true;
    }

	safeEl("form_score_1p").value = data.p1Score;
	safeEl("form_score_2p").value = data.p2Score;
    if (data.p1Score == data.p2Score) {
        alert(window.t('t8_scores_same') + " " + data.p1Score + ". " + window.t('t8_scores_same_2'));
        return false;
    }
    return true;
}

function startTop8() {
    getJsonDataFromServer("getNextRoundData", updateCurrentAndNextInfo)
}

function updateTop8StartedButton(currentNextData) {
    var top8Started = currentNextData.started;
    if (top8Started) {
        setButtonColourAndText("rectangle_button_18", "#C62828", "In Progress");
    } else {
        resetStartButton();
    }
}

function resetStartButton() {
    // Clear the inline override so the stylesheet's green .btn-start
    // styling (including hover) applies again
    var element = safeEl("rectangle_button_18");
    element.style.removeProperty('background');
    element.style.removeProperty('color');
    element.innerText = "\u25B6 Start Top 8";
}

function setButtonColourAndText(id, bgColour, text) {
    var element = safeEl(id);
    // 'important' priority so the .btn-start !important stylesheet
    // rules (incl. :hover) can't override the state colour
    element.style.setProperty('background', bgColour, 'important');
    element.innerText = text;
    element.style.setProperty('color', 'white', 'important');
}

function updateCurrentAndNextInfo(currentNextData) {
    safeEl("form_next_round_team_1p").value = currentNextData.nextPlayer1.team;
    safeEl("form_next_round_name_1p").value = currentNextData.nextPlayer1.name;
    safeEl("form_next_round_team_2p").value = currentNextData.nextPlayer2.team;
    safeEl("form_next_round_name_2p").value = currentNextData.nextPlayer2.name;
    safeEl("dropdown_country_next1").value = currentNextData.nextPlayer1.country;
    safeEl("dropdown_country_next2").value = currentNextData.nextPlayer2.country;
    safeEl("form_team_1p").value = currentNextData.player1.team;
    safeEl("form_name_1p").value = currentNextData.player1.name;
    safeEl("form_team_2p").value = currentNextData.player2.team;
    safeEl("form_name_2p").value = currentNextData.player2.name;
    safeEl("dropdown_country_current_1").value = currentNextData.player1.country;
    safeEl("dropdown_country_current_2").value = currentNextData.player2.country;
    safeEl("form_score_1p").value = "0";
    safeEl("form_score_2p").value = "0";
    safeEl("dropdown_round").value = currentNextData.currentRoundName;
    updateTop8StartedButton(currentNextData);
    highlightNextRoundForms(currentNextData.nextRound)
    highlightCurrentRoundForms(currentNextData.currentRound)

    jsonData.round = currentNextData.currentRoundName;
    jsonData.p1Team = currentNextData.player1.team;
    jsonData.p2Team = currentNextData.player2.team;
    jsonData.p1Name = currentNextData.player1.name;
    jsonData.p2Name = currentNextData.player2.name;
    jsonData.p1Country = currentNextData.player1.country;
    jsonData.p2Country = currentNextData.player2.country;

    jsonData.p1Seed = "";
    jsonData.p2Seed = "";
	// If player is in player map, try to set the seed value
	if (playersMap.has(jsonData.p1Name)) {
	    jsonData.p1Seed = playersMap.get(jsonData.p1Name).seed;
	}
    if (playersMap.has(jsonData.p2Name)) {
        jsonData.p2Seed = playersMap.get(jsonData.p2Name).seed;
    }

    jsonData.p1Score = "0";
    jsonData.p2Score = "0";
    jsonData.nextteam1 = currentNextData.nextPlayer1.team;
    jsonData.nextplayer1 = currentNextData.nextPlayer1.name;
    jsonData.nextteam2 = currentNextData.nextPlayer2.team;
    jsonData.nextplayer2 = currentNextData.nextPlayer2.name;
    jsonData.nextcountry1 = currentNextData.nextPlayer1.country;
    jsonData.nextcountry2 = currentNextData.nextPlayer2.country;

    // Restore saved characters for whoever now occupies each slot --
    // clears the picker when a slot is empty, loads the right picks
    // otherwise. Covers current AND next so advancing a round never
    // leaves a previous player's character behind.
    CHAR_PLAYERS.forEach(function(p) { charRestoreFor(p); });
    CHAR_PLAYERS.forEach(function(p) { updateMatchHint(p); });
    refreshH2H();
}

function highlightCurrentRoundForms(round) {
    var gfBadge = document.getElementById('gf_reset_badge');
    if (gfBadge) gfBadge.style.display = (parseInt(round, 10) === 11) ? '' : 'none';
    for (const suffix of lastRoundSuffix) {
        safeEl("form_team_" + suffix).style.border="";
        safeEl("form_name_" + suffix).style.border="";
        safeEl("form_score_" + suffix).style.border="";
    }
    if (round == null || !roundSuffixMap[round]) return;
    for (const suffix of roundSuffixMap[round]) {
        safeEl("form_team_" + suffix).style.border="2px solid red";
        safeEl("form_name_" + suffix).style.border="2px solid red";
        safeEl("form_score_" + suffix).style.border="2px solid red";
    }
    if (round == 11) {
        safeEl("form_score_w1_gf2").style.border="2px solid red";
        safeEl("form_score_w2_gf2").style.border="2px solid red";
    }
    lastRoundSuffix = roundSuffixMap[round];
}

function highlightNextRoundForms(round) {
    for (const suffix of lastNextRoundSuffix) {
        safeEl("form_team_" + suffix).style.border="";
        safeEl("form_name_" + suffix).style.border="";
        safeEl("form_score_" + suffix).style.border="";
    }
    if (round == null || !roundSuffixMap[round]) return;
    for (const suffix of roundSuffixMap[round]) {
        safeEl("form_team_" + suffix).style.border="2px solid yellow";
        safeEl("form_name_" + suffix).style.border="2px solid yellow";
        safeEl("form_score_" + suffix).style.border="2px solid yellow";
    }
    lastNextRoundSuffix = roundSuffixMap[round];
}

function updateCurrentAndNextInfoUpdatePlayerData(currentNextData) {
    updateCurrentAndNextInfo(currentNextData)
    getJsonDataFromServer("getTop8PlayerData", populateTop8PlayerData)
}

function getJsonDataFromServerWithArgs(endpoint, callback, arg1, arg2, arg3) {
    fetch('/' + endpoint)
        .then(function(response) { return response.json(); })
        .then(function(data) { callback(data, arg1, arg2, arg3); })
        .catch(function(err) { console.log('error: ' + err); });
}

function getJsonDataFromServer(endpoint, callback) {
    fetch('/' + endpoint)
        .then(function(response) { return response.json(); })
        .then(function(data) { callback(data); })
        .catch(function(err) { console.log('error: ' + err); });
}

function updateResults() {
	safeEl("form_results_score_1p").style.opacity  = 1;
	safeEl("form_results_score_2p").style.opacity  = 1;
	safeEl("form_results_name_1p").style.opacity  = 1;
	safeEl("form_results_name_2p").style.opacity  = 1;
	jsonData.resultscore1 = safeEl("form_results_score_1p").value;
	jsonData.resultscore2 = safeEl("form_results_score_2p").value;
	jsonData.resultplayer1 = safeEl("form_results_name_1p").value;
	jsonData.resultplayer2 = safeEl("form_results_name_2p").value;
	sendJsonToEndpoint('updateResults');
}

function callServer(endpoint) {
    fetch('/' + endpoint, { method: 'POST' })
        .catch(function(err) { console.log('error: ' + err); });
}

function resetBracket() {
    if (!confirm("Reset the bracket run? Scores and progress are cleared; the 8 seeded players (names, teams, countries) are kept.")) return;
    fetch('/resetBracket', { method: 'POST' })
        .then(function(response) {
            if (response.ok) {
                // Server state changed wholesale -- reload so every panel
                // (bracket, current/next, button state) reflects it
                location.reload();
            } else {
                alert(window.t('t8_reset_failed') + ' (' + response.status + ')');
            }
        })
        .catch(function(err) { console.log('resetBracket error: ' + err); });
}

function resetTop8() {
    fetch('/resetTop8', { method: 'POST' })
        .then(function(response) {
            if (response.ok) {
                resetStartButton();
                for (const suffix of lastRoundSuffix) {
                    safeEl("form_team_" + suffix).style.border="";
                    safeEl("form_name_" + suffix).style.border="";
                    safeEl("form_score_" + suffix).style.border="";
                }
                for (const suffix of lastNextRoundSuffix) {
                    safeEl("form_team_" + suffix).style.border="";
                    safeEl("form_name_" + suffix).style.border="";
                    safeEl("form_score_" + suffix).style.border="";
                }
                safeEl("form_score_w1_gf2").style.border="";
                safeEl("form_score_w2_gf2").style.border="";
            }
        })
        .catch(function(err) { console.log('error: ' + err); });
}

function updateAllData(callback) {
    jsonData.timestamp = Date.now();
    fetch('/updatealldata', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(jsonData)
    }).then(function(response) {
        if (response.ok) { callback(); }
    }).catch(function(err) { console.log('error: ' + err); });
}

function sendJsonToEndpoint(endpoint) {
    sendJsonToEndpointWithCallback(function (){}, endpoint);
}

function sendJsonToEndpointWithCallback(callback, endpoint) {
    jsonData.timestamp = Date.now();
    fetch('/' + endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(jsonData)
    }).then(function(response) {
        if (response.ok) { callback(); }
    }).catch(function(err) { console.log('error: ' + err); });
}

var startggInfo;
var playersMap = new Map();

function getStartggInfo() {
    fetch('/getTournamentInfo')
        .then(function(response) {
            return response.json();
        })
        .then(function (data) {
        if (Object.keys(data).length != 0) {
            startggInfo = data;
        }
        loadPlayerData(true);
      })
    .catch(function (err) {
      console.log('error: ' + err);
    });
}

function loadPlayerData(fromCache) {
    var param1 = encodeURIComponent(startggInfo.tournament);
    var param2 = encodeURIComponent(startggInfo.event);
    var param3 = fromCache;
    var url = `/getAllPlayersForTournament?tournament=${param1}&event=${param2}&fromCache=${param3}`;
    fetch(url)
      .then(function(response) {
         if (!response.ok) throw new Error("Network response was not ok");
           return response.json();
         })
        .then(function (playersData) {
            nextPlaySuggestions = safeEl('next_player_suggestions');
            playersMap.clear();
            if (playersData.length === 0 || playersData[startggInfo.event].length === 0) {
                // Clear all options from the datalist
                nextPlaySuggestions.innerHTML = '';
                return;
            }

            // Build playersMap regardless of preference (needed for team/country lookup)
            playersData[startggInfo.event]
              .slice()
              .sort((a, b) => a.name.localeCompare(b.name))
              .forEach(player => {
                playersMap.set(player.name, player);
            });

            rebuildT8NamePickers();
        })
        .catch(function (err) {
              console.log('error: ' + err);
            });
}

getDataFromServer();
getStartggInfo();

// ════════════════════════════════════════════════════════════════
// CHARACTER PICKER (current match) — ported from the event dashboard.
// Reads game/slots from the server, shows the player's roster first,
// saves picks to the player profile, and pushes scoreboard updates
// through /updatePlayerCharacters.
// ════════════════════════════════════════════════════════════════
var CHAR_PLAYERS = [1, 2, '1Next', '2Next'];
var _gameSlots = {};
var _activeSlot = { 1: 0, 2: 0, '1Next': 0, '2Next': 0 };
var _charMaps = {};
var _forceFullList = { 1: false, 2: false, '1Next': false, '2Next': false };
var _charBooted = false;

function charGetGame() { return (jsonData && jsonData.current_game) || ''; }
function charGetSlots(game) { return _gameSlots[game] || 1; }

function charPlayerName(player) {
    if (!jsonData) return '';
    if (player === '1Next') return jsonData.nextplayer1;
    if (player === '2Next') return jsonData.nextplayer2;
    return jsonData['p' + player + 'Name'];
}

function charGetLocalPlayer(player) {
    var name = charPlayerName(player);
    return name ? _localPlayersByName.get(name.trim()) : null;
}

function charBoot() {
    if (_charBooted) return;
    _charBooted = true;
    fetch('/getGames')
        .then(function(r) { return r.json(); })
        .then(function(games) {
            _gameSlots = games || {};
            CHAR_PLAYERS.forEach(function(p) {
                // Restore from scoreboard.json state written by the dashboard
                var list = jsonData['p' + p + 'Characters'];
                if (Array.isArray(list) && list.length) charApplyList(p, list, false);
                else charRenderSlotTabs(p);
            });
        })
        .catch(function(e) { console.log('charBoot error:', e); });
    charLoadPacks();
}

function charLoadPacks() {
    var game = charGetGame();
    if (!game) return;
    fetch('/getCharacterPacks?game=' + encodeURIComponent(game))
        .then(function(r) { return r.json(); })
        .then(function(packs) {
            CHAR_PLAYERS.forEach(function(p) {
                var sel = document.getElementById('p' + p + 'CharPack');
                if (!sel) return;
                sel.innerHTML = '<option value="">Pack</option>';
                (packs || []).forEach(function(pk) {
                    var opt = document.createElement('option');
                    opt.value = pk; opt.textContent = pk;
                    sel.appendChild(opt);
                });
                if (packs && packs.length === 1) sel.value = packs[0];
            });
        })
        .catch(function(e) { console.log('charLoadPacks error:', e); });
}

function charLoadChars(player) {
    var game = charGetGame();
    var pack = document.getElementById('p' + player + 'CharPack').value;
    charClosePopover(player);
    if (!game || !pack) return;
    var key = game + '/' + pack;
    if (_charMaps[key]) return;  // already cached
    fetch('/getCharacterList?game=' + encodeURIComponent(game) + '&pack=' + encodeURIComponent(pack))
        .then(function(r) { return r.json(); })
        .then(function(charMap) { _charMaps[key] = charMap; });
}

function charGetList(player) {
    var list = jsonData['p' + player + 'Characters'];
    if (!Array.isArray(list)) { list = []; jsonData['p' + player + 'Characters'] = list; }
    return list;
}

function charCompactPicks(player) {
    var picks = [];
    charGetList(player).forEach(function(p, i) {
        if (p && p.file) picks.push({ slot: i, pack: p.pack,
            character: p.character, palette: p.palette, file: p.file });
    });
    return picks;
}

function charPushToServer(player) {
    fetch('/updatePlayerCharacters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player: String(player), characters: charCompactPicks(player) })
    }).catch(function(e) { console.log('updatePlayerCharacters error:', e); });
}

function charUpdateButton(player) {
    var pick  = charGetList(player)[_activeSlot[player]];
    var thumb = document.getElementById('p' + player + 'CharThumb');
    var label = document.getElementById('p' + player + 'CharLabel');
    var packSel = document.getElementById('p' + player + 'CharPack');
    if (pick && pick.file) {
        if (thumb) { thumb.src = '/' + pick.file; thumb.style.display = 'inline'; }
        if (label) label.textContent = pick.character + ' (' + pick.palette + ')';
        if (packSel && pick.pack) packSel.value = pick.pack;
    } else {
        if (thumb) { thumb.src = ''; thumb.style.display = 'none'; }
        if (label) label.textContent = '\u2014';
    }
}

function charRenderSlotTabs(player) {
    var wrap = document.getElementById('p' + player + 'CharSlots');
    var slots = charGetSlots(charGetGame());
    if (_activeSlot[player] >= slots) _activeSlot[player] = 0;
    if (wrap) {
        if (slots <= 1) {
            wrap.style.display = 'none';
            wrap.innerHTML = '';
        } else {
            wrap.style.display = 'flex';
            wrap.innerHTML = '';
            var list = charGetList(player);
            for (var s = 0; s < slots; s++) (function(s) {
                var pick = list[s];
                var tab = document.createElement('div');
                tab.className = 'char-slot-tab' +
                    (s === _activeSlot[player] ? ' active' : '') +
                    (pick && pick.file ? ' filled' : '');
                if (pick && pick.file) {
                    var im = document.createElement('img');
                    im.src = '/' + pick.file;
                    im.className = 'char-preview-target';
                    im.dataset.char = pick.character;
                    im.dataset.palette = pick.palette;
                    im.onerror = function() { this.style.display = 'none'; };
                    tab.appendChild(im);
                } else {
                    var sp = document.createElement('span');
                    sp.textContent = (s + 1);
                    tab.appendChild(sp);
                }
                tab.title = pick && pick.character
                    ? 'Slot ' + (s + 1) + ': ' + pick.character + ' (' + pick.palette + ')'
                    : 'Slot ' + (s + 1) + ' (empty)';
                tab.onclick = function(e) {
                    e.stopPropagation();
                    _activeSlot[player] = s;
                    charRenderSlotTabs(player);
                };
                wrap.appendChild(tab);
            })(s);
        }
    }
    charUpdateButton(player);
}

function charApplyList(player, saved, push) {
    if (saved && !Array.isArray(saved)) saved = [saved];
    var list = [];
    (saved || []).forEach(function(p, i) {
        if (!p || !p.file) return;
        var s = (typeof p.slot === 'number') ? p.slot : i;
        list[s] = { slot: s, pack: p.pack || '', character: p.character || '',
                    palette: p.palette || 0, file: p.file };
    });
    jsonData['p' + player + 'Characters'] = list;
    _activeSlot[player] = 0;
    charRenderSlotTabs(player);
    if (push) charPushToServer(player);
}

function charRestoreFor(player) {
    var game = charGetGame();
    var lp = charGetLocalPlayer(player);
    charApplyList(player, (game && lp && lp.characters) ? lp.characters[game] : null, true);
}

function charClosePopover(player) {
    _forceFullList[player] = false;
    var popover = document.getElementById('p' + player + 'CharPopover');
    var btn     = document.getElementById('p' + player + 'CharPickerBtn');
    if (popover) popover.style.display = 'none';
    if (btn) btn.classList.remove('open');
}

function charClearSlot(player) {
    var list = charGetList(player);
    var s = _activeSlot[player];
    charClosePopover(player);
    if (!list[s]) return;
    list[s] = undefined;
    charRenderSlotTabs(player);
    charPushToServer(player);
    var game = charGetGame();
    var lp = charGetLocalPlayer(player);
    if (game && lp && lp.id) {
        var picks = charCompactPicks(player);
        if (!lp.characters) lp.characters = {};
        lp.characters[game] = picks;
        var u = {}; u[game] = picks;
        fetch('/saveLocalPlayer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: lp.id, name: lp.name, characters: u })
        }).catch(function(e) { console.log('clearSlot save error:', e); });
    }
}

function charPopoverFooter(player, popover, mode, hasRoster) {
    var foot = document.createElement('div');
    foot.className = 'char-popover-footer';
    var slots = charGetSlots(charGetGame());
    var active = _activeSlot[player];
    if (charGetList(player)[active]) {
        var clr = document.createElement('button');
        clr.className = 'char-popover-footbtn';
        clr.textContent = '\u2715 Clear' + (slots > 1 ? ' slot ' + (active + 1) : '');
        clr.onclick = function(e) { e.stopPropagation(); charClearSlot(player); };
        foot.appendChild(clr);
    }
    if (mode === 'roster') {
        var full = document.createElement('button');
        full.className = 'char-popover-footbtn';
        full.textContent = window.t('t8_load_full_roster');
        full.onclick = function(e) {
            e.stopPropagation();
            charClosePopover(player);
            _forceFullList[player] = true;
            charTogglePicker(player);
        };
        foot.appendChild(full);
    } else if (hasRoster) {
        var ros = document.createElement('button');
        ros.className = 'char-popover-footbtn';
        ros.textContent = '\u25C2 Player roster';
        ros.onclick = function(e) {
            e.stopPropagation();
            charClosePopover(player);
            charTogglePicker(player);
        };
        foot.appendChild(ros);
    }
    if (foot.children.length) popover.appendChild(foot);
}

function charRenderRosterPopover(player, game, roster, popover, btn) {
    popover.innerHTML = '';
    var head = document.createElement('div');
    head.className = 'char-roster-head';
    head.textContent = (charPlayerName(player) || 'Player') + "'s roster";
    popover.appendChild(head);
    roster.forEach(function(entry) {
        if (!entry || !entry.file) return;
        var row = document.createElement('div');
        row.className = 'char-row';
        row.innerHTML =
            '<img class="char-row-thumb char-preview-target" data-char="' + entry.character +
            '" data-palette="' + entry.palette + '" src="/' + entry.file + '">' +
            '<span class="char-row-name">' + entry.character +
            ' <span class="char-roster-pal">(' + entry.palette + ')</span></span>';
        row.querySelector('.char-row-thumb').onerror = function() { this.style.display = 'none'; };
        row.onclick = function(e) {
            e.stopPropagation();
            charSelectPalette(player, game, entry.pack, entry.character,
                              entry.palette, entry.file, null, popover);
        };
        popover.appendChild(row);
    });
    charPopoverFooter(player, popover, 'roster', true);
    popover.style.display = 'block';
    btn.classList.add('open');
}

function charTogglePicker(player) {
    var popover = document.getElementById('p' + player + 'CharPopover');
    var btn     = document.getElementById('p' + player + 'CharPickerBtn');
    if (!popover || !btn) return;
    if (popover.style.display === 'block') { charClosePopover(player); return; }
    CHAR_PLAYERS.forEach(function(p) { if (p !== player) charClosePopover(p); });

    var game = charGetGame();
    if (!game) { alert(window.t('t8_set_game_first')); return; }

    var localPlayer = charGetLocalPlayer(player);
    var roster = (localPlayer && localPlayer.roster && localPlayer.roster[game]) || [];
    if (roster.length > 0 && !_forceFullList[player]) {
        charRenderRosterPopover(player, game, roster, popover, btn);
        return;
    }

    var pack = document.getElementById('p' + player + 'CharPack').value;
    if (!pack) { alert(window.t('t8_select_pack_first')); return; }
    var key = game + '/' + pack;

    function render(charMap) {
        popover.innerHTML = '';
        Object.keys(charMap).sort().forEach(function(char) {
            var palettes = charMap[char];
            if (!palettes || !palettes.length) return;
            var defaultImg = '/' + palettes[0].file;
            var row = document.createElement('div');
            row.className = 'char-row';
            row.innerHTML =
                '<img class="char-row-thumb char-preview-target" data-char="' + char +
                '" data-palette="' + palettes[0].palette + '" src="' + defaultImg + '">' +
                '<span class="char-row-name">' + char + '</span>' +
                '<span class="char-row-arrow">\u203A</span>';
            row.querySelector('.char-row-thumb').onerror = function() { this.style.display = 'none'; };
            var strip = document.createElement('div');
            strip.className = 'char-palette-strip';
            strip.style.display = 'none';
            palettes.forEach(function(p) {
                var img = document.createElement('img');
                img.className = 'char-palette-thumb';
                img.src = '/' + p.file;
                img.dataset.char = char;
                img.dataset.palette = p.palette;
                img.onerror = function() { this.style.display = 'none'; };
                img.onclick = function(e) {
                    e.stopPropagation();
                    charSelectPalette(player, game, pack, char, p.palette, p.file, img, popover);
                };
                strip.appendChild(img);
            });
            row.onclick = function(e) {
                e.stopPropagation();
                var open = strip.style.display !== 'none';
                popover.querySelectorAll('.char-palette-strip').forEach(function(s) { s.style.display = 'none'; });
                strip.style.display = open ? 'none' : 'flex';
            };
            popover.appendChild(row);
            popover.appendChild(strip);
        });
        var lp = charGetLocalPlayer(player);
        var hasRoster = !!(lp && lp.roster && lp.roster[game] && lp.roster[game].length);
        charPopoverFooter(player, popover, 'full', hasRoster);
        popover.style.display = 'block';
        btn.classList.add('open');
    }

    if (_charMaps[key]) { render(_charMaps[key]); return; }
    fetch('/getCharacterList?game=' + encodeURIComponent(game) + '&pack=' + encodeURIComponent(pack))
        .then(function(r) { return r.json(); })
        .then(function(charMap) {
            _charMaps[key] = charMap || {};
            render(_charMaps[key]);
        })
        .catch(function(e) { console.log('getCharacterList error:', e); });
}

function charSelectPalette(player, game, pack, char, palette, file, imgEl, popover) {
    popover.querySelectorAll('.char-palette-thumb.selected').forEach(function(el) {
        el.classList.remove('selected');
    });
    if (imgEl) imgEl.classList.add('selected');

    var list = charGetList(player);
    list[_activeSlot[player]] = { slot: _activeSlot[player], pack: pack,
                                  character: char, palette: palette, file: file };
    charRenderSlotTabs(player);
    charPushToServer(player);
    charClosePopover(player);

    var localPlayer = charGetLocalPlayer(player);
    if (game && localPlayer && localPlayer.id) {
        var picks = charCompactPicks(player);
        if (!localPlayer.characters) localPlayer.characters = {};
        localPlayer.characters[game] = picks;
        if (!localPlayer.roster) localPlayer.roster = {};
        var rlist = localPlayer.roster[game] || [];
        var found = false;
        rlist.forEach(function(e) {
            if (e.character === char) { e.pack = pack; e.palette = palette; e.file = file; found = true; }
        });
        if (!found) rlist.push({ character: char, pack: pack, palette: palette, file: file });
        localPlayer.roster[game] = rlist;
        var cu = {}; cu[game] = picks;
        var ru = {}; ru[game] = rlist;
        fetch('/saveLocalPlayer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: localPlayer.id, name: localPlayer.name,
                                   characters: cu, roster: ru })
        }).catch(function(e) { console.log('saveCharacter error:', e); });
    }
}

// Close popovers on outside click
document.addEventListener('click', function(e) {
    if (!e.target.closest('.char-select-row')) {
        CHAR_PLAYERS.forEach(charClosePopover);
    }
});

// ── CHARACTER HOVER PREVIEW ─────────────────────────────────────
(function() {
    var p = document.getElementById('char-preview');
    var img = document.getElementById('char-preview-img');
    var lbl = document.getElementById('char-preview-label');
    if (!p) return;
    function move(e) {
        if (p.style.display === 'none') return;
        var x = e.clientX + 16, y = e.clientY + 16;
        if (x + 140 > window.innerWidth)  x = e.clientX - 148;
        if (y + 155 > window.innerHeight) y = e.clientY - 158;
        p.style.left = x + 'px'; p.style.top = y + 'px';
    }
    document.addEventListener('mouseover', function(e) {
        var t = e.target.closest('.char-palette-thumb, .char-preview-target');
        if (!t) { p.style.display = 'none'; return; }
        img.src = t.src;
        lbl.textContent = (t.dataset.char || '') +
            (t.dataset.palette !== undefined ? ' \u00b7 ' + t.dataset.palette : '');
        p.style.display = 'block';
        move(e);
    });
    document.addEventListener('mousemove', move);
    document.addEventListener('mouseout', function(e) {
        var t = e.target.closest('.char-palette-thumb, .char-preview-target');
        if (t && !(e.relatedTarget && e.relatedTarget.closest('.char-palette-thumb, .char-preview-target'))) {
            p.style.display = 'none';
        }
    });
})();


// ════════════════════════════════════════════════════════════════
// LIVE SYNC — refresh when other pages change shared data.
// ════════════════════════════════════════════════════════════════
if (window.liveSync) {
    liveSync.on('players', function() {
        loadLocalPlayersIntoDatalist();
        loadH2HEvents();
        refreshH2H();
    });
    liveSync.on('top8', function() {
        fetch('/getTop8PlayerData')
            .then(function(r) { return r.json(); })
            .then(populateTop8PlayerData)
            .catch(function(e) { console.log('liveSync top8 refresh error:', e); });
        fetch('/getTop8CurrentNextData')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                updateTop8StartedButton(data);
                highlightNextRoundForms(data.nextRound);
                highlightCurrentRoundForms(data.currentRound);
            })
            .catch(function(e) { console.log('liveSync top8 state error:', e); });
    });
}


// ════════════════════════════════════════════════════════════════
// EXPLICIT PLAYER SAVE (current match cards)
// ════════════════════════════════════════════════════════════════
function updateMatchHint(token) {
    var el = document.getElementById('p' + token + 'MatchHint');
    if (!el) return;
    var name = (charPlayerName(token) || '').trim();
    if (!name) { el.textContent = ''; el.className = 'player-match-hint'; return; }
    var rec = _localPlayersByName.get(name);
    if (rec && rec.id) {
        el.textContent = '\u2192 ' + rec.name;
        el.className = 'player-match-hint matched';
    } else {
        el.textContent = window.t('t8_not_in_db');
        el.className = 'player-match-hint unmatched';
    }
}

function refreshAllMatchHints() { CHAR_PLAYERS.forEach(updateMatchHint); }

function savePlayerCard(token) {
    var name = (charPlayerName(token) || '').trim();
    if (!name) return;
    var rec = _localPlayersByName.get(name);
    var body = { name: name };
    var team = jsonData['p' + token + 'Team'];
    var country = jsonData['p' + token + 'Country'];
    if (team)    body.team    = team;
    if (country) body.country = country;
    if (!rec || !rec.id) {
        var game = charGetGame();
        var picks = charCompactPicks(token);
        if (game && picks.length) {
            body.characters = {}; body.characters[game] = picks;
            body.roster = {}; body.roster[game] = picks.map(function(p) {
                return { character: p.character, pack: p.pack, palette: p.palette, file: p.file };
            });
        }
    }
    var btn = document.getElementById('p' + token + 'SaveBtn');
    fetch('/saveLocalPlayer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    }).then(function(r) {
        if (!r.ok) throw new Error(r.status);
        if (btn) {
            btn.textContent = '\u2713 Saved';
            setTimeout(function() { btn.textContent = window.t('t8_save_player'); }, 1600);
        }
    }).catch(function(e) {
        console.log('savePlayerCard error:', e);
        if (btn) {
            btn.textContent = window.t('t8_save_failed');
            setTimeout(function() { btn.textContent = window.t('t8_save_player'); }, 2000);
        }
    });
}


// ════════════════════════════════════════════════════════════════
// MATCHUP HISTORY (H2H) — follows the two current-match players.
// ════════════════════════════════════════════════════════════════
var _h2hEvents = [];
var _h2hScope = 'alltime';

function _h2hResolveId(name) {
    var rec = name ? _localPlayersByName.get(name.trim()) : null;
    return (rec && rec.id) ? rec.id : null;
}

function loadH2HEvents() {
    fetch('/listImportedEvents')
        .then(function(r) { return r.json(); })
        .then(function(events) {
            _h2hEvents = events || [];
            var sel = document.getElementById('h2hScope');
            if (!sel) return;
            var prev = sel.value || 'alltime';
            sel.innerHTML = '<option value="alltime">All-time</option>';
            // Series tier: distinct series across imported events
            var seriesNames = [];
            _h2hEvents.forEach(function(ev) {
                var s = (ev.series || '').trim();
                if (s && seriesNames.indexOf(s) === -1) seriesNames.push(s);
            });
            seriesNames.sort(function(a, b) { return a.toLowerCase().localeCompare(b.toLowerCase()); });
            if (seriesNames.length) {
                var sg = document.createElement('optgroup');
                sg.label = 'Series';
                seriesNames.forEach(function(s) {
                    var o = document.createElement('option');
                    o.value = 'series:' + s;
                    o.textContent = s;
                    sg.appendChild(o);
                });
                sel.appendChild(sg);
            }
            // Individual events
            var eg = document.createElement('optgroup');
            eg.label = 'Events';
            _h2hEvents.forEach(function(ev) {
                var o = document.createElement('option');
                o.value = ev.event_slug;
                o.textContent = ev.label || ev.event_name || ev.event_slug;
                eg.appendChild(o);
            });
            sel.appendChild(eg);
            sel.value = prev;
            if (sel.value !== prev) { sel.value = 'alltime'; }
            _h2hScope = sel.value;
        })
        .catch(function(e) { console.log('loadH2HEvents error:', e); });
}

function onH2HScopeChange() {
    var sel = document.getElementById('h2hScope');
    _h2hScope = sel ? sel.value : 'alltime';
    refreshH2H();
}

function refreshH2H() {
    var box = document.getElementById('h2hResult');
    if (!box) return;
    var name1 = charPlayerName(1) || '';
    var name2 = charPlayerName(2) || '';
    var id1 = _h2hResolveId(name1);
    var id2 = _h2hResolveId(name2);
    if (!id1 || !id2) {
        box.textContent = (name1 && name2) ? 'Both players must be in the player DB.' : '';
        box.className = 'h2h-result muted';
        _writeH2HFields({ scope: _h2hScope });
        return;
    }
    if (id1 === id2) { box.textContent = ''; return; }
    var isSeries = _h2hScope.indexOf('series:') === 0;
    var seriesName = isSeries ? _h2hScope.slice(7) : '';
    var _h2hGame = charGetGame();
    var url = '/getMatchupHistory?p1=' + encodeURIComponent(id1) + '&p2=' + encodeURIComponent(id2);
    if (_h2hGame) url += '&game=' + encodeURIComponent(_h2hGame);
    if (isSeries) url += '&series=' + encodeURIComponent(seriesName);
    else if (_h2hScope !== 'alltime') url += '&event=' + encodeURIComponent(_h2hScope);
    fetch(url)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.ok) { box.textContent = ''; return; }
            var n1 = (_localPlayersByName.get(name1) || {}).name || name1;
            var n2 = (_localPlayersByName.get(name2) || {}).name || name2;
            var isEvent = (!isSeries && _h2hScope !== 'alltime');
            var rec = isSeries ? (data.series || {wins:0,losses:0})
                    : isEvent ? (data.event || {wins:0,losses:0})
                    : data.alltime;
            var total = rec.wins + rec.losses;
            var evName = '';
            if (isEvent) {
                var evMatch = _h2hEvents.filter(function(e) { return e.event_slug === _h2hScope; })[0];
                evName = evMatch ? (evMatch.label || evMatch.event_name || '') : '';
            } else if (isSeries) {
                evName = seriesName;
            }
            var p1place = (isEvent && data.event) ? data.event.p1_placement : null;
            var p2place = (isEvent && data.event) ? data.event.p2_placement : null;
            _writeH2HFields({ scope: _h2hScope, eventName: evName,
                p1w: rec.wins, p1l: rec.losses, p2w: rec.losses, p2l: rec.wins,
                p1place: p1place, p2place: p2place });
            if (total === 0) {
                box.className = 'h2h-result muted';
                box.textContent = isSeries ? ('None in ' + seriesName + '.')
                    : isEvent ? 'None in this event.'
                    : 'No recorded matches.';
                return;
            }
            box.className = 'h2h-result';
            var pl1 = '', pl2 = '';
            if (isEvent && data.event) {
                if (data.event.p1_placement != null) pl1 = ' <span class="h2h-place">(' + _ordinal(data.event.p1_placement) + ')</span>';
                if (data.event.p2_placement != null) pl2 = '<span class="h2h-place">(' + _ordinal(data.event.p2_placement) + ')</span> ';
            }
            box.innerHTML = '<strong>' + _escH2H(n1) + pl1 + ' ' + rec.wins + '</strong> \u2013 '
                + '<strong>' + rec.losses + ' ' + pl2 + _escH2H(n2) + '</strong>';
        })
        .catch(function(e) { console.log('refreshH2H error:', e); });
}

function _writeH2HFields(opts) {
    // Mirror H2H state into scoreboard.json via the normal send path.
    // opts: { scope, eventName, p1w, p1l, p2w, p2l, p1place, p2place }
    jsonData.h2hScope            = opts.scope || 'alltime';
    jsonData.h2hEventName        = opts.eventName || '';
    jsonData.h2hSeriesName       = (opts.scope && opts.scope.indexOf('series:') === 0) ? opts.eventName || '' : '';
    jsonData.p1MatchupWins       = (opts.p1w != null) ? opts.p1w : '';
    jsonData.p1MatchupLosses     = (opts.p1l != null) ? opts.p1l : '';
    jsonData.p2MatchupWins       = (opts.p2w != null) ? opts.p2w : '';
    jsonData.p2MatchupLosses     = (opts.p2l != null) ? opts.p2l : '';
    jsonData.p1EventPlacement    = (opts.p1place != null) ? opts.p1place : '';
    jsonData.p2EventPlacement    = (opts.p2place != null) ? opts.p2place : '';
    jsonData.p1EventPlacementText = (opts.p1place != null) ? _ordinal(opts.p1place) : '';
    jsonData.p2EventPlacementText = (opts.p2place != null) ? _ordinal(opts.p2place) : '';
    // Top8 pushes state via sendJsonToEndpoint (there is no sendJSON here);
    // the old guarded sendJSON call silently no-oped, so H2H fields and the
    // show/hide toggle never reached scoreboard.json / the overlays.
    if (typeof sendJsonToEndpoint === 'function') sendJsonToEndpoint("updatealldata");
}

function toggleH2HVisible() {
    jsonData.h2hVisible = !jsonData.h2hVisible;
    var btn = document.getElementById('h2hVisibleBtn');
    if (btn) btn.textContent = jsonData.h2hVisible ? window.t('t8_hide_stream') : window.t('t8_show_stream');
    // refreshH2H recomputes + sends; if there aren't two resolvable players it
    // still must push the visibility flag, so fall back to a direct send.
    if (typeof refreshH2H === 'function') refreshH2H();
    else if (typeof sendJsonToEndpoint === 'function') sendJsonToEndpoint("updatealldata");
}

function _ordinal(n) {
    if (n == null) return '';
    var s = ['th', 'st', 'nd', 'rd'], v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function _escH2H(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
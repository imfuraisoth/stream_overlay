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
}

function updateElement(id, value) {
	if (value != null && value.length > 0) {
		safeEl(id).value = value;
	}
}

// ── LOCAL PLAYER PERSISTENCE (shared with Event Dashboard) ────────
function saveLocalPlayerName(name) {
    if (!name || !name.trim()) return;
    fetch('/saveLocalPlayer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim() })
    }).catch(function(e) { console.log('saveLocalPlayer error:', e); });
}

function loadLocalPlayersIntoDatalist() {
    var source = localStorage.getItem('player_source') || 'both';
    var dl = document.getElementById('next_player_suggestions');
    if (!dl) return;

    // Clear and rebuild based on preference
    // Start.gg players are already in the datalist from populateTop8PlayerData —
    // so for 'startgg' mode we leave whatever is there; for 'local' we clear first
    if (source === 'local') {
        dl.innerHTML = '';
    }

    if (source === 'local' || source === 'both') {
        fetch('/getLocalPlayers')
            .then(function(r) { return r.json(); })
            .then(function(names) {
                if (!names || !names.length) return;
                var existing = new Set(Array.from(dl.options).map(function(o) { return o.value; }));
                names.forEach(function(name) {
                    if (!existing.has(name)) {
                        var opt = document.createElement('option');
                        opt.value = name;
                        dl.appendChild(opt);
                    }
                });
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
    // Rebuild datalist immediately
    var dl = document.getElementById('next_player_suggestions');
    if (!dl) return;
    dl.innerHTML = '';
    if (src === 'startgg' || src === 'both') {
        playersMap.forEach(function(_, name) {
            var opt = document.createElement('option');
            opt.value = name; dl.appendChild(opt);
        });
    }
    if (src === 'local' || src === 'both') {
        loadLocalPlayersIntoDatalist();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    var src = localStorage.getItem('player_source') || 'both';
    ['both','startgg','local'].forEach(function(s) {
        var btn = document.getElementById('t8srcBtn' + s.charAt(0).toUpperCase() + s.slice(1));
        if (btn) btn.classList.toggle('active', s === src);
    });
    loadLocalPlayersIntoDatalist();
});

function updatePlayer1() {
	jsonData.p1Name = safeEl("form_name_1p").value;
    saveLocalPlayerName(jsonData.p1Name);
	sendJsonToEndpoint('updateCurrentPlayers');
}

function updatePlayer2() {
	jsonData.p2Name = safeEl("form_name_2p").value;
    saveLocalPlayerName(jsonData.p2Name);
	sendJsonToEndpoint('updateCurrentPlayers');
}

function updateTeam1() {
	jsonData.p1Team = safeEl("form_team_1p").value;
	sendJsonToEndpoint('updateCurrentPlayers');
}

function updateTeam2() {
	jsonData.p2Team = safeEl("form_team_2p").value;
	sendJsonToEndpoint('updateCurrentPlayers');
}

function updateNextPlayer1() {
	jsonData.nextplayer1 = safeEl("form_next_round_name_1p").value;
    saveLocalPlayerName(jsonData.nextplayer1);
	sendJsonToEndpoint('updateNextPlayers');
}

function updateNextPlayer2() {
	jsonData.nextplayer2 = safeEl("form_next_round_name_2p").value;
    saveLocalPlayerName(jsonData.nextplayer2);
	sendJsonToEndpoint('updateNextPlayers');
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

function resetNamesAndScore() {
	safeEl("form_name_1p").value = "";
	safeEl("form_name_2p").value = "";
	safeEl("form_team_1p").value = "";
	safeEl("form_team_2p").value = "";
	safeEl("form_score_1p").value = "0";
	safeEl("form_score_2p").value = "0";
	safeEl("dropdown_country_current_1").value = "US";
    safeEl("dropdown_country_current_2").value = "US";
	jsonData.p1Name = "";
	jsonData.p2Name = "";
	jsonData.p1Team = "";
	jsonData.p2Team = "";
	jsonData.p1Country = "US";
	jsonData.p2Country = "US";
	jsonData.p1Score = "0";
	jsonData.p2Score = "0";
	jsonData.p1Seed = "";
	jsonData.p2Seed = "";
	sendJsonToEndpoint("updatealldata");
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
        saveLocalPlayerName(value);
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
            if (!response.ok) { alert('Nothing to undo.'); return null; }
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
        alert("Player 1 and player 2 scores same value: " + data.p1Score + ". Update scores then try again.");
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
        setButtonColourAndText("rectangle_button_18", "#14BF01", "In Progress");
    } else {
        setButtonColourAndText("rectangle_button_18", "#675267", "Start Top 8");
    }
}

function setButtonColourAndText(id, bgColour, text) {
    var element = safeEl(id);
    element.style.background = bgColour;
    element.innerText = text;
    element.style.color = "white";
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
}

function highlightCurrentRoundForms(round) {
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

function resetTop8() {
    fetch('/resetTop8', { method: 'POST' })
        .then(function(response) {
            if (response.ok) {
                safeEl("rectangle_button_18").style.background = "#675267";
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

            // Populate datalist based on source preference
            var source = localStorage.getItem('player_source') || 'both';
            nextPlaySuggestions.innerHTML = '';
            if (source === 'startgg' || source === 'both') {
                playersMap.forEach(function(_, name) {
                    const option = document.createElement('option');
                    option.value = name;
                    nextPlaySuggestions.appendChild(option);
                });
            }
            if (source === 'local' || source === 'both') {
                loadLocalPlayersIntoDatalist();
            }
        })
        .catch(function (err) {
              console.log('error: ' + err);
            });
}

getDataFromServer();
getStartggInfo();
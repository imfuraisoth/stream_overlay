// ── LOCAL PLAYER PERSISTENCE ──────────────────────────────────────
// Saves any manually entered name to data/local_players.json on the server
// and merges them into the next_player_suggestions datalist on load.

var _playerSource = localStorage.getItem('player_source') || 'both';

function setPlayerSource(src) {
    _playerSource = src;
    localStorage.setItem('player_source', src);
    // Update toggle button states
    ['both','startgg','local'].forEach(function(s) {
        var btn = document.getElementById('srcBtn' + s.charAt(0).toUpperCase() + s.slice(1));
        if (btn) btn.classList.toggle('active', s === src);
    });
    // Repopulate datalist from scratch with new preference
    rebuildNamePickers();
}

function populateNamePickers(names) {
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
    var dl = document.getElementById('next_player_suggestions');
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

function rebuildNamePickers() {
    // Clear and rebuild all pickers and datalist based on current source preference
    document.querySelectorAll('select.name-picker').forEach(function(sel) {
        sel.innerHTML = '<option value="">▾</option>';
    });
    var dl = document.getElementById('next_player_suggestions');
    if (dl) dl.innerHTML = '';
    var names = [];
    if (_playerSource === 'startgg' || _playerSource === 'both') {
        playersMap.forEach(function(_, name) { names.push(name); });
    }
    if (_playerSource === 'local' || _playerSource === 'both') {
        _localPlayersByName.forEach(function(_, name) { names.push(name); });
    }
    names.sort(function(a,b) { return a.toLowerCase().localeCompare(b.toLowerCase()); });
    // Deduplicate
    names = names.filter(function(v,i,a) { return a.indexOf(v) === i; });
    populateNamePickers(names);
}

function refreshDatalist() { rebuildNamePickers(); }

function pickName(inputId, sel, updateFn) {
    if (!sel.value) return;
    var input = document.getElementById(inputId);
    if (input) { input.value = sel.value; }
    sel.selectedIndex = 0; // reset picker back to ▾
    if (updateFn) updateFn();
}

var _localPlayersMap = new Map();     // id   -> player record
var _localPlayersByName = new Map(); // name -> player record (for fast lookup)

function refreshSocialFields() {
    if (!jsonData) return;
    var changed = false;
    function applySocial(name, handleKey, platformKey) {
        var p = _localPlayersByName.get(name);
        var h  = p ? (p.social_handle   || '') : '';
        var pl = p ? (p.social_platform || '') : '';
        if (jsonData[handleKey] !== h || jsonData[platformKey] !== pl) {
            jsonData[handleKey]   = h;
            jsonData[platformKey] = pl;
            changed = true;
        }
    }
    applySocial(jsonData.p1Name,      'p1SocialHandle',    'p1SocialPlatform');
    applySocial(jsonData.p2Name,      'p2SocialHandle',    'p2SocialPlatform');
    applySocial(jsonData.nextplayer1, 'nextSocial1Handle', 'nextSocial1Platform');
    applySocial(jsonData.nextplayer2, 'nextSocial2Handle', 'nextSocial2Platform');
    updateSocialDisplays();
    if (changed) sendJSON();
}

const SOCIAL_ICONS = { twitter: '𝕏', bluesky: '🦋', instagram: '📷', facebook: '👤' };

function updateSocialDisplays() {
    function setDisplay(rowId, valueId, handle, platform) {
        var row = document.getElementById(rowId);
        var val = document.getElementById(valueId);
        if (!row || !val) return;
        if (handle) {
            var icon = SOCIAL_ICONS[platform] ? SOCIAL_ICONS[platform] + ' ' : '';
            val.textContent = icon + handle;
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    }
    setDisplay('p1SocialDisplay',   'p1SocialValue',   jsonData.p1SocialHandle,    jsonData.p1SocialPlatform);
    setDisplay('p2SocialDisplay',   'p2SocialValue',   jsonData.p2SocialHandle,    jsonData.p2SocialPlatform);
    setDisplay('next1SocialDisplay','next1SocialValue', jsonData.nextSocial1Handle, jsonData.nextSocial1Platform);
    setDisplay('next2SocialDisplay','next2SocialValue', jsonData.nextSocial2Handle, jsonData.nextSocial2Platform);
}

function saveLocalPlayerName(name, team, country) {
    if (!name || name.trim() === '') return;
    // Merge into existing map entry — never overwrite with blanks
    var existing = _localPlayersByName.get(name.trim()) || _localPlayersMap.get(name.trim()) || { name: name.trim() };
    if (team)    existing.team    = team;
    if (country) existing.country = country;
    existing.name = name.trim();
    _localPlayersMap.set(existing.id || name.trim(), existing);
    _localPlayersByName.set(name.trim(), existing);
    // Only send non-empty fields — never send blank socials that would
    // overwrite correctly stored values on the server
    var payload = { name: name.trim() };
    if (team)                     payload.team            = team;
    if (country)                  payload.country         = country;
    // Always send social fields even if empty so server clears them
    payload.social_handle   = existing.social_handle   || '';
    payload.social_platform = existing.social_platform || '';
    fetch('/saveLocalPlayer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }).then(function() {
        // Add to datalist immediately if local is in scope
        if (_playerSource === 'local' || _playerSource === 'both') {
            var dl = document.getElementById('next_player_suggestions');
            if (!dl) return;
            var existing = new Set(Array.from(dl.options).map(function(o) { return o.value; }));
            if (!existing.has(name.trim())) {
                var opt = document.createElement('option');
                opt.value = name.trim(); dl.appendChild(opt);
            }
        }
    }).catch(function(e) { console.log('saveLocalPlayer error:', e); });
}

function loadLocalPlayers() {
    fetch('/getLocalPlayers')
        .then(function(r) { return r.json(); })
        .then(function(players) {
            if (!players || !players.length) return;
            // Build lookup map for auto-fill
            players.forEach(function(p) {
                if (!p || !p.name) return;
                _localPlayersMap.set(p.id || p.name, p);
                _localPlayersByName.set(p.name, p);
            });
            // Write social fields for any players already on screen
            refreshSocialFields();
            populateNamePickers(players.map(function(p) { return typeof p === 'string' ? p : p.name; }));
            // Restore characters for currently displayed players now that map is loaded
            [1, 2].forEach(function(player) {
                var name = jsonData['p' + player + 'Name'];
                if (!name) return;
                var localPlayer = _localPlayersByName.get(name.trim());
                var game = charGetGame();
                var saved = (game && localPlayer && localPlayer.characters) ? localPlayer.characters[game] : null;
                if (saved && saved.file) {
                    jsonData['p' + player + 'Character']     = saved.character || '';
                    jsonData['p' + player + 'CharacterPack'] = saved.pack || '';
                    jsonData['p' + player + 'Palette']       = saved.palette || 0;
                    jsonData['p' + player + 'CharacterFile'] = saved.file || '';
                    var thumb   = document.getElementById('p' + player + 'CharThumb');
                    var label   = document.getElementById('p' + player + 'CharLabel');
                    var portrait = document.getElementById('p' + player + 'CharPortrait');
                    var packSel = document.getElementById('p' + player + 'CharPack');
                    if (thumb)   { thumb.src = '/' + saved.file; thumb.style.display = 'inline'; }
                    if (label)   label.textContent = saved.character + ' (' + saved.palette + ')';
                    if (portrait){ portrait.src = '/' + saved.file; portrait.style.display = 'block'; }
                    if (packSel) packSel.value = saved.pack;
                }
            });
        })
        .catch(function(e) { console.log('loadLocalPlayers error:', e); });
}

// On load: restore toggle state and seed datalist
document.addEventListener('DOMContentLoaded', function() {
    // Restore toggle button active state
    setPlayerSource(_playerSource);
    // Seed with local players if preference includes local
    if (_playerSource === 'local' || _playerSource === 'both') {
        loadLocalPlayers();
    }
});

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
}

function populateData(data) {
	updateElement("form_name_1p", data.p1Name);
	updateElement("form_name_2p", data.p2Name);
	updateElement("form_team_1p", data.p1Team);
	updateElement("form_team_2p", data.p2Team);
	updateElement("dropdown_round", data.round);
	updateElement("dropdown_next_round", data.nextRound);
	updateElement("form_score_1p", data.p1Score);
	updateElement("form_score_2p", data.p2Score);
	updateElement("dropdown_country_1p", data.p1Country);
	updateElement("dropdown_country_2p", data.p2Country);
    updateElement("dropdown_country_next1", data.nextcountry1);
    updateElement("dropdown_country_next2", data.nextcountry2);
	updateElement("form_next_round_team_1p", data.nextteam1);
	updateElement("form_next_round_name_1p", data.nextplayer1);
	updateElement("form_next_round_team_2p", data.nextteam2);
	updateElement("form_next_round_name_2p", data.nextplayer2);
	updateElement("form_results_name_1p", data.resultplayer1);
	updateElement("form_results_score_1p", data.resultscore1);
	updateElement("form_results_name_2p", data.resultplayer2);
	updateElement("form_results_score_2p", data.resultscore2);
	updateElement("form_ft", data.maxScore);
	jsonData = data;
	if (jsonData.p1Name == undefined) {
	    jsonData.p1Name = "";
	}
    if (jsonData.p2Name == undefined) {
        jsonData.p2Name = "";
    }
    if (jsonData.p1Score == undefined) {
        jsonData.p1Score = "0";
    }
    if (jsonData.p2Score == undefined) {
        jsonData.p2Score = "0";
    }
    if (jsonData.p1Seed == undefined) {
        jsonData.p1Seed = "";
    }
    if (jsonData.p2Seed == undefined) {
        jsonData.p2Seed = "";
    }
    if (jsonData.p1SocialHandle   == undefined) { jsonData.p1SocialHandle   = ""; }
    if (jsonData.p1SocialPlatform == undefined) { jsonData.p1SocialPlatform = ""; }
    if (jsonData.p2SocialHandle   == undefined) { jsonData.p2SocialHandle   = ""; }
    if (jsonData.p2SocialPlatform == undefined) { jsonData.p2SocialPlatform = ""; }
    if (jsonData.nextSocial1Handle   == undefined) { jsonData.nextSocial1Handle   = ""; }
    if (jsonData.nextSocial1Platform == undefined) { jsonData.nextSocial1Platform = ""; }
    if (jsonData.nextSocial2Handle   == undefined) { jsonData.nextSocial2Handle   = ""; }
    if (jsonData.nextSocial2Platform == undefined) { jsonData.nextSocial2Platform = ""; }
    refreshSocialFields();
	updateCurrentPlayerDisplay();
	// Restore character UI from scoreboard.json values
	function restoreCharUI(player) {
		var file = jsonData['p' + player + 'CharacterFile'];
		var char = jsonData['p' + player + 'Character'];
		var palette = jsonData['p' + player + 'Palette'];
		var pack = jsonData['p' + player + 'CharacterPack'];
		var thumb   = document.getElementById('p' + player + 'CharThumb');
		var label   = document.getElementById('p' + player + 'CharLabel');
		var portrait = document.getElementById('p' + player + 'CharPortrait');
		var packSel = document.getElementById('p' + player + 'CharPack');
		if (file) {
			if (thumb)   { thumb.src = '/' + file; thumb.style.display = 'inline'; }
			if (label)   label.textContent = char + ' (' + palette + ')';
			if (portrait){ portrait.src = '/' + file; portrait.style.display = 'block'; }
			if (packSel && pack) packSel.value = pack;
		} else {
			if (thumb)   { thumb.src = ''; thumb.style.display = 'none'; }
			if (label)   label.textContent = '—';
			if (portrait){ portrait.src = ''; portrait.style.display = 'none'; }
		}
	}
	restoreCharUI(1);
	restoreCharUI(2);
}

const countriesDropDownList = ['US', 'CA', 'JP', 'KR', 'MX', 'GB', 'ES', 'FR', 'FI', 'SE', 'PR', 'BR'];
const dropDownSelects = ['dropdown_country_1p', 'dropdown_country_2p', 'dropdown_country_next1', 'dropdown_country_next2'];
var currentPlayerInfoDisplay = "";
var currentScoreInfoDisplay = "";

function populateCountrySelectDropDown() {
  dropDownSelects.forEach(selectId => {
	const selectElement = document.getElementById(selectId);
	countriesDropDownList.forEach(country => {
	  const option = document.createElement('option');
	  option.textContent = country;
	  selectElement.appendChild(option);
	});
  });
}

function updateElementEmptyOkay(id, value) {
	if (value != null) {
		document.getElementById(id).value = value;
	}
}

function updateElement(id, value) {
	if (value != null && value.length > 0) {
		document.getElementById(id).value = value;
	}
}

function updateCurrentPlayerDisplay() {
	var names = jsonData.p1Name + " vs " + jsonData.p2Name;
	var scores = jsonData.p1Score + " - " + jsonData.p2Score;
	if (currentPlayerInfoDisplay != names) {
		currentPlayerInfoDisplay = names;
		var nameElement = document.getElementById("currentPlayerInfoDisplay");
		nameElement.style.opacity = "0";
		setTimeout(function() {
			nameElement.textContent = currentPlayerInfoDisplay;
			nameElement.style.opacity = "1";
		  }, 1000);
	}
	if (currentScoreInfoDisplay != scores) {
		currentScoreInfoDisplay = scores;
		var scoreElement = document.getElementById("currentScoreInfoDisplay");
		scoreElement.style.opacity = "0";
		setTimeout(function() {
			scoreElement.textContent = currentScoreInfoDisplay;
			scoreElement.style.opacity = "1";
		  }, 1000);
	}
}

function updatePlayer1() {
    jsonData.p1Name = document.getElementById("form_name_1p").value;
    jsonData.p1Seed = "";
    if (playersMap.has(jsonData.p1Name)) {
        jsonData.p1Seed = playersMap.get(jsonData.p1Name).seed;
    } else if (nextPlayersMap.has(jsonData.p1Name)) {
        jsonData.p1Seed = nextPlayersMap.get(jsonData.p1Name).seed;
    }
    // Auto-fill team/country/social from local DB if available
    var localPlayer = _localPlayersByName.get(jsonData.p1Name);
    if (localPlayer) {
        jsonData.p1Team = localPlayer.team || '';
        document.getElementById("form_team_1p").value = localPlayer.team || '';
        if (localPlayer.country) {
            jsonData.p1Country = localPlayer.country;
            var sel = document.getElementById("dropdown_country_1p");
            if (sel) sel.value = localPlayer.country;
        }
        jsonData.p1SocialHandle   = localPlayer.social_handle   || '';
        jsonData.p1SocialPlatform = localPlayer.social_platform || '';
        // Restore saved character for current game
        var _game1 = charGetGame();
        var _saved1 = (_game1 && localPlayer.characters) ? localPlayer.characters[_game1] : null;
        if (_saved1 && _saved1.file) {
            jsonData.p1Character = _saved1.character || ''; jsonData.p1CharacterPack = _saved1.pack || '';
            jsonData.p1Palette = _saved1.palette || 0; jsonData.p1CharacterFile = _saved1.file || '';
            var _t1 = document.getElementById('p1CharThumb'); var _l1 = document.getElementById('p1CharLabel'); var _p1 = document.getElementById('p1CharPortrait');
            if (_t1) { _t1.src = '/' + _saved1.file; _t1.style.display = 'inline'; }
            if (_l1) _l1.textContent = _saved1.character + ' (' + _saved1.palette + ')';
            if (_p1) { _p1.src = '/' + _saved1.file; _p1.style.display = 'block'; }
            var _pk1 = document.getElementById('p1CharPack'); if (_pk1) _pk1.value = _saved1.pack;
        } else { clearCharacterSelect(1); }
    } else {
        jsonData.p1SocialHandle   = '';
        jsonData.p1SocialPlatform = '';
        clearCharacterSelect(1);
    }
    saveLocalPlayerName(jsonData.p1Name, jsonData.p1Team, jsonData.p1Country);
    updateCurrentPlayerDisplay();
    sendJSON();
}

function updatePlayer2() {
    jsonData.p2Name = document.getElementById("form_name_2p").value;
    jsonData.p2Seed = "";
    if (playersMap.has(jsonData.p2Name)) {
        jsonData.p2Seed = playersMap.get(jsonData.p2Name).seed;
    } else if (nextPlayersMap.has(jsonData.p2Name)) {
        jsonData.p2Seed = nextPlayersMap.get(jsonData.p2Name).seed;
    }
    // Auto-fill team/country/social from local DB if available
    var localPlayer = _localPlayersByName.get(jsonData.p2Name);
    if (localPlayer) {
        jsonData.p2Team = localPlayer.team || '';
        document.getElementById("form_team_2p").value = localPlayer.team || '';
        if (localPlayer.country) {
            jsonData.p2Country = localPlayer.country;
            var sel = document.getElementById("dropdown_country_2p");
            if (sel) sel.value = localPlayer.country;
        }
        jsonData.p2SocialHandle   = localPlayer.social_handle   || '';
        jsonData.p2SocialPlatform = localPlayer.social_platform || '';
        // Restore saved character for current game
        var _game2 = charGetGame();
        var _saved2 = (_game2 && localPlayer.characters) ? localPlayer.characters[_game2] : null;
        if (_saved2 && _saved2.file) {
            jsonData.p2Character = _saved2.character || ''; jsonData.p2CharacterPack = _saved2.pack || '';
            jsonData.p2Palette = _saved2.palette || 0; jsonData.p2CharacterFile = _saved2.file || '';
            var _t2 = document.getElementById('p2CharThumb'); var _l2 = document.getElementById('p2CharLabel'); var _p2 = document.getElementById('p2CharPortrait');
            if (_t2) { _t2.src = '/' + _saved2.file; _t2.style.display = 'inline'; }
            if (_l2) _l2.textContent = _saved2.character + ' (' + _saved2.palette + ')';
            if (_p2) { _p2.src = '/' + _saved2.file; _p2.style.display = 'block'; }
            var _pk2 = document.getElementById('p2CharPack'); if (_pk2) _pk2.value = _saved2.pack;
        } else { clearCharacterSelect(2); }
    } else {
        jsonData.p2SocialHandle   = '';
        jsonData.p2SocialPlatform = '';
        clearCharacterSelect(2);
    }
    saveLocalPlayerName(jsonData.p2Name, jsonData.p2Team, jsonData.p2Country);
    updateCurrentPlayerDisplay();
    sendJSON();
}

function updateTeam1() {
    jsonData.p1Team = document.getElementById("form_team_1p").value;
    saveLocalPlayerName(jsonData.p1Name, jsonData.p1Team, jsonData.p1Country);
    sendJSON();
}

function updateTeam2() {
    jsonData.p2Team = document.getElementById("form_team_2p").value;
    saveLocalPlayerName(jsonData.p2Name, jsonData.p2Team, jsonData.p2Country);
    sendJSON();
}

function updateNextPlayer1() {
	jsonData.nextplayer1 = document.getElementById("form_next_round_name_1p").value;
    saveLocalPlayerName(jsonData.nextplayer1, jsonData.nextteam1, jsonData.nextcountry1);
    // Auto-fill from local DB
    var localP1 = _localPlayersByName.get(jsonData.nextplayer1);
    if (localP1) {
        if (localP1.team) { jsonData.nextteam1 = localP1.team; document.getElementById("form_next_round_team_1p").value = localP1.team; }
        if (localP1.country) { jsonData.nextcountry1 = localP1.country; document.getElementById("dropdown_country_next1").value = localP1.country; }
        jsonData.nextSocial1Handle   = localP1.social_handle   || '';
        jsonData.nextSocial1Platform = localP1.social_platform || '';
    }
	if (nextPlayersMap.has(jsonData.nextplayer1)) {
        // Auto set team name and player 2 name to the opponent's name
        match = nextPlayersMap.get(jsonData.nextplayer1);
        player1Info = getPlayerInfo(match, jsonData.nextplayer1);
        player2Info = getOtherPlayerInfo(match, jsonData.nextplayer1);
        jsonData.nextteam1 = player1Info.team;
        document.getElementById("form_next_round_team_1p").value = jsonData.nextteam1;
        jsonData.nextcountry1 = player1Info.country;
        document.getElementById("dropdown_country_next1").value = jsonData.nextcountry1;
        jsonData.nextplayer2 = player2Info.name;
        document.getElementById("form_next_round_name_2p").value = jsonData.nextplayer2;
        jsonData.nextteam2 = player2Info.team;
        document.getElementById("form_next_round_team_2p").value = jsonData.nextteam2;
        jsonData.nextcountry2 = player2Info.country;
        document.getElementById("dropdown_country_next2").value = jsonData.nextcountry2;
	} else if (playersMap.has(jsonData.nextplayer1)) {
	    player = playersMap.get(jsonData.nextplayer1);
        jsonData.nextteam1 = player.team;
        document.getElementById("form_next_round_team_1p").value = jsonData.nextteam1;
        jsonData.nextcountry1 = player.country;
        document.getElementById("dropdown_country_next1").value = jsonData.nextcountry1;
	}
	sendJSON();
}

function updateNextPlayer2() {
	jsonData.nextplayer2 = document.getElementById("form_next_round_name_2p").value;
    saveLocalPlayerName(jsonData.nextplayer2, jsonData.nextteam2, jsonData.nextcountry2);
    // Auto-fill from local DB
    var localP2 = _localPlayersByName.get(jsonData.nextplayer2);
    if (localP2) {
        if (localP2.team) { jsonData.nextteam2 = localP2.team; document.getElementById("form_next_round_team_2p").value = localP2.team; }
        if (localP2.country) { jsonData.nextcountry2 = localP2.country; document.getElementById("dropdown_country_next2").value = localP2.country; }
        jsonData.nextSocial2Handle   = localP2.social_handle   || '';
        jsonData.nextSocial2Platform = localP2.social_platform || '';
    }
    if (nextPlayersMap.has(jsonData.nextplayer2)) {
        // Auto set team name and player 1 name to the opponent's name
        match = nextPlayersMap.get(jsonData.nextplayer2);
        player2Info = getPlayerInfo(match, jsonData.nextplayer2);
        player1Info = getOtherPlayerInfo(match, jsonData.nextplayer2);
        jsonData.nextteam2 = player2Info.team;
        document.getElementById("form_next_round_team_2p").value = jsonData.nextteam2;
        jsonData.nextcountry2 = player2Info.country;
        document.getElementById("dropdown_country_next2").value = jsonData.nextcountry2;
        jsonData.nextplayer1 = player1Info.name;
        document.getElementById("form_next_round_name_1p").value = jsonData.nextplayer1;
        jsonData.nextteam1 = player1Info.team;
        document.getElementById("form_next_round_team_1p").value = jsonData.nextteam1;
        jsonData.nextcountry1 = player1Info.country;
        document.getElementById("dropdown_country_next1").value = jsonData.nextcountry1;
    } else if (playersMap.has(jsonData.nextplayer2)) {
        player = playersMap.get(jsonData.nextplayer2);
        jsonData.nextteam2 = player.team;
        document.getElementById("form_next_round_team_2p").value = jsonData.nextteam2;
        jsonData.nextcountry2 = player.country;
        document.getElementById("dropdown_country_next2").value = jsonData.nextcountry2;
    }
	sendJSON();
}

function getPlayerInfo(match, playerName) {
    if (match.player1.name === playerName) {
        return match.player1;
    }
    return match.player2;
}

function getOtherPlayerInfo(match, playerName) {
    if (match.player1.name === playerName) {
        return match.player2;
    }
    return match.player1;
}

function updateNextTeam1() {
	jsonData.nextteam1 = document.getElementById("form_next_round_team_1p").value;
	sendJSON();
}

function updateNextTeam2() {
	jsonData.nextteam2 = document.getElementById("form_next_round_team_2p").value;
	sendJSON();
}

function updateScore1() {
	jsonData.p1Score = document.getElementById("form_score_1p").value;
	updateCurrentPlayerDisplay();
	sendJsonToEndpoint("updateP1score");
}

function updateScore2() {
	jsonData.p2Score = document.getElementById("form_score_2p").value;
	updateCurrentPlayerDisplay();
	sendJsonToEndpoint("updateP2score");
}

function updateRound() {
	jsonData.round = document.getElementById("dropdown_round").value;
	sendJSON();
}

function updateNextRound() {
	jsonData.nextRound = document.getElementById("dropdown_next_round").value;
	sendJSON();
}

function updateMaxScore() {
	jsonData.maxScore = document.getElementById("form_ft").value;
	sendJSON();
}

function updateNextCountry1() {
    jsonData.nextcountry1 = document.getElementById("dropdown_country_next1").value;
    saveLocalPlayerName(jsonData.nextplayer1, jsonData.nextteam1, jsonData.nextcountry1);
    sendJSON();
}

function updateNextCountry2() {
    jsonData.nextcountry2 = document.getElementById("dropdown_country_next2").value;
    saveLocalPlayerName(jsonData.nextplayer2, jsonData.nextteam2, jsonData.nextcountry2);
    sendJSON();
}

function resetNamesAndScore() {
	document.getElementById("form_name_1p").value = "";
	document.getElementById("form_name_2p").value = "";
	document.getElementById("form_team_1p").value = "";
	document.getElementById("form_team_2p").value = "";
	document.getElementById("form_score_1p").value = "0";
	document.getElementById("form_score_2p").value = "0";
	document.getElementById("dropdown_country_1p").value = "US";
    document.getElementById("dropdown_country_2p").value = "US";
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
	updateCurrentPlayerDisplay();
	sendJsonToEndpoint("updatealldata");
}

function reversePlayerNames() {
	var p1 = document.getElementById("form_name_1p").value;
	var p2 = document.getElementById("form_name_2p").value;
	var t1 = document.getElementById("form_team_1p").value;
	var t2 = document.getElementById("form_team_2p").value;
	var c1 = document.getElementById("dropdown_country_1p").value;
	var c2 = document.getElementById("dropdown_country_2p").value;
	document.getElementById("form_name_1p").value = p2;
	document.getElementById("form_name_2p").value = p1;
	document.getElementById("form_team_1p").value = t2;
	document.getElementById("form_team_2p").value = t1;
	document.getElementById("dropdown_country_1p").value = c2;
	document.getElementById("dropdown_country_2p").value = c1;
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
	updateCurrentPlayerDisplay();
	sendJSON();
}

function reverseScores() {
    fetch('/getdata')
        .then(function(response) {
            return response.json();
        }).then(function (data) {
        updateElement("form_score_1p", data.p1Score);
        updateElement("form_score_2p", data.p2Score);
        var p1 = document.getElementById("form_score_1p").value;
        var p2 = document.getElementById("form_score_2p").value;
        document.getElementById("form_score_1p").value = p2;
        document.getElementById("form_score_2p").value = p1;
        jsonData.p1Score = p2;
        jsonData.p2Score = p1;
        updateCurrentPlayerDisplay();
        sendJsonToEndpoint('updateCurrentScore');
    })
        .catch(function (err) {
        console.log('error: ' + err);
    });
}

function addScoreP1() {
	var score = parseInt(document.getElementById("form_score_1p").value);
	score++;
	jsonData.p1Score = score.toString();
	document.getElementById("form_score_1p").value = jsonData.p1Score;
	updateCurrentPlayerDisplay();
	sendJsonToEndpoint("updateP1score");
}

function subtractScoreP1() {
	var score = parseInt(document.getElementById("form_score_1p").value);
	if (score <= 0) {
		return;
	}
	score--;
	jsonData.p1Score = score.toString();
	document.getElementById("form_score_1p").value = jsonData.p1Score;
	updateCurrentPlayerDisplay();
	sendJsonToEndpoint("updateP1score");
}

function addScoreP2() {
	var score = parseInt(document.getElementById("form_score_2p").value);
	score++;
	jsonData.p2Score = score.toString();
	document.getElementById("form_score_2p").value = jsonData.p2Score;
	updateCurrentPlayerDisplay();
	sendJsonToEndpoint("updateP2score");
}

function subtractScoreP2() {
	var score = parseInt(document.getElementById("form_score_2p").value);
	if (score <= 0) {
		return;
	}
	score--;
	jsonData.p2Score = score.toString();
	document.getElementById("form_score_2p").value = jsonData.p2Score;
	updateCurrentPlayerDisplay();
	sendJsonToEndpoint("updateP2score");
}

function resetScores() {
	document.getElementById("form_score_1p").value = "0";
	document.getElementById("form_score_2p").value = "0";
	jsonData.p1Score = "0";
	jsonData.p2Score = "0";
	updateCurrentPlayerDisplay();
	sendJsonToEndpoint('updateCurrentScore');
}

function resetAll() {
	document.getElementById("form_name_1p").value = "";
	document.getElementById("form_name_2p").value = "";
	document.getElementById("form_team_1p").value = "";
	document.getElementById("form_team_2p").value = "";
	document.getElementById("form_score_1p").value = "0";
	document.getElementById("form_score_2p").value = "0";
	document.getElementById("form_next_round_team_1p").value = "";
	document.getElementById("form_next_round_name_1p").value = "";
	document.getElementById("form_next_round_team_2p").value = "";
	document.getElementById("form_next_round_name_2p").value = "";
	document.getElementById("dropdown_country_next1").value = "US";
	document.getElementById("dropdown_country_next2").value = "US";
	document.getElementById("form_results_name_1p").value = "";
	document.getElementById("form_results_score_1p").value = "";
	document.getElementById("form_results_name_2p").value = "";
	document.getElementById("form_results_score_2p").value = "";
	document.getElementById("form_ft").value = "";
	document.getElementById("dropdown_round").value = "Casuals";
	
	jsonData.p1Name = "";
	jsonData.p2Name = "";
	jsonData.p1Team = "";
	jsonData.p2Team = "";
    jsonData.p1Seed = "";
    jsonData.p2Seed = "";
	jsonData.p1Score = "0";
	jsonData.p2Score = "0";
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
	jsonData.nextRound = "Casuals";
	jsonData.current_game = "";
	updateCurrentPlayerDisplay();
	sendJsonToEndpoint("updatealldata");
}

function countryDropdown1() {
    var c1 = document.getElementById("dropdown_country_1p");
    jsonData.p1Country = c1.options[c1.selectedIndex].text;
    saveLocalPlayerName(jsonData.p1Name, jsonData.p1Team, jsonData.p1Country);
    sendJSON();
}

function countryDropdown2() {
    var c2 = document.getElementById("dropdown_country_2p");
    jsonData.p2Country = c2.options[c2.selectedIndex].text;
    saveLocalPlayerName(jsonData.p2Name, jsonData.p2Team, jsonData.p2Country);
    sendJSON();
}

function clearCharacterSelect(player) {
    jsonData['p' + player + 'Character']     = '';
    jsonData['p' + player + 'CharacterPack'] = '';
    jsonData['p' + player + 'Palette']       = 0;
    jsonData['p' + player + 'CharacterFile'] = '';
    var thumb   = document.getElementById('p' + player + 'CharThumb');
    var label   = document.getElementById('p' + player + 'CharLabel');
    var portrait = document.getElementById('p' + player + 'CharPortrait');
    if (thumb)    { thumb.src = ''; thumb.style.display = 'none'; }
    if (label)    label.textContent = '—';
    if (portrait) { portrait.src = ''; portrait.style.display = 'none'; }
    // Clear selected highlight in popover
    var popover = document.getElementById('p' + player + 'CharPopover');
    if (popover) popover.querySelectorAll('.char-palette-thumb.selected').forEach(function(el) { el.classList.remove('selected'); });
}

function nextRound() {
    clearCharacterSelect(1);
    clearCharacterSelect(2);
    fetch('/getdata')
        .then(function(response) {
            return response.json();
        })
        .then(function (data) {
        if (compareScores(data)) {
            reportScoresToStartgg(data)
            nextRoundUpdate(data);
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

	document.getElementById("form_score_1p").value = data.p1Score;
	document.getElementById("form_score_2p").value = data.p2Score;
    if (data.p1Score == data.p2Score) {
        alert("Player 1 and player 2 scores same value: " + data.p1Score + ". Update scores then try again.");
        return false;
    }
    return true;
}

function reportScoresToStartgg(data) {
    var winner = data.p1Name;
    var p2win = false;
    if (data.p2Score > data.p1Score) {
        winner = data.p2Name;
        p2win = true;
    }

    if (currentSet == null) {
        // We don't know about this set in start.gg so just ignore it
        return;
    }
    // Check the names in the set matches
    if (data.p1Name != currentSet.player1.name && data.p1Name != currentSet.player2.name) {
        // Names don't match, don't report it
        return;
    }
    if (data.p2Name != currentSet.player2.name && data.p2Name != currentSet.player2.name) {
        // Names don't match, don't report it
        return;
    }
    var setId = currentSet.set_id
    var winnerId = p2win ? currentSet.player2.entrant_id : currentSet.player1.entrant_id;
    var loserId = p2win ? currentSet.player1.entrant_id : currentSet.player2.entrant_id;
    const winnerData = {
      setId: setId,
      winnerId: winnerId,
      loserId: loserId,
      entrant1Score: data.p1Score,
      entrant2Score: data.p2Score
    };

    sendJsonDataToEndpoint(winnerData, "reportWinnerToStartgg");
}

function nextRoundUpdate(data) {
	jsonData.resultscore1 = data.p1Score;
	jsonData.resultscore2 = data.p2Score;
	jsonData.resultplayer1 = data.p1Name;
	jsonData.resultplayer2 = data.p2Name;
	jsonData.current_game = data.current_game;
	if (data.current_game) { charRefreshPacks(); }
    jsonData.com1 = data.com1;
    jsonData.com2 = data.com2;
    jsonData.soc1 = data.soc1;
    jsonData.soc2 = data.soc2;
    document.getElementById("dropdown_round").value = data.nextRound;
    jsonData.round = data.nextRound;

	document.getElementById("dropdown_round").value = jsonData.round;
	document.getElementById("form_results_score_1p").value = jsonData.resultscore1;
	document.getElementById("form_results_score_2p").value = jsonData.resultscore2;
	document.getElementById("form_results_name_1p").value = jsonData.resultplayer1;
	document.getElementById("form_results_name_2p").value = jsonData.resultplayer2;
	
	document.getElementById("form_results_score_1p").style.opacity  = 0.5;
	document.getElementById("form_results_score_2p").style.opacity  = 0.5;
	document.getElementById("form_results_name_1p").style.opacity  = 0.5;
	document.getElementById("form_results_name_2p").style.opacity  = 0.5;
	
    document.getElementById("dropdown_country_1p").value = data.nextcountry1;
    document.getElementById("dropdown_country_2p").value = data.nextcountry2;
	document.getElementById("form_team_1p").value = data.nextteam1;
	document.getElementById("form_name_1p").value = data.nextplayer1;
	document.getElementById("form_team_2p").value = data.nextteam2;
	document.getElementById("form_name_2p").value = data.nextplayer2;
	jsonData.p1Team = data.nextteam1;
	jsonData.p2Team = data.nextteam2;
	jsonData.p1Name = data.nextplayer1;
	jsonData.p2Name = data.nextplayer2;
	jsonData.p1Country = data.nextcountry1;
	jsonData.p2Country = data.nextcountry2;

    jsonData.p1Seed = "";
    jsonData.p2Seed = "";
	// If player is in player map, try to set the seed value
	if (playersMap.has(jsonData.p1Name)) {
	    jsonData.p1Seed = playersMap.get(jsonData.p1Name).seed;
	} else if (nextPlayersMap.has(jsonData.p1Name)) {
        jsonData.p1Seed = nextPlayersMap.get(jsonData.p1Name).seed;
    }
    if (playersMap.has(jsonData.p2Name)) {
        jsonData.p2Seed = playersMap.get(jsonData.p2Name).seed;
    } else if (nextPlayersMap.has(jsonData.p2Name)) {
        jsonData.p2Seed = nextPlayersMap.get(jsonData.p2Name).seed;
    }

	document.getElementById("form_score_1p").value = "0";
	document.getElementById("form_score_2p").value = "0";

	jsonData.p1Score = "0";
	jsonData.p2Score = "0";
	currentSet = nextPlayersMap.get(data.nextplayer1);
	if (currentSet == null) {
	    currentSet = nextPlayersMap.get(data.nextplayer2);
	}
    nextPlayersMap.delete(document.getElementById("form_next_round_name_1p").value)
    nextPlayersMap.delete(document.getElementById("form_next_round_name_2p").value)
    rebuildPlayerSuggestion();
    if (nextPlayersMap.size > 0) {
        // select next players from queue
        // Get the iterator
        let iterator = nextPlayersMap.entries();

        // Get the first key-value pair
        let firstEntry = iterator.next().value[1];
        jsonData.nextteam1 = firstEntry.player1.team;
        jsonData.nextplayer1 = firstEntry.player1.name;
        jsonData.nextcountry1 = firstEntry.player1.country;
        jsonData.nextteam2 = firstEntry.player2.team;
        jsonData.nextplayer2 = firstEntry.player2.name;
        jsonData.nextcountry2 = firstEntry.player2.country;
    } else {
    	jsonData.nextteam1 = "";
    	jsonData.nextplayer1 = "";
    	jsonData.nextteam2 = "";
    	jsonData.nextplayer2 = "";
        jsonData.nextcountry1 = "US";
        jsonData.nextcountry2 = "US";
    }
    document.getElementById("form_next_round_team_1p").value = jsonData.nextteam1;
    document.getElementById("form_next_round_name_1p").value = jsonData.nextplayer1;
    document.getElementById("form_next_round_team_2p").value = jsonData.nextteam2;
    document.getElementById("form_next_round_name_2p").value = jsonData.nextplayer2;
    document.getElementById("dropdown_country_next1").value = jsonData.nextcountry1;
    document.getElementById("dropdown_country_next2").value = jsonData.nextcountry2;

	// Restore characters for the new players
	function restoreCharForPlayer(player, name) {
		var game = charGetGame();
		var localPlayer = _localPlayersByName.get((name || '').trim());
		var saved = (game && localPlayer && localPlayer.characters) ? localPlayer.characters[game] : null;
		if (saved && saved.file) {
			jsonData['p' + player + 'Character']     = saved.character || '';
			jsonData['p' + player + 'CharacterPack'] = saved.pack || '';
			jsonData['p' + player + 'Palette']       = saved.palette || 0;
			jsonData['p' + player + 'CharacterFile'] = saved.file || '';
			var thumb   = document.getElementById('p' + player + 'CharThumb');
			var label   = document.getElementById('p' + player + 'CharLabel');
			var portrait = document.getElementById('p' + player + 'CharPortrait');
			var packSel = document.getElementById('p' + player + 'CharPack');
			if (thumb)   { thumb.src = '/' + saved.file; thumb.style.display = 'inline'; }
			if (label)   label.textContent = saved.character + ' (' + saved.palette + ')';
			if (portrait){ portrait.src = '/' + saved.file; portrait.style.display = 'block'; }
			if (packSel) packSel.value = saved.pack;
		} else {
			clearCharacterSelect(player);
		}
	}
	restoreCharForPlayer(1, jsonData.p1Name);
	restoreCharForPlayer(2, jsonData.p2Name);
	updateCurrentPlayerDisplay();
    refreshSocialFields();
	sendJsonToEndpoint("updatealldata");
}

function updateResults() {
	document.getElementById("form_results_score_1p").style.opacity  = 1;
	document.getElementById("form_results_score_2p").style.opacity  = 1;
	document.getElementById("form_results_name_1p").style.opacity  = 1;
	document.getElementById("form_results_name_2p").style.opacity  = 1;
	jsonData.resultscore1 = document.getElementById("form_results_score_1p").value;
	jsonData.resultscore2 = document.getElementById("form_results_score_2p").value;
	jsonData.resultplayer1 = document.getElementById("form_results_name_1p").value;
	jsonData.resultplayer2 = document.getElementById("form_results_name_2p").value;
	sendJSON();
}

var _sendJsonTimer = null;
function sendJSON() {
	jsonData.timestamp = Date.now();
	if (_sendJsonTimer) clearTimeout(_sendJsonTimer);
	_sendJsonTimer = setTimeout(function() {
		fetch('/updatedatanoscores', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(jsonData)
		}).catch(function(err) { console.log('error: ' + err); });
	}, 300);
}

function sendJsonToEndpoint(endpoint) {
    sendJsonToEndpointWithCallback(function() {}, endpoint);
}

function sendJsonDataToEndpoint(data, endpoint, message) {
    fetch('/' + endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(function(response) {
        if (response.ok && message != null && message.trim() !== '') {
            alert(message);
        } else if (!response.ok) {
            console.log('Something went wrong. Status:', response.status);
        }
    }).catch(function(err) { console.log('error: ' + err); });
}

function sendJsonToEndpointWithCallback(callback, endpoint) {
	jsonData.timestamp = Date.now();
	fetch('/' + endpoint, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(jsonData)
	}).then(function(response) {
		if (response.ok) callback();
	}).catch(function(err) { console.log('error: ' + err); });
}

// For pop up dialogue
document.getElementById('openPopupTop8Btn').addEventListener('click', function() {
    document.getElementById('popupTop8').style.display = 'block';
});

document.getElementById('closePopupTop8Btn').addEventListener('click', function() {
    document.getElementById('popupTop8').style.display = 'none';
});

document.getElementById('openAddPlayerStatBtn').addEventListener('click', function() {
    document.getElementById('addPlayerStat').style.display = 'block';
});

document.getElementById('closeAddPlayerStatBtn').addEventListener('click', function() {
    document.getElementById('addPlayerStat').style.display = 'none';
});

document.getElementById('openStartggBtn').addEventListener('click', function() {
    document.getElementById('startggPopup').style.display = 'block';
});

document.getElementById('closeStartggBtn').addEventListener('click', function() {
    document.getElementById('startggPopup').style.display = 'none';
});

document.getElementById('tournamentName').addEventListener('change', function() {
    saveStartggInfo();
});

document.getElementById('currentEventName').addEventListener('change', function() {
    saveStartggInfo();
});

document.getElementById('streamName').addEventListener('change', function() {
    saveStartggInfo();
});

window.addEventListener('click', function(event) {
    if (event.target == document.getElementById('startggPopup')) {
        document.getElementById('startggPopup').style.display = 'none';
    }
});

document.getElementById('openStatsBtn').addEventListener('click', function() {
    document.getElementById('statsPopup').style.display = 'block';
});

document.getElementById('closeStatsBtn').addEventListener('click', function() {
    document.getElementById('statsPopup').style.display = 'none';
});

window.addEventListener('click', function(event) {
    if (event.target == document.getElementById('statsPopup')) {
        document.getElementById('statsPopup').style.display = 'none';
    }
});

function loadLeagueStats() {
    const value = document.getElementById('league_suggestions').value;
    fetch("/loadLeagueData", {
        method: "POST",
        body: new URLSearchParams({
            path: value
        })
    });
}

function clearLeagueStats() {
    sendJsonDataToEndpoint({}, "clearLeagueData", "League data deleted!");
}

function getLeagueDirs() {
    fetch('/getLeagueDirs')
        .then(function(response) {
            return response.json();
        })
        .then(function (data) {
            leagues = document.getElementById('league_suggestions');
            leaguesList = data.leagues;
            if (leaguesList.length === 0) {
                // Clear all options from the datalist
                leagues.innerHTML = '';
                return;
            }

            // Clear all options from the leagues
            leagues.innerHTML = '';
            // Filter and add leagues
            const option = document.createElement('option');
            option.textContent = "Select League For Stats";
            option.selected = true;
            option.disabled = true;
            leagues.appendChild(option);
            currentLeague = data.current_league;
            leaguesList
              .slice() // optional: avoids mutating the original array
              .sort((a, b) => a.localeCompare(b))
              .forEach(league => {
                const option = document.createElement('option');
                option.value = league;
                option.textContent = league;
                option.style.color = "black";
                if (league === currentLeague) {
                    option.selected = true;
                }
                leagues.appendChild(option);
            });
          })
        .catch(function (err) {
          console.log('error: ' + err);
        });
}

function loadStatsInfo() {
    getLeagueDirs();
    createEventsWithStatsDropdown();
}

function saveStartggInfo() {
    var tournamentName = document.getElementById('tournamentName').value
    var eventName = document.getElementById('currentEventName').value
    var streamName = document.getElementById('streamName').value
    startggInfo.tournament = tournamentName;
    startggInfo.event = eventName;
    startggInfo.stream = streamName;
    sendJsonDataToEndpoint(startggInfo, "setTournamentInfo");
}

function fetchStartggTop8Info() {
    var tournamentName = document.getElementById('tournamentNameTop8').value
    var eventName = document.getElementById('eventNameTop8').value
    const jsonData = { tournament: tournamentName, event: eventName };
    document.getElementById('popupTop8').style.display = 'none';
    sendJsonDataToEndpoint(jsonData, "fetchStartggTop8Info");
}

function addStartggTop8Info() {
    var tournamentName = document.getElementById('tournamentNameTop8').value
    var eventName = document.getElementById('eventNameTop8').value
    const jsonData = { tournament: tournamentName, event: eventName };
    sendJsonDataToEndpoint(jsonData, "addStartggTop8Info", "Player stats for event added!");
}

function addPlayStats() {
    var playerName = document.getElementById('playerName').value
    var eventName = document.getElementById('eventName').value
    var placementValue = document.getElementById('placement').value
    var winsValue = document.getElementById('wins').value
    var lossesValue = document.getElementById('losses').value
    const jsonData = { gamerTag: playerName, event: eventName, placement: placementValue, wins: winsValue, losses: lossesValue };
    sendJsonDataToEndpoint(jsonData, "addPlayerStat", playerName + " stat for " + eventName + " added!");
}

function deletePlayerStats() {
    sendJsonDataToEndpoint({}, "deletePlayerStats", "Player stats deleted!");
}

function getAllPlayersForTournament(event) {
    event.preventDefault();
    event.stopPropagation();
    loadPlayerData(false, true);
}

function loadPlayerData(fromCache) {
   loadPlayerData(fromCache, false);
}

function loadPlayerData(fromCache, notify) {
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
            nextPlaySuggestions = document.getElementById('next_player_suggestions');
            playersMap.clear();
            if (playersData.length === 0 || playersData[startggInfo.event].length === 0) {
                if (notify) alert("Got no data for tournament: " + startggInfo.tournament + " event: " + startggInfo.event);
                // Clear all options from the datalist
                nextPlaySuggestions.innerHTML = '';
                return;
            }

            // Clear all options from the nextPlaySuggestions
            nextPlaySuggestions.innerHTML = '';
            // Filter and add suggestions to next player list
            playersData[startggInfo.event]
              .slice()
              .sort((a, b) => a.name.localeCompare(b.name))
              .forEach(player => {
                playersMap.set(player.name, player);
            });
            // Only add to datalist if preference includes startgg
            nextPlaySuggestions.innerHTML = '';
            if (_playerSource === 'startgg' || _playerSource === 'both') {
                playersMap.forEach(function(_, name) {
                    const option = document.createElement('option');
                    option.value = name;
                    nextPlaySuggestions.appendChild(option);
                });
            }
            // If preference includes local, merge those in too
            if (_playerSource === 'local' || _playerSource === 'both') {
                loadLocalPlayers();
            }
            if (notify) alert("Tournament data loaded for tournament: " + startggInfo.tournament + " event: " + startggInfo.event);
        })
        .catch(function (err) {
              console.log('error: ' + err);
            });
}

function getNextPlayersFromStartgg(event) {
    event.preventDefault();
    event.stopPropagation();
    fetch('/getNextPlayers')
        .then(function (response) {
        nextPlayerData = response.json();
      return nextPlayerData;
    })
    .then(function (nextPlayerData) {
        nextPlaySuggestions = document.getElementById('next_player_suggestions');
        if (nextPlayerData.length === 0) {
            nextPlayersMap.clear();
            // Clear all options from the datalist
            nextPlaySuggestions.innerHTML = '';
            return;
        }
        jsonData.nextplayer1 = nextPlayerData[0].player1.name;
        jsonData.nextplayer2 = nextPlayerData[0].player2.name;
        jsonData.nextteam1 = nextPlayerData[0].player1.team;
        jsonData.nextteam2 = nextPlayerData[0].player2.team;
        jsonData.nextcountry1 = nextPlayerData[0].player1.country;
        jsonData.nextcountry2 = nextPlayerData[0].player2.country;
        // Clear all options from the nextPlaySuggestions
        nextPlaySuggestions.innerHTML = '';
        // Filter and add suggestions to next player list
        nextPlayerData.forEach(set => {
            const option1 = document.createElement('option');
            option1.value = set.player1.name;
            const option2 = document.createElement('option');
            option2.value = set.player2.name;
            nextPlaySuggestions.appendChild(option1);
            nextPlaySuggestions.appendChild(option2);
            nextPlayersMap.set(set.player1.name, set);
            nextPlayersMap.set(set.player2.name, set);
        });
        updateElementEmptyOkay("form_next_round_team_1p", jsonData.nextteam1);
        updateElementEmptyOkay("form_next_round_name_1p", jsonData.nextplayer1);
        updateElementEmptyOkay("dropdown_country_next1", jsonData.nextcountry1);
        updateElementEmptyOkay("form_next_round_team_2p", jsonData.nextteam2);
        updateElementEmptyOkay("form_next_round_name_2p", jsonData.nextplayer2);
        updateElementEmptyOkay("dropdown_country_next2", jsonData.nextcountry2);
        sendJSON();
      })
    .catch(function (err) {
      console.log('error: ' + err);
    });
}

function rebuildPlayerSuggestion() {
    if (nextPlayersMap.size === 0) {
        return;
    }
    nextPlaySuggestions = document.getElementById('next_player_suggestions');
    nextPlaySuggestions.innerHTML = '';

    // Filter and add suggestions to next player list
    const names = new Set();
    nextPlayersMap.forEach((set, name) => {
        if (names.has(name)) {
            return;
        }
        const option1 = document.createElement('option');
        option1.value = set.player1.name;
        const option2 = document.createElement('option');
        option2.value = set.player2.name;
        names.add(option1.value);
        names.add(option2.value);
        nextPlaySuggestions.appendChild(option1);
        nextPlaySuggestions.appendChild(option2);
    });
}

var startggInfo;
var nextPlayersMap = new Map();
var playersMap = new Map();
var currentSet = null;

function getStartggInfo() {
    fetch('/getTournamentInfo')
        .then(function (response) {
        startggData = response.json();
      return startggData;
    })
    .then(function (data) {
        if (Object.keys(data).length != 0) {
            startggInfo = data;
        }
        document.getElementById('tournamentName').value = startggInfo.tournament;
        document.getElementById('streamName').value = startggInfo.stream;
        document.getElementById('currentEventName').value = startggInfo.event;
        loadPlayerData(true);
      })
    .catch(function (err) {
      console.log('error: ' + err);
    });
}

function addEventListenersForNextRound(id) {
    const nextRoundName = document.getElementById(id);
    let previousValue = '';

    nextRoundName.addEventListener('focus', (event) => {
        if (nextPlayersMap.size > 0) {
            previousValue = event.target.value;
            event.target.value = '';
        }
    });

    nextRoundName.addEventListener('blur', (event) => {
        if (nextPlayersMap.size > 0) {
            if (!event.target.value) {
                event.target.value = previousValue;
            }
        }
    });
}

function setEventForStats() {
	var eventStats = document.getElementById("eventStatsSelect");
	selected = eventStats.options[eventStats.selectedIndex].text;
	eventStats.value = selected;
	eventData = { event: selected };
	sendJsonDataToEndpoint(eventData, "setEventForStats")
}

function createEventsWithStatsDropdown() {
    fetch('/getEventsWithStats')
        .then(function(response) {
            return response.json();
        })
        .then(function (eventData) {
        // Create the <select> element
        const select = document.getElementById("eventStatsSelect");
        select.innerHTML = '';
        const option1 = document.createElement('option');
        option1.textContent = "Select Event For Stats";
        option1.selected = true;
        option1.disabled = true;
        select.appendChild(option1);
        var currentEvent = eventData.current_event;
        // Loop through the list of strings and create <option> elements
        eventData.events.forEach(event => {
            // Create an <option> element for each string
            const option = document.createElement("option");
            option.value = event;  // Set the value of the option
            option.textContent = event;          // Set the text inside the option
            option.style.color = "black";
            if (event === currentEvent) {
                option.selected = true;
            }
            select.appendChild(option);          // Append the option to the select element
        });
        // Add event listener to handle selection change
        select.addEventListener("change", function() {
            const selectedOption = select.options[select.selectedIndex];
            selectedOption.textContent = select.value
        });
      })
    .catch(function (err) {
      console.log('error: ' + err);
    });

}

function removeNextPlayers(event) {
    event.preventDefault();
    event.stopPropagation();
    var p1_name = document.getElementById("form_next_round_name_1p").value;
    var p2_name = document.getElementById("form_next_round_name_2p").value;
    if (p1_name.trim() != "") {
        removeNextPlayer(p1_name);
    }
    if (p2_name.trim() != "") {
        removeNextPlayer(p2_name);
    }
}

function removeNextPlayer(name) {
    var select = document.getElementById('next_player_suggestions');
    var options = select.options;
    for (var i = 0; i < options.length; i++) {
      if (options[i].value == name) {
        select.remove(i);  // Removes the option with name
        nextPlayersMap.delete(name);
        break;
      }
    }
}

function clearNextPlayers(event) {
    event.preventDefault();
    event.stopPropagation();
    nextPlaySuggestions = document.getElementById('next_player_suggestions');
    // Clear all options from the nextPlaySuggestions
    nextPlaySuggestions.innerHTML = '';
    nextPlayersMap.clear();
    playersMap.clear();
    sendJsonToEndpoint("clearPlayersList");
}

function updateCurrentGame() {
    jsonData["current_game"] = document.getElementById('gameSelect').value;
    charRefreshPacks();
    sendJSON();
}

function getAllGames() {
    fetch('/getAllGameImageDir')
        .then(function (response) {
            gamesData = response.json();
            return gamesData;
        }).then(function (gamesData) {
                  var games = document.getElementById('gameSelect');
                  if (gamesData.game_list.length === 0) {
                      // Clear all options from the datalist
                      games.innerHTML = '';
                      return;
                  }

                  // Clear all options from the nextPlaySuggestions
                  games.innerHTML = '';
                  const option1 = document.createElement('option');
                  option1.textContent = "Select Game";
                  option1.selected = true;
                  option1.disabled = true;
                  games.appendChild(option1);
                  // Filter and add suggestions to next player list
                  var currentGame = gamesData.current_game;
                  gamesData.game_list
                    .slice() // optional: avoids mutating the original array
                    .sort((a, b) => a.localeCompare(b))
                    .forEach(game => {
                      const option = document.createElement('option');
                      option.value = game;
                      if (game === currentGame) {
                        option.selected = true;
                      }
                      option.textContent = game;
                      option.style.color = "black";
                      games.appendChild(option);
                  });
                  // Load character packs for the currently selected game
                  if (currentGame) { charRefreshPacks(); }
              })
              .catch(function (err) {
                    console.log('error: ' + err);
                  });
}

populateCountrySelectDropDown();
getDataFromServer();
getStartggInfo();
createEventsWithStatsDropdown();
addEventListenersForNextRound('form_next_round_name_1p');
addEventListenersForNextRound('form_next_round_name_2p');
getAllGames();

// ── CHARACTER SELECT ──────────────────────────────────────────────
var _charMaps = {};  // cache: "game/pack" -> charMap

function charGetGame() {
    // Use the current game from the main game dropdown
    return (jsonData && jsonData.current_game) ? jsonData.current_game : '';
}

function charRefreshPacks() {
    // Called when current_game changes -- reload packs for both players
    [1, 2].forEach(function(p) { charLoadPacksForPlayer(p); });
}

function charLoadPacksForPlayer(player) {
    var game = charGetGame();
    var packSel = document.getElementById('p' + player + 'CharPack');
    if (!packSel) return;
    packSel.innerHTML = '<option value="">-- Pack --</option>';
    charClosePopover(player);
    if (!game) { console.log('charLoadPacksForPlayer: no game set'); return; }
    console.log('charLoadPacksForPlayer: fetching packs for', game, 'player', player);
    fetch('/getCharacterPacks?game=' + encodeURIComponent(game))
        .then(function(r) { return r.json(); })
        .then(function(packs) {
            console.log('charLoadPacksForPlayer: got packs', packs);
            packs.forEach(function(p) {
                var opt = document.createElement('option');
                opt.value = p; opt.textContent = p;
                packSel.appendChild(opt);
            });
        })
        .catch(function(e) { console.log('charLoadPacksForPlayer error:', e); });
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

function charTogglePicker(player) {
    var popover = document.getElementById('p' + player + 'CharPopover');
    var btn     = document.getElementById('p' + player + 'CharPickerBtn');
    if (popover.style.display !== 'none') {
        charClosePopover(player);
        return;
    }
    var game = charGetGame();
    var pack = document.getElementById('p' + player + 'CharPack').value;
    if (!game) { alert('Set a current game first using the Game dropdown.'); return; }
    if (!pack) { alert('Select a pack first.'); return; }
    var key  = game + '/' + pack;

    function renderPopover(charMap) {
        _charMaps[key] = charMap;
        popover.innerHTML = '';
        var chars = Object.keys(charMap).sort();
        chars.forEach(function(char) {
            var palettes = charMap[char];
            var defaultImg = '/' + palettes[0].file;

            // Row
            var row = document.createElement('div');
            row.className = 'char-row';
            row.innerHTML =
                '<img class="char-row-thumb" src="' + defaultImg + '">' +
                '<span class="char-row-name">' + char + '</span>' +
                '<span class="char-row-arrow">›</span>';
            row.querySelector('.char-row-thumb').onerror = function() { this.style.display = 'none'; };

            // Palette strip (hidden until row clicked)
            var strip = document.createElement('div');
            strip.className = 'char-palette-strip';
            strip.style.display = 'none';
            palettes.forEach(function(p) {
                var img = document.createElement('img');
                img.className = 'char-palette-thumb';
                img.src = '/' + p.file;
                img.title = 'Palette ' + p.palette;
                img.dataset.char = char;
                img.dataset.palette = p.palette;
                img.onerror = function() { this.style.display = 'none'; };
                img.onclick = function(e) {
                    e.stopPropagation();
                    charSelectPalette(player, game, pack, char, p.palette, p.file, img, popover);
                };
                strip.appendChild(img);
            });

            row.onclick = function() {
                var isOpen = row.classList.contains('expanded');
                // Close all other expanded rows
                popover.querySelectorAll('.char-row.expanded').forEach(function(r) {
                    r.classList.remove('expanded');
                    r.nextElementSibling.style.display = 'none';
                });
                if (!isOpen) {
                    row.classList.add('expanded');
                    strip.style.display = 'flex';
                    strip.scrollIntoView({ block: 'nearest' });
                }
            };

            popover.appendChild(row);
            popover.appendChild(strip);
        });

        popover.style.display = 'block';
        btn.classList.add('open');
    }

    if (_charMaps[key]) {
        renderPopover(_charMaps[key]);
    } else {
        fetch('/getCharacterList?game=' + encodeURIComponent(game) + '&pack=' + encodeURIComponent(pack))
            .then(function(r) { return r.json(); })
            .then(renderPopover);
    }
}

function charClosePopover(player) {
    var popover = document.getElementById('p' + player + 'CharPopover');
    var btn     = document.getElementById('p' + player + 'CharPickerBtn');
    if (popover) popover.style.display = 'none';
    if (btn) btn.classList.remove('open');
}

function charSelectPalette(player, game, pack, char, palette, file, imgEl, popover) {
    // Highlight selection
    popover.querySelectorAll('.char-palette-thumb.selected').forEach(function(el) {
        el.classList.remove('selected');
    });
    imgEl.classList.add('selected');

    // Update the picker button
    var thumb = document.getElementById('p' + player + 'CharThumb');
    var label = document.getElementById('p' + player + 'CharLabel');
    if (thumb) { thumb.src = '/' + file; thumb.style.display = 'inline'; }
    if (label) label.textContent = char + ' (' + palette + ')';
    // Update portrait
    var portrait = document.getElementById('p' + player + 'CharPortrait');
    if (portrait) { portrait.src = '/' + file; portrait.style.display = 'block'; }

    // Write to jsonData and save
    jsonData['p' + player + 'Character']     = char;
    jsonData['p' + player + 'CharacterPack'] = pack;
    jsonData['p' + player + 'Palette']       = palette;
    jsonData['p' + player + 'CharacterFile'] = file;
    sendJSON();

    // Save character to player profile and update in-memory map
    var playerName = jsonData['p' + player + 'Name'];
    var game = charGetGame();
    if (playerName && game) {
        var localPlayer = _localPlayersByName.get(playerName.trim());
        if (localPlayer && localPlayer.id) {
            // Update in-memory record immediately
            if (!localPlayer.characters) localPlayer.characters = {};
            localPlayer.characters[game] = { pack: pack, character: char, palette: palette, file: file };
            var charUpdate = {};
            charUpdate[game] = { pack: pack, character: char, palette: palette, file: file };
            fetch('/saveLocalPlayer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: localPlayer.id, name: localPlayer.name, characters: charUpdate })
            }).catch(function(e) { console.log('saveCharacter error:', e); });
        }
    }

    // Close popover after short delay
    setTimeout(function() { charClosePopover(player); }, 300);
}

// Close popovers on outside click
document.addEventListener('click', function(e) {
    [1, 2].forEach(function(p) {
        var btn     = document.getElementById('p' + p + 'CharPickerBtn');
        var popover = document.getElementById('p' + p + 'CharPopover');
        if (!btn || !popover) return;
        if (!btn.contains(e.target) && !popover.contains(e.target)) {
            charClosePopover(p);
        }
    });
});

// Packs load when current_game is set via the game dropdown

// ── CHARACTER PALETTE PREVIEW ──────────────────────────────────
(function() {
  var preview = null, previewImg = null, previewLabel = null;

  function getPreview() {
    if (!preview) {
      preview      = document.getElementById('char-preview');
      previewImg   = document.getElementById('char-preview-img');
      previewLabel = document.getElementById('char-preview-label');
    }
    return preview;
  }

  function showPreview(e, src, label) {
    var p = getPreview();
    if (!p) return;
    previewImg.src = src;
    previewLabel.textContent = label;
    p.style.display = 'block';
    movePreview(e);
  }

  function movePreview(e) {
    var p = getPreview();
    if (!p || p.style.display === 'none') return;
    var x = e.clientX + 16;
    var y = e.clientY + 16;
    // Keep within viewport
    if (x + 140 > window.innerWidth)  x = e.clientX - 148;
    if (y + 155 > window.innerHeight) y = e.clientY - 158;
    p.style.left = x + 'px';
    p.style.top  = y + 'px';
  }

  function hidePreview() {
    var p = getPreview();
    if (p) p.style.display = 'none';
  }

  // Attach to dynamically created palette thumbs via event delegation
  document.addEventListener('mouseover', function(e) {
    var thumb = e.target.closest('.char-palette-thumb');
    if (!thumb) { hidePreview(); return; }
    var char    = thumb.dataset.char    || '';
    var palette = thumb.dataset.palette !== undefined ? thumb.dataset.palette : '';
    showPreview(e, thumb.src, char + (palette !== '' ? ' · ' + palette : ''));
  });

  document.addEventListener('mousemove', function(e) {
    movePreview(e);
  });

  document.addEventListener('mouseout', function(e) {
    var thumb = e.target.closest('.char-palette-thumb');
    if (thumb && !e.relatedTarget?.closest('.char-palette-thumb')) {
      hidePreview();
    }
  });
})();
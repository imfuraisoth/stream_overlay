// Creating a XHR object
var xhr = new XMLHttpRequest();

function getDataFromServer() {
    fetch('/getdata')
        .then(function (response) {
        jsonData = response.json();
      return jsonData;
    })
    .then(function (data) {
        populateData(data);
      })
    .catch(function (err) {
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
	updateCurrentPlayerDisplay();
}

const countriesDropDownList = ['US', 'CA', 'JP', 'KR', 'MX', 'GB', 'ES', 'FR', 'FI', 'SE', 'PR'];
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
	updateCurrentPlayerDisplay();
	sendJSON();
}

function updatePlayer2() {
	jsonData.p2Name = document.getElementById("form_name_2p").value;
	updateCurrentPlayerDisplay();
	sendJSON();
}

function updateTeam1() {
	jsonData.p1Team = document.getElementById("form_team_1p").value;
	sendJSON();
}

function updateTeam2() {
	jsonData.p2Team = document.getElementById("form_team_2p").value;
	sendJSON();
}

function updateNextPlayer1() {
	jsonData.nextplayer1 = document.getElementById("form_next_round_name_1p").value;
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
	sendJSON();
}

function updateNextCountry2() {
	jsonData.nextcountry2 = document.getElementById("dropdown_country_next2").value;
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
	updateCurrentPlayerDisplay();
	sendJSON();
}

function reverseScores() {
    fetch('/getdata')
        .then(function (response) {
        jsonData = response.json();
      return jsonData;
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
	updateCurrentPlayerDisplay();
	sendJsonToEndpoint("updatealldata");
}

function countryDropdown1() {
	var c1 = document.getElementById("dropdown_country_1p");
	jsonData.p1Country = c1.options[c1.selectedIndex].text;
	sendJSON();
}

function countryDropdown2() {
	var c2 = document.getElementById("dropdown_country_2p");
	jsonData.p2Country = c2.options[c2.selectedIndex].text;
	sendJSON();
}

function nextRound() {
    fetch('/getdata')
        .then(function (response) {
        jsonData = response.json();
      return jsonData;
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

	updateCurrentPlayerDisplay();
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

function sendJSON() {
	// open a connection
	xhr.open("POST", '/updatedatanoscores', true);

	// Set the request header i.e. which type of content you are sending
	xhr.setRequestHeader("Content-Type", "application/json");

	// Create a state change callback
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4 && xhr.status === 200) {
			// console.log("Server Okay");
		}
	};

	// Set timestamp
	jsonData.timestamp = Date.now();

	// Converting JSON data to string
	var data = JSON.stringify(jsonData);
	// Sending data with the request
	xhr.send(data);
}

function sendJsonToEndpoint(endpoint) {
    sendJsonToEndpointWithCallback(function (){}, endpoint);
}

function sendJsonDataToEndpoint(data, endpoint) {
    sendJsonToEndpoint(data, endpoint, "");
}

function sendJsonDataToEndpoint(data, endpoint, message) {
// open a connection
	xhr.open("POST", "../" + endpoint, true);

	// Set the request header i.e. which type of content you are sending
	xhr.setRequestHeader("Content-Type", "application/json");

    // Handle the response
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {  // 4 means request is done
            if (xhr.status === 200 && message != null && message.trim() != "") {  // 200 means OK
                alert(message);
            } else if (xhr.status === 400) {
                console.log("Bad request. Please check your data.");
            } else if (xhr.status === 500) {
                console.log("Server error. Please try again later.");
            } else {
                console.log("Something went wrong. Status:", xhr.status);
            }
        }
    };

    // Handle network errors
    xhr.onerror = function() {
        console.log("Request failed due to network error.");
    };

	// Converting JSON data to string
	var dataToSend = JSON.stringify(data);
	// Sending data with the request
	xhr.send(dataToSend);
}

function sendJsonToEndpointWithCallback(callback, endpoint) {
    // open a connection
	xhr.open("POST", "../" + endpoint, true);

	// Set the request header i.e. which type of content you are sending
	xhr.setRequestHeader("Content-Type", "application/json");

	// Create a state change callback
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4 && xhr.status === 200) {
		    callback();
        }
	};

	// Set timestamp
	jsonData.timestamp = Date.now();

	// Converting JSON data to string
	var data = JSON.stringify(jsonData);
	// Sending data with the request
	xhr.send(data);
}

function registerClientForRefresh() {
    // Open a connection to the server
    xhr.open("GET", "/registerClientRefresh", true);
	// Set the request header i.e. which type of content you are sending
	xhr.setRequestHeader("Content-Type", "application/json");

    // Handle the response from the server
    xhr.onreadystatechange = function() {
		if (xhr.readyState === 4 && xhr.status === 200) {
            // Update the UI with the new notification
            getDataFromServer();
            // Send another request to the server
            registerClientForRefresh();
        }
    };

    // Send the request
    xhr.send();
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

function saveStartggInfo() {
    var tournamentName = document.getElementById('tournamentName').value
    var eventName = document.getElementById('currentEventName').value
    var streamName = document.getElementById('streamName').value
    startggInfo.tournament = tournamentName;
    startggInfo.event = eventName;
    startggInfo.stream = streamName;
    document.getElementById('startggPopup').style.display = 'none';
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
    loadPlayerData(false);
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
            nextPlaySuggestions = document.getElementById('next_player_suggestions');
            playersMap.clear();
            if (playersData.length === 0) {
                // Clear all options from the datalist
                nextPlaySuggestions.innerHTML = '';
                return;
            }

            // Clear all options from the nextPlaySuggestions
            nextPlaySuggestions.innerHTML = '';
            // Filter and add suggestions to next player list
            playersData
              .slice() // optional: avoids mutating the original array
              .sort((a, b) => a.name.localeCompare(b.name))
              .forEach(player => {
                playersMap.set(player.name, player);
                const option = document.createElement('option');
                option.value = player.name;
                nextPlaySuggestions.appendChild(option);
            });
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
        .then(function (response) {
        jsonData = response.json();
      return jsonData;
    })
    .then(function (events) {
        // Get the container where the dropdown will be inserted
        const container = document.getElementById("eventStatsContainer");

        // Create the <select> element
        const select = document.getElementById("eventStatsSelect");
        select.classList.add("events-with-stats-dropdown");

        // Loop through the list of strings and create <option> elements
        events.forEach(event => {
            // Create an <option> element for each string
            const option = document.createElement("option");
            option.value = event;  // Set the value of the option
            option.textContent = event;          // Set the text inside the option
            option.style.color = "black";
            select.appendChild(option);          // Append the option to the select element
        });
        // Append the <select> element to the container
        container.appendChild(select);
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

populateCountrySelectDropDown();
getDataFromServer();
getStartggInfo();
createEventsWithStatsDropdown();
addEventListenersForNextRound('form_next_round_name_1p');
addEventListenersForNextRound('form_next_round_name_2p');
registerClientForRefresh();
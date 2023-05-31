// Creating a XHR object
var xhr = new XMLHttpRequest();
var url = "http://192.168.0.168:8080/";

var jsonData;

function getDataFromServer() {
    fetch(url + 'getdata')
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
}

function updateElement(id, value) {
	if (value != null && value.length > 0) {
		document.getElementById(id).value = value;
	}
}

function updatePlayer1() {
	jsonData.p1Name = document.getElementById("form_name_1p").value;
	sendJSON();
}

function updatePlayer2() {
	jsonData.p2Name = document.getElementById("form_name_2p").value;
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
	sendJSON();
}

function updateNextPlayer2() {
	jsonData.nextplayer2 = document.getElementById("form_next_round_name_2p").value;
	sendJSON();
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
	sendJSON();
}

function updateScore2() {
	jsonData.p2Score = document.getElementById("form_score_2p").value;
	sendJSON();
}

function updateRound() {
	jsonData.round = document.getElementById("dropdown_round").value;
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
	jsonData.p1Country = "";
	jsonData.p2Country = "";
	jsonData.p1Score = "0";
	jsonData.p2Score = "0";
	sendJSON();
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
	sendJSON();
}

function reverseScores() {
	var p1 = document.getElementById("form_score_1p").value;
	var p2 = document.getElementById("form_score_2p").value;
	document.getElementById("form_score_1p").value = p2;
	document.getElementById("form_score_2p").value = p1;
	jsonData.p1Score = p2;
	jsonData.p2Score = p1;
	sendJSON();
}

function addScoreP1() {
	var score = parseInt(document.getElementById("form_score_1p").value);
	score++;
	jsonData.p1Score = score.toString();
	document.getElementById("form_score_1p").value = jsonData.p1Score;
	sendJSON();
}

function subtractScoreP1() {
	var score = parseInt(document.getElementById("form_score_1p").value);
	if (score <= 0) {
		return;
	}
	score--;
	jsonData.p1Score = score.toString();
	document.getElementById("form_score_1p").value = jsonData.p1Score;
	sendJSON();
}

function addScoreP2() {
	var score = parseInt(document.getElementById("form_score_2p").value);
	score++;
	jsonData.p2Score = score.toString();
	document.getElementById("form_score_2p").value = jsonData.p2Score;
	sendJSON();
}

function subtractScoreP2() {
	var score = parseInt(document.getElementById("form_score_2p").value);
	if (score <= 0) {
		return;
	}
	score--;
	jsonData.p2Score = score.toString();
	document.getElementById("form_score_2p").value = jsonData.p2Score;
	sendJSON();
}

function resetScores() {
	document.getElementById("form_score_1p").value = "0";
	document.getElementById("form_score_2p").value = "0";
	jsonData.p1Score = "0";
	jsonData.p2Score = "0";
	sendJSON();
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
	sendJSON();
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
    fetch(url + 'getdata')
        .then(function (response) {
        jsonData = response.json();
      return jsonData;
    })
    .then(function (data) {
        nextRoundUpdate(data);
      })
    .catch(function (err) {
      console.log('error: ' + err);
    });
}

function nextRoundUpdate(data) {
	jsonData.resultscore1 = data.p1Score;
	jsonData.resultscore2 = data.p2Score;
	jsonData.resultplayer1 = data.p1Name;
	jsonData.resultplayer2 = data.p2Name;
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
    document.getElementById("dropdown_country_next1").value = "US";
    document.getElementById("dropdown_country_next2").value = "US";
	jsonData.p1Score = "0";
	jsonData.p2Score = "0";
	document.getElementById("form_next_round_team_1p").value = "";
	document.getElementById("form_next_round_name_1p").value = "";
	document.getElementById("form_next_round_team_2p").value = "";
	document.getElementById("form_next_round_name_2p").value = "";
	jsonData.nextteam1 = "";
	jsonData.nextplayer1 = "";
	jsonData.nextteam2 = "";
	jsonData.nextplayer2 = "";
    jsonData.nextcountry1 = "US";
    jsonData.nextcountry2 = "US";
	sendJSON();
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

function triggerReplay() {
	// open a connection
	xhr.open("POST", url + 'replaystart', true);

	// Set the request header i.e. which type of content you are sending
	xhr.setRequestHeader("Content-Type", "application/json");

	// Create a state change callback
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4 && xhr.status === 200) {
			// console.log("Server Okay");
		}
	};

	// Sending data with the request
	xhr.send();
}

function stopReplay() {
	// open a connection
	xhr.open("POST", url + 'replaystop', true);

	// Set the request header i.e. which type of content you are sending
	xhr.setRequestHeader("Content-Type", "application/json");

	// Create a state change callback
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4 && xhr.status === 200) {
			// console.log("Server Okay");
		}
	};

	// Sending data with the request
	xhr.send();
}

function sendJSON() {
	// open a connection
	xhr.open("POST", url + 'updatealldata', true);

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

function registerClientForRefresh() {
    // Open a connection to the server
    xhr.open("GET", url + "/registerClientRefresh", true);
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

getDataFromServer();
registerClientForRefresh();
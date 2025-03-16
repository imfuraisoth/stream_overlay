// Creating a XHR object
var xhr = new XMLHttpRequest();

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

fetch('/getTop8PlayerData')
	.then(function (response) {
	top8Data = response.json();
  return top8Data;
})
.then(function (data) {
	populateTop8PlayerData(data);
  })
.catch(function (err) {
  console.log('error: ' + err);
});

function populateTop8PlayerData(data) {
    console.log(data);
    populateTop8Player("w1", data, "r1", "p1", true)
    populateTop8Player("w2", data, "r1", "p2", true)
    populateTop8Player("w3", data, "r2", "p1", true)
    populateTop8Player("w4", data, "r2", "p2", true)
    populateTop8Player("l1", data, "r3", "p1", true)
    populateTop8Player("l2", data, "r3", "p2", true)
    populateTop8Player("l3", data, "r4", "p1", true)
    populateTop8Player("l4", data, "r4", "p2", true)
    populateTop8Player("w1_wf", data, "r5", "p1")
    populateTop8Player("w2_wf", data, "r5", "p2")
    populateTop8Player("w1_gf", data, "r10", "p1")
    populateTop8Player("w2_gf", data, "r10", "p2")
    populateTop8Player("l1_lq", data, "r6", "p1")
    populateTop8Player("l2_lq", data, "r6", "p2")
    populateTop8Player("l3_lq", data, "r7", "p1")
    populateTop8Player("l4_lq", data, "r7", "p2")
    populateTop8Player("l1_ls", data, "r8", "p1")
    populateTop8Player("l2_ls", data, "r8", "p2")
    populateTop8Player("l1_lf", data, "r9", "p1")
    populateTop8Player("l2_lf", data, "r9", "p2")
}

function populateTop8Player(suffix, data, round, player) {
    populateTop8Player(suffix, data, round, player, false)
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
    // open a connection
    xhr.open("POST", '../setNextRound', true);
    // Set the request header i.e. which type of content you are sending
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    // Create a state change callback
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            getJsonDataFromServerWithArgs('getTop8PlayerData', updateNextRoundForms, round, suffix1, suffix2);
        }
    };
    // Sending data with the request
    xhr.send('round=' + round);
}

function updateNextRoundForms(top8PlayerData, round, suffix1, suffix2) {
    document.getElementById("form_next_round_team_1p").value = document.getElementById("form_team_" + suffix1).value;
    document.getElementById("form_next_round_name_1p").value = document.getElementById("form_name_" + suffix1).value;
    document.getElementById("dropdown_country_next1").value = top8PlayerData["r" + round]["p1"]["country"];
    document.getElementById("form_next_round_team_2p").value = document.getElementById("form_team_" + suffix2).value;
    document.getElementById("form_next_round_name_2p").value = document.getElementById("form_name_" + suffix2).value;
    document.getElementById("dropdown_country_next2").value = top8PlayerData["r" + round]["p2"]["country"];
    highlightNextRoundForms(round);
    jsonData.nextteam1 = document.getElementById("form_team_" + suffix1).value;
    jsonData.nextplayer1 = document.getElementById("form_name_" + suffix1).value;
    jsonData.nextteam2 = document.getElementById("form_team_" + suffix2).value;
    jsonData.nextplayer2 = document.getElementById("form_name_" + suffix2).value;
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
		document.getElementById(id).value = value;
	}
}

function updatePlayer1() {
	jsonData.p1Name = document.getElementById("form_name_1p").value;
	sendJsonToEndpoint('updateCurrentPlayers');
}

function updatePlayer2() {
	jsonData.p2Name = document.getElementById("form_name_2p").value;
	sendJsonToEndpoint('updateCurrentPlayers');
}

function updateTeam1() {
	jsonData.p1Team = document.getElementById("form_team_1p").value;
	sendJsonToEndpoint('updateCurrentPlayers');
}

function updateTeam2() {
	jsonData.p2Team = document.getElementById("form_team_2p").value;
	sendJsonToEndpoint('updateCurrentPlayers');
}

function updateNextPlayer1() {
	jsonData.nextplayer1 = document.getElementById("form_next_round_name_1p").value;
	sendJsonToEndpoint('updateNextPlayers');
}

function updateNextPlayer2() {
	jsonData.nextplayer2 = document.getElementById("form_next_round_name_2p").value;
	sendJsonToEndpoint('updateNextPlayers');
}

function updateNextTeam1() {
	jsonData.nextteam1 = document.getElementById("dropdown_country_next1").value;
	sendJsonToEndpoint('updateNextPlayers');
}

function updateNextTeam2() {
	jsonData.nextteam2 = document.getElementById("dropdown_country_next2").value;
	sendJsonToEndpoint('updateNextPlayers');
}

function updateScore1() {
	jsonData.p1Score = document.getElementById("form_score_1p").value;
	sendJsonToEndpoint('updateP1score');
}

function updateScore2() {
	jsonData.p2Score = document.getElementById("form_score_2p").value;
	sendJsonToEndpoint('updateP2score');
}

function updateRound() {
	jsonData.round = document.getElementById("dropdown_round").value;
	sendJsonToEndpoint('updateCurrentPlayers');
}

function resetNamesAndScore() {
	document.getElementById("form_name_1p").value = "";
	document.getElementById("form_name_2p").value = "";
	document.getElementById("form_team_1p").value = "";
	document.getElementById("form_team_2p").value = "";
	document.getElementById("form_score_1p").value = "0";
	document.getElementById("form_score_2p").value = "0";
	document.getElementById("dropdown_country_current_1").value = "US";
    document.getElementById("dropdown_country_current_2").value = "US";
	jsonData.p1Name = "";
	jsonData.p2Name = "";
	jsonData.p1Team = "";
	jsonData.p2Team = "";
	jsonData.p1Country = "US";
	jsonData.p2Country = "US";
	jsonData.p1Score = "0";
	jsonData.p2Score = "0";
	sendJsonToEndpoint("updatealldata");
}

function reversePlayerNames() {
	var p1 = document.getElementById("form_name_1p").value;
	var p2 = document.getElementById("form_name_2p").value;
	var t1 = document.getElementById("form_team_1p").value;
	var t2 = document.getElementById("form_team_2p").value;
	var c1 = document.getElementById("dropdown_country_current_1").value;
	var c2 = document.getElementById("dropdown_country_current_2").value;
	document.getElementById("form_name_1p").value = p2;
	document.getElementById("form_name_2p").value = p1;
	document.getElementById("form_team_1p").value = t2;
	document.getElementById("form_team_2p").value = t1;
	document.getElementById("dropdown_country_current_1").value = c2;
	document.getElementById("dropdown_country_current_2").value = c1;
	jsonData.p1Name = p2;
	jsonData.p2Name = p1;
	jsonData.p1Team = t2;
	jsonData.p2Team = t1;
	jsonData.p1Country = c2;
	jsonData.p2Country = c1;
	sendJsonToEndpointWithCallback(reverseNames, 'updateCurrentPlayers');
}

function reverseNames() {
    callServer("reverseNames");
}

function reverseScores() {
	var p1 = document.getElementById("form_score_1p").value;
	var p2 = document.getElementById("form_score_2p").value;
	document.getElementById("form_score_1p").value = p2;
	document.getElementById("form_score_2p").value = p1;
	jsonData.p1Score = p2;
	jsonData.p2Score = p1;
	sendJsonToEndpoint('updateCurrentScore');
}

function addScoreP1() {
	var score = parseInt(document.getElementById("form_score_1p").value);
	score++;
	jsonData.p1Score = score.toString();
	document.getElementById("form_score_1p").value = jsonData.p1Score;
	sendJsonToEndpoint('updateP1score');
}

function subtractScoreP1() {
	var score = parseInt(document.getElementById("form_score_1p").value);
	if (score <= 0) {
		return;
	}
	score--;
	jsonData.p1Score = score.toString();
	document.getElementById("form_score_1p").value = jsonData.p1Score;
	sendJsonToEndpoint('updateP1score');
}

function addScoreP2() {
	var score = parseInt(document.getElementById("form_score_2p").value);
	score++;
	jsonData.p2Score = score.toString();
	document.getElementById("form_score_2p").value = jsonData.p2Score;
	sendJsonToEndpoint('updateP2score');
}

function subtractScoreP2() {
	var score = parseInt(document.getElementById("form_score_2p").value);
	if (score <= 0) {
		return;
	}
	score--;
	jsonData.p2Score = score.toString();
	document.getElementById("form_score_2p").value = jsonData.p2Score;
	sendJsonToEndpoint('updateP2score');
}

function resetScores() {
	document.getElementById("form_score_1p").value = "0";
	document.getElementById("form_score_2p").value = "0";
	jsonData.p1Score = "0";
	jsonData.p2Score = "0";
	sendJsonToEndpoint('updateCurrentScore');
}

function resetAll() {
	document.getElementById("form_name_1p").value = "";
	document.getElementById("form_name_2p").value = "";
	document.getElementById("form_team_1p").value = "";
	document.getElementById("form_team_2p").value = "";
	document.getElementById("form_score_1p").value = "0";
	document.getElementById("form_score_2p").value = "0";
	document.getElementById("dropdown_country_current_1").value = "US";
	document.getElementById("dropdown_country_current_2").value = "US";
	document.getElementById("form_next_round_team_1p").value = "";
	document.getElementById("form_next_round_name_1p").value = "";
	document.getElementById("form_next_round_team_2p").value = "";
	document.getElementById("form_next_round_name_2p").value = "";
	document.getElementById("form_results_name_1p").value = "";
	document.getElementById("form_results_score_1p").value = "";
	document.getElementById("form_results_name_2p").value = "";
	document.getElementById("form_results_score_2p").value = "";
    document.getElementById("dropdown_country_w1").value = "US";
    document.getElementById("dropdown_country_w2").value = "US";
    document.getElementById("dropdown_country_w3").value = "US";
    document.getElementById("dropdown_country_w4").value = "US";
    document.getElementById("dropdown_country_l1").value = "US";
    document.getElementById("dropdown_country_l2").value = "US";
    document.getElementById("dropdown_country_l3").value = "US";
    document.getElementById("dropdown_country_l4").value = "US";
    document.getElementById("dropdown_country_next1").value = "US";
    document.getElementById("dropdown_country_next2").value = "US";
	document.getElementById("form_name_w1").value = "";
    document.getElementById("form_name_w2").value = "";
    document.getElementById("form_name_w3").value = "";
    document.getElementById("form_name_w4").value = "";
    document.getElementById("form_name_l1").value = "";
    document.getElementById("form_name_l2").value = "";
    document.getElementById("form_name_l3").value = "";
    document.getElementById("form_name_l4").value = "";
    document.getElementById("form_team_w1").value = "";
    document.getElementById("form_team_w2").value = "";
    document.getElementById("form_team_w3").value = "";
    document.getElementById("form_team_w4").value = "";
    document.getElementById("form_team_l1").value = "";
    document.getElementById("form_team_l2").value = "";
    document.getElementById("form_team_l3").value = "";
    document.getElementById("form_team_l4").value = "";
    document.getElementById("form_score_w1").value = "";
    document.getElementById("form_score_w2").value = "";
    document.getElementById("form_score_w3").value = "";
    document.getElementById("form_score_w4").value = "";
    document.getElementById("form_score_l1").value = "";
    document.getElementById("form_score_l2").value = "";
    document.getElementById("form_score_l3").value = "";
    document.getElementById("form_score_l4").value = "";
    document.getElementById("form_name_w1_wf").value = "";
    document.getElementById("form_team_w1_wf").value = "";
    document.getElementById("form_score_w1_wf").value = "";
    document.getElementById("form_score_w1_gf2").value = "";
    document.getElementById("form_name_w2_wf").value = "";
    document.getElementById("form_team_w2_wf").value = "";
    document.getElementById("form_score_w2_wf").value = "";
    document.getElementById("form_score_w2_gf2").value = "";
    document.getElementById("form_name_w1_gf").value = "";
    document.getElementById("form_team_w1_gf").value = "";
    document.getElementById("form_score_w1_gf").value = "";
    document.getElementById("form_name_w2_gf").value = "";
    document.getElementById("form_team_w2_gf").value = "";
    document.getElementById("form_score_w2_gf").value = "";
    document.getElementById("form_name_l1_lq").value = "";
    document.getElementById("form_team_l1_lq").value = "";
    document.getElementById("form_score_l1_lq").value = "";
    document.getElementById("form_name_l2_lq").value = "";
    document.getElementById("form_team_l2_lq").value = "";
    document.getElementById("form_score_l2_lq").value = "";
    document.getElementById("form_name_l3_lq").value = "";
    document.getElementById("form_team_l3_lq").value = "";
    document.getElementById("form_score_l3_lq").value = "";
    document.getElementById("form_name_l4_lq").value = "";
    document.getElementById("form_team_l4_lq").value = "";
    document.getElementById("form_score_l4_lq").value = "";
    document.getElementById("form_name_l1_ls").value = "";
    document.getElementById("form_team_l1_ls").value = "";
    document.getElementById("form_score_l1_ls").value = "";
    document.getElementById("form_name_l2_ls").value = "";
    document.getElementById("form_team_l2_ls").value = "";
    document.getElementById("form_score_l2_ls").value = "";
    document.getElementById("form_name_l1_lf").value = "";
    document.getElementById("form_team_l1_lf").value = "";
    document.getElementById("form_score_l1_lf").value = "";
    document.getElementById("form_name_l2_lf").value = "";
    document.getElementById("form_team_l2_lf").value = "";
    document.getElementById("form_score_l2_lf").value = "";
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
	updateAllData(resetTop8);
}

function countryDropdown(id) {
	var c = document.getElementById(id);
	jsonData.p1Country = c.options[c.selectedIndex].text;
	sendJsonToEndpoint('updateCurrentPlayers');
}

function countryDropdown(id, round, player) {
    var value = document.getElementById(id);
    updateTop8PlayerInfo(round, player, "country", value.options[value.selectedIndex].text)
}

function updateTop8PlayerInfo(round, player, field, value) {
    // open a connection
    xhr.open("POST", '../updateTop8playerInfo', true);
    // Set the request header i.e. which type of content you are sending
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    // Create a state change callback
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            // console.log("Server Okay");
        }
    };
    // Sending data with the request
    xhr.send("round=" + round + "&player=" + player + "&field=" + field + "&value=" + value);
}

function nextRound(jsonData) {
    fetch('/getdata')
        .then(function (response) {
        jsonData = response.json();
      return jsonData;
    })
    .then(function (jsonData) {
        document.getElementById("form_results_score_1p").value = jsonData.p1Score;
        document.getElementById("form_results_score_2p").value = jsonData.p2Score;
        document.getElementById("form_results_name_1p").value = jsonData.p1Name;
        document.getElementById("form_results_name_2p").value = jsonData.p2Name;

        document.getElementById("form_results_score_1p").style.opacity  = 0.5;
        document.getElementById("form_results_score_2p").style.opacity  = 0.5;
        document.getElementById("form_results_name_1p").style.opacity  = 0.5;
        document.getElementById("form_results_name_2p").style.opacity  = 0.5;
        getJsonDataFromServer("getNextRoundData", updateCurrentAndNextInfoUpdatePlayerData)
      })
    .catch(function (err) {
      console.log('error: ' + err);
    });
}

function startTop8() {
    getJsonDataFromServer("getNextRoundData", updateCurrentAndNextInfo)
}

function updateCurrentAndNextInfo(currentNextData) {
    document.getElementById("form_next_round_team_1p").value = currentNextData.nextPlayer1.team;
    document.getElementById("form_next_round_name_1p").value = currentNextData.nextPlayer1.name;
    document.getElementById("form_next_round_team_2p").value = currentNextData.nextPlayer2.team;
    document.getElementById("form_next_round_name_2p").value = currentNextData.nextPlayer2.name;
    document.getElementById("dropdown_country_next1").value = currentNextData.nextPlayer1.country;
    document.getElementById("dropdown_country_next2").value = currentNextData.nextPlayer2.country;
    document.getElementById("form_team_1p").value = currentNextData.player1.team;
    document.getElementById("form_name_1p").value = currentNextData.player1.name;
    document.getElementById("form_team_2p").value = currentNextData.player2.team;
    document.getElementById("form_name_2p").value = currentNextData.player2.name;
    document.getElementById("dropdown_country_current_1").value = currentNextData.player1.country;
    document.getElementById("dropdown_country_current_2").value = currentNextData.player2.country;
    document.getElementById("form_score_1p").value = "0";
    document.getElementById("form_score_2p").value = "0";
    document.getElementById("dropdown_round").value = currentNextData.currentRoundName;
    var top8Started = currentNextData.started;
    if (top8Started) {
        document.getElementById("rectangle_button_18").style.background = "#14BF01";
    } else {
        document.getElementById("rectangle_button_18").style.background = "#675267";
    }
    highlightNextRoundForms(currentNextData.nextRound)
    highlightCurrentRoundForms(currentNextData.currentRound)

    jsonData.round = currentNextData.currentRoundName;
    jsonData.p1Team = currentNextData.player1.team;
    jsonData.p2Team = currentNextData.player2.team;
    jsonData.p1Name = currentNextData.player1.name;
    jsonData.p2Name = currentNextData.player2.name;
    jsonData.p1Country = currentNextData.player1.country;
    jsonData.p2Country = currentNextData.player2.country;
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
        document.getElementById("form_team_" + suffix).style.border="";
        document.getElementById("form_name_" + suffix).style.border="";
        document.getElementById("form_score_" + suffix).style.border="";
    }
    for (const suffix of roundSuffixMap[round]) {
        document.getElementById("form_team_" + suffix).style.border="2px solid red";
        document.getElementById("form_name_" + suffix).style.border="2px solid red";
        document.getElementById("form_score_" + suffix).style.border="2px solid red";
    }
    if (round == 11) {
        document.getElementById("form_score_w1_gf2").style.border="2px solid red";
        document.getElementById("form_score_w2_gf2").style.border="2px solid red";
    }
    lastRoundSuffix = roundSuffixMap[round];
}

function highlightNextRoundForms(round) {
    for (const suffix of lastNextRoundSuffix) {
        document.getElementById("form_team_" + suffix).style.border="";
        document.getElementById("form_name_" + suffix).style.border="";
        document.getElementById("form_score_" + suffix).style.border="";
    }
    for (const suffix of roundSuffixMap[round]) {
        document.getElementById("form_team_" + suffix).style.border="2px solid yellow";
        document.getElementById("form_name_" + suffix).style.border="2px solid yellow";
        document.getElementById("form_score_" + suffix).style.border="2px solid yellow";
    }
    lastNextRoundSuffix = roundSuffixMap[round];
}

function updateCurrentAndNextInfoUpdatePlayerData(currentNextData) {
    updateCurrentAndNextInfo(currentNextData)
    getJsonDataFromServer("getTop8PlayerData", populateTop8PlayerData)
}

function getJsonDataFromServerWithArgs(endpoint, callback, arg1, arg2, arg3) {
	// open a connection
	xhr.open("GET", '/' + endpoint, true);

	// Set the request header i.e. which type of content you are sending
	xhr.setRequestHeader("Content-Type", "application/json");

	// Create a state change callback
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4 && xhr.status === 200) {
			// console.log("Server Okay");
			callback(JSON.parse(xhr.response), arg1, arg2, arg3)
		}
	};
	// Sending data with the request
	xhr.send();
}

function getJsonDataFromServer(endpoint, callback) {
	// open a connection
	xhr.open("GET", '/' + endpoint, true);

	// Set the request header i.e. which type of content you are sending
	xhr.setRequestHeader("Content-Type", "application/json");

	// Create a state change callback
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4 && xhr.status === 200) {
			// console.log("Server Okay");
			callback(JSON.parse(xhr.response))
		}
	};
	// Sending data with the request
	xhr.send();
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
	sendJsonToEndpoint('updateResults');
}

function callServer(endpoint) {
	// open a connection
	xhr.open("POST", '../' + endpoint, true);

	// Set the request header i.e. which type of content you are sending
	xhr.setRequestHeader("Content-Type", "application/json");

	// Create a state change callback
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4 && xhr.status === 200) {
		}
	};

	// Sending data with the request
	xhr.send();
}

function resetTop8() {
	// open a connection
	xhr.open("POST", '../resetTop8', true);

	// Set the request header i.e. which type of content you are sending
	xhr.setRequestHeader("Content-Type", "application/json");

	// Create a state change callback
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4 && xhr.status === 200) {
	        document.getElementById("rectangle_button_18").style.background = "#675267";
            for (const suffix of lastRoundSuffix) {
                document.getElementById("form_team_" + suffix).style.border="";
                document.getElementById("form_name_" + suffix).style.border="";
                document.getElementById("form_score_" + suffix).style.border="";
            }
            for (const suffix of lastNextRoundSuffix) {
                document.getElementById("form_team_" + suffix).style.border="";
                document.getElementById("form_name_" + suffix).style.border="";
                document.getElementById("form_score_" + suffix).style.border="";
            }
            document.getElementById("form_score_w1_gf2").style.border="";
            document.getElementById("form_score_w2_gf2").style.border="";
		}
	};

	// Sending data with the request
	xhr.send();
}

function updateAllData(callback) {
    // open a connection
	xhr.open("POST", '../updatealldata', true);

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

function sendJsonToEndpoint(endpoint) {
    sendJsonToEndpointWithCallback(function (){}, endpoint);
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

getDataFromServer();
registerClientForRefresh();
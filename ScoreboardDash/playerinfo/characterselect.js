// Creating a XHR object
var xhr = new XMLHttpRequest();

let currentGame = "";
const relativePath = "../";

function handleGameSelect() {
    const select = document.getElementById("gameSelect");
    currentGame = select.value;
    renderCharacters(currentGame);
}

function renderCharacters(game) {
    var url = `/getCharacterImages?game=${game}`;
    fetch(url)
      .then(function(response) {
         if (!response.ok) throw new Error("Network response was not ok");
           return response.json();
         })
        .then(function (characters) {
            const container = document.getElementById("characterList");
            container.innerHTML = "";

            Object.keys(characters).forEach(character => {

                const row = document.createElement("div");
                row.style.display = "flex";
                row.style.alignItems = "center";
                row.style.marginBottom = "10px";
                row.classList.add("character-row");

                const checkbox = document.createElement("input");
                checkbox.type = "checkbox";

                // ----------- Add event listener to toggle highlight -----------
                checkbox.addEventListener("change", () => {
                    if (checkbox.checked) {
                        row.classList.add("selected");
                    } else {
                        row.classList.remove("selected");
                    }
                });

                const label = document.createElement("label");
                label.textContent = character;
                label.style.width = "120px";

                const dropdown = document.createElement("select");
                dropdown.classList.add("variation-dropdown");
                characters[character].forEach((img, index) => {

                    const option = document.createElement("option");
                    option.value = img;
                    option.textContent = "Style " + index;

                    dropdown.appendChild(option);

                });

                const preview = document.createElement("img");
                preview.src = relativePath + characters[character][0];
                preview.style.width = "60px";
                preview.style.marginLeft = "10px";

                dropdown.addEventListener("change", () => {
                    preview.src = relativePath + dropdown.value;
                });

                row.appendChild(checkbox);
                row.appendChild(label);
                row.appendChild(dropdown);
                row.appendChild(preview);

                container.appendChild(row);

            });
        }).catch(function (err) {
                console.log('error: ' + err);
              });
}

var playersMap = new Map();

function getAllEvents() {
    fetch('/getAllEvents')
        .then(function (response) {
        events = response.json();
      return events;
    })
    .then(function (data) {
            var events = document.getElementById('eventSelect');
            if (data.length === 0) {
                // Clear all options from the datalist
                events.innerHTML = '';
                return;
            }

            // Clear all options from the nextPlaySuggestions
            events.innerHTML = '';
            const option1 = document.createElement('option');
            option1.textContent = "Select Event";
            option1.selected = true;
            option1.disabled = true;
            events.appendChild(option1);

            // Filter and add suggestions to next player list
            data
              .slice() // optional: avoids mutating the original array
              .sort((a, b) => a.localeCompare(b))
              .forEach(event => {
                const option = document.createElement('option');
                option.value = event;
                option.textContent = event;
                option.style.color = "black";
                events.appendChild(option);
            });
      })
    .catch(function (err) {
      console.log('error: ' + err);
    });
}

function loadPlayersDropdown() {
    const select = document.getElementById("eventSelect");
    const selectedValue = select.value;
    var url = `/getAllPlayersForEvent?event=${selectedValue}`;
    fetch(url)
      .then(function(response) {
         if (!response.ok) throw new Error("Network response was not ok");
           return response.json();
         })
        .then(function (playersData) {
            players = document.getElementById('playerSelect');
            playersMap.clear();
            if (playersData.length === 0) {
                // Clear all options from the datalist
                players.innerHTML = '';
                return;
            }

            // Clear all options from the nextPlaySuggestions
            players.innerHTML = '';
            const option1 = document.createElement('option');
            option1.textContent = "Select Player";
            option1.selected = true;
            option1.disabled = true;
            players.appendChild(option1);
            // Filter and add suggestions to next player list
            playersData
              .slice() // optional: avoids mutating the original array
              .sort((a, b) => a.name.localeCompare(b.name))
              .forEach(player => {
                playersMap.set(player.name, player);
                const option = document.createElement('option');
                option.value = player.name;
                option.textContent = player.name;
                players.appendChild(option);
            });
        })
        .catch(function (err) {
              console.log('error: ' + err);
            });
}

function getAllGames() {
    fetch('/getAllGameImageDir')
        .then(function (response) {
            gameDirs = response.json();
            return gameDirs;
        }).then(function (gameDirs) {
                  var games = document.getElementById('gameSelect');
                  if (gameDirs.length === 0) {
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
                  gameDirs
                    .slice() // optional: avoids mutating the original array
                    .sort((a, b) => a.localeCompare(b))
                    .forEach(game => {
                      const option = document.createElement('option');
                      option.value = game;
                      option.textContent = game;
                      option.style.color = "black";
                      games.appendChild(option);
                  });
              })
              .catch(function (err) {
                    console.log('error: ' + err);
                  });
}

function savePlayerCharacterData() {
    const game = document.getElementById('gameSelect').value;
    const player = document.getElementById('playerSelect').value;
    const characters = getSelectedCharacters();
    data = {
        game: game,
        player: player,
        characters: characters
    }
    sendJsonDataToEndpoint(data, "savePlayerCharacterData", "Player Character Data Saved!");
}

function getSelectedCharacters() {
    const selected = [];

    // get all checked checkboxes
    const checkboxes = document.querySelectorAll(".character-row input[type='checkbox']:checked");

    checkboxes.forEach(cb => {
        const row = cb.closest(".character-row");

        // character name (from label text)
        const name = row.querySelector("label").textContent.trim();

        // selected variation image
        const dropdown = row.querySelector("select");
        const style = dropdown.options[dropdown.selectedIndex].text;
        const imageUrl = sanitizeImageUrl(dropdown.value);

        selected.push({
            character: name,
            variant: style,
            image: imageUrl
        });
    });

    return selected;
}

function sanitizeImageUrl(url) {
    return url.replace(/\\/g, "/");
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

getAllEvents();
getAllGames();
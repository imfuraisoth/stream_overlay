// Creating a XHR object
var xhr = new XMLHttpRequest();

var jsonData;

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
function populateData(data) {
    console.log(data);
	updateElement("form_name_1", data.com1);
	updateElement("form_name_2", data.com2);
	updateElement("form_social_1", data.soc1);
	updateElement("form_social_2", data.soc2);
	jsonData = data;
}

function updateElement(id, value) {
	if (value != null && value.length > 0) {
		document.getElementById(id).value = value;
	}
}

function updateCom1() {
	jsonData.com1 = document.getElementById("form_name_1").value;
	sendJSON();
}

function updateCom2() {
	jsonData.com2 = document.getElementById("form_name_2").value;
	sendJSON();
}

function updateSoc1() {
	jsonData.soc1 = document.getElementById("form_social_1").value;
	sendJSON();
}

function updateSoc2() {
	jsonData.soc2 = document.getElementById("form_social_2").value;
	sendJSON();
}

function reverseCommentatorNames() {
	var c1 = document.getElementById("form_name_1").value;
	var c2 = document.getElementById("form_name_2").value;
	var s1 = document.getElementById("form_social_1").value;
	var s2 = document.getElementById("form_social_2").value;
	document.getElementById("form_name_1").value = c2;
	document.getElementById("form_name_2").value = c1;
	document.getElementById("form_social_1").value = s2;
	document.getElementById("form_social_2").value = s1;
	jsonData.com1 = c2;
	jsonData.com2 = c1;
	jsonData.soc1 = s2;
	jsonData.soc2 = s1;
	sendJSON();
}

function addCommentator() {
    var name_value = document.getElementById("commentator_name").value;
    var social_value = document.getElementById("commentator_social").value;
    const commentator_data = {
      name: name_value,
      soc: social_value
    };
    document.getElementById('popupAdd').style.display = 'none';
    sendJsonDataToEndpoint(commentator_data, "addCommentator", populateCommentatorDropdown);
}

function deleteCommentator() {
    const checkboxes = document.querySelectorAll("#commentatorsList input[type='checkbox']");
    const selectedNames = Array.from(checkboxes)
        .filter(checkbox => checkbox.checked)
        .map(checkbox => {
            const label = document.querySelector(`label[for="${checkbox.id}"]`);
            return label ? label.textContent.trim() : "";  // trim spaces
        })
        .filter(name => name !== ""); // remove empty strings

    document.getElementById('popupDelete').style.display = 'none';
    sendJsonDataToEndpoint(selectedNames, "deleteCommentators", populateCommentatorDropdown);
}

function createCommentatorList() {
    fetch('/getCommentators')
        .then(function (response) {
        jsonData = response.json();
      return jsonData;
    })
    .then(function (data) {
        const commentatorsList = document.getElementById('commentatorsList');
        // Clear all existing items
        commentatorsList.innerHTML = '';
        Object.keys(data).forEach(key => {
            const li = document.createElement('li');

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = key;
            const label = document.createElement('label');
            label.htmlFor = checkbox.id;
            label.textContent = key;

            li.appendChild(checkbox);
            li.appendChild(label);
            commentatorsList.appendChild(li);
        });
        document.getElementById('popupDelete').style.display = 'block';
      })
    .catch(function (err) {
      console.log('error: ' + err);
    });
}

function sendJsonDataToEndpoint(data, endpoint, callback) {
// open a connection
	xhr.open("POST", "../" + endpoint, true);

	// Set the request header i.e. which type of content you are sending
	xhr.setRequestHeader("Content-Type", "application/json");

    // Handle the response
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {  // 4 means request is done
            if (xhr.status === 200 && message != null && message.trim() != "") {  // 200 means OK
                callback();
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

function sendJSON() {
	// open a connection
	xhr.open("POST", '/updatecommdata', true);

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

window.onload = function() {
    populateCommentatorDropdown();
};

function populateCommentatorDropdown() {
    fetch('/getCommentators')
        .then(function (response) {
        jsonData = response.json();
      return jsonData;
    })
    .then(function (data) {
        generateDropdown("soc1_dropdown", "select1", data, updateFromDropdown1);
        generateDropdown("soc2_dropdown", "select2", data, updateFromDropdown2);
      })
    .catch(function (err) {
      console.log('error: ' + err);
    });
}

function generateDropdown(elementId, selectId, data, callback) {
    var dropdownContainer = document.getElementById(elementId);

    // Create a select element
    var select = document.createElement("select");
    select.setAttribute("id", selectId);

    // Create a default placeholder option
    var defaultOption = document.createElement("option");
    defaultOption.textContent = "Select a commentator"; // Placeholder text
    defaultOption.value = ""; // Placeholder value
    defaultOption.disabled = true; // Disable the placeholder option
    defaultOption.selected = true; // Select the placeholder option by default
    select.appendChild(defaultOption);

    var names = Object.keys(data);
    names.forEach(function(name) {
        // Create options
        var option = document.createElement("option");
        option.text = name;
        option.value = JSON.stringify(data[name]);
        select.appendChild(option);
    });
    // Attach onchange event listener
    select.addEventListener("change", function() {
        callback(this.value);
    });
    // Append select to container
    dropdownContainer.appendChild(select);
}

function updateFromDropdown1(value) {
    var person = JSON.parse(value);
    jsonData.com1 = person.name;
    jsonData.soc1 = person.soc;
    document.getElementById("form_name_1").value = jsonData.com1;
    document.getElementById("form_social_1").value = jsonData.soc1;
    jsonData.com2 = document.getElementById("form_name_2").value;
    jsonData.soc2 = document.getElementById("form_social_2").value;
    sendJSON();
}

function updateFromDropdown2(value) {
    var person = JSON.parse(value);
    jsonData.com2 = person.name;
    jsonData.soc2 = person.soc;
    document.getElementById("form_name_2").value = jsonData.com2;
    document.getElementById("form_social_2").value = jsonData.soc2;
    jsonData.com1 = document.getElementById("form_name_1").value;
    jsonData.soc1 = document.getElementById("form_social_1").value;
    sendJSON();
}

// For pop up dialogue
document.getElementById('rectangle_button_add_commentator').addEventListener('click', function() {
    document.getElementById('popupAdd').style.display = 'block';
});
document.getElementById('rectangle_button_delete_commentator').addEventListener('click', function() {
    createCommentatorList();
});

document.getElementById('closeAddBtn').addEventListener('click', function() {
    document.getElementById('popupAdd').style.display = 'none';
});

document.getElementById('closeDelBtn').addEventListener('click', function() {
    document.getElementById('popupDelete').style.display = 'none';
});

window.addEventListener('click', function(event) {
    if (event.target == document.getElementById('popup')) {
        document.getElementById('popup').style.display = 'none';
    }
});
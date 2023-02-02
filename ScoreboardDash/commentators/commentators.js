// Creating a XHR object
var xhr = new XMLHttpRequest();
var url = "http://127.0.0.1:8080/";

var jsonData;

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

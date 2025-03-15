var countries = {
	"US": {
		"alpha2": "US",
		"alpha3": "USA",
		"name": "United States",
		"flag": "US"
	},
	
	"CA": {
		"alpha2": "CA",
		"alpha3": "CAN",
		"name": "Canada",
		"flag": "CA"
	},
	
	"GB": {
		"alpha2": "GB",
		"alpha3": "GBR",
		"name": "United Kingdom",
		"flag": "GB"
	},
	
	"MX": {
		"alpha2": "MX",
		"alpha3": "MEX",
		"name": "Mexico",
		"flag": "MX"
	},
	
	"JP": {
		"alpha2": "JP",
		"alpha3": "JPN",
		"name": "Japan",
		"flag": "JP"
	},
	
	"KR": {
		"alpha2": "KR",
		"alpha3": "KOR",
		"name": "Korea",
		"flag": "KR"
	},

    "ES": {
        "alpha2": "ES",
        "alpha3": "ESP",
        "name": "Spain",
        "flag": "ES"
    },

    "FR": {
        "alpha2": "FR",
        "alpha3": "FRA",
        "name": "France",
        "flag": "FR"
    },

    "FI": {
        "alpha2": "FI",
        "alpha3": "FIN",
        "name": "Finland",
        "flag": "FI"
    },

    "SE": {
        "alpha2": "SE",
        "alpha3": "SWE",
        "name": "Sweden",
        "flag": "SE"
    },

    "PR": {
        "alpha2": "PR",
        "alpha3": "PRI",
        "name": "Puerto Rico",
        "flag": "PR"
    }
};

var countryFlag = function(country){
	for (var prop in countries){
		if (countries.hasOwnProperty(prop)){
			if(countries[prop].alpha2 == country.toUpperCase() || countries[prop].alpha3 == country.toUpperCase()){
				return countries[prop].flag;
			}
		}
	}
	return "unknown"
};

var countryName = function(country){
	for (var prop in countries){
		if (countries.hasOwnProperty(prop)){
			if(countries[prop].alpha2 == country.toUpperCase() || countries[prop].alpha3 == country.toUpperCase()){
				return countries[prop].name;
			}
		}
	}
	return "unknown"
};
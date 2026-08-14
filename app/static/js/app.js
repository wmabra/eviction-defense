/* evictions.help — Eligibility + Payment */
const SUPPORTED_STATES = [
	"AR",
	"CO",
	"CT",
	"GA",
	"IL",
	"KY",
	"LA",
	"MI",
	"MN",
	"MO",
	"NM",
	"OR",
	"RI",
	"SC",
	"TN",
	"TX",
	"VA",
];
const SUPPORTED_COUNTIES = {
	AR: [
		"Benton",
		"Columbia",
		"Craighead",
		"Crawford",
		"Faulkner",
		"Garland",
		"Greene",
		"Hempstead",
		"Independence",
		"Jefferson",
		"Lonoke",
		"Miller",
		"Mississippi",
		"Ouachita",
		"Pulaski",
		"Saline",
		"Sebastian",
		"Union",
		"Washington",
		"White",
	],


	CO: [
		"Adams",
		"Arapahoe",
		"Boulder",
		"Broomfield",
		"Denver",
		"Douglas",
		"Eagle",
		"El Paso",
		"Fremont",
		"Garfield",
		"Jefferson",
		"La Plata",
		"Larimer",
		"Mesa",
		"Montrose",
		"Morgan",
		"Pueblo",
		"Routt",
		"Summit",
		"Weld",
	],
	CT: [
		"Fairfield",
		"Hartford",
		"Litchfield",
		"Middlesex",
		"New Haven",
		"New London",
		"Tolland",
		"Windham",
	],

	GA: [
		"Bibb",
		"Chatham",
		"Cherokee",
		"Clarke",
		"Clayton",
		"Cobb",
		"Columbia",
		"Coweta",
		"DeKalb",
		"Douglas",
		"Fayette",
		"Forsyth",
		"Fulton",
		"Gwinnett",
		"Hall",
		"Henry",
		"Houston",
		"Muscogee",
		"Paulding",
		"Richmond",
	],
	IL: [
		"Champaign",
		"Cook",
		"DuPage",
		"Kane",
		"Kankakee",
		"Kendall",
		"LaSalle",
		"Lake",
		"Macon",
		"Madison",
		"McHenry",
		"McLean",
		"Peoria",
		"Rock Island",
		"Sangamon",
		"St. Clair",
		"Tazewell",
		"Vermilion",
		"Will",
		"Winnebago",
	],
		KY: [
			"Jefferson",
			"Fayette",
			"Kenton",
			"Boone",
			"Warren",
			"Hardin",
			"Daviess",
			"Campbell",
			"Madison",
			"Bullitt",
			"Christian",
			"Oldham",
			"Pulaski",
			"Laurel",
			"Scott",
			"Jessamine",
			"Franklin",
			"McCracken",
			"Hopkins",
			"Shelby",
		],
	LA: [
		"Ascension",
		"Bossier",
		"Caddo",
		"Calcasieu",
		"East Baton Rouge",
		"Iberia",
		"Jefferson",
		"Lafayette",
		"Lafourche",
		"Livingston",
		"Orleans",
		"Ouachita",
		"Rapides",
		"St. Charles",
		"St. John the Baptist",
		"St. Landry",
		"St. Tammany",
		"Tangipahoa",
		"Terrebonne",
		"Vernon",
	],

	MI: [
		"Bay",
		"Berrien",
		"Calhoun",
		"Eaton",
		"Genesee",
		"Ingham",
		"Isabella",
		"Jackson",
		"Kalamazoo",
		"Kent",
		"Livingston",
		"Macomb",
		"Monroe",
		"Muskegon",
		"Oakland",
		"Ottawa",
		"Saginaw",
		"St. Clair",
		"Washtenaw",
		"Wayne",
	],
	MN: [
		"Anoka",
		"Beltrami",
		"Blue Earth",
		"Carver",
		"Clay",
		"Crow Wing",
		"Dakota",
		"Hennepin",
		"Kandiyohi",
		"Olmsted",
		"Otter Tail",
		"Ramsey",
		"Rice",
		"Scott",
		"Sherburne",
		"St. Louis",
		"Stearns",
		"Washington",
		"Winona",
		"Wright",
	],
		MO: [
			"St. Louis County",
			"Jackson",
			"St. Charles",
			"Greene",
			"St. Louis City",
			"Clay",
			"Jefferson",
			"Boone",
			"Jasper",
			"Cass",
			"Platte",
			"Franklin",
			"Christian",
			"Buchanan",
			"Cape Girardeau",
			"Cole",
			"St. Francois",
			"Lincoln",
			"Taney",
			"Howell",
		],
	NM: [
		"Bernalillo",
		"Chaves",
		"Curry",
		"Doña Ana",
		"Eddy",
		"Grant",
		"Lea",
		"Los Alamos",
		"Luna",
		"McKinley",
		"Otero",
		"Rio Arriba",
		"Roosevelt",
		"San Juan",
		"San Miguel",
		"Sandoval",
		"Santa Fe",
		"Taos",
		"Torrance",
		"Valencia",
	],

	OR: [
		"Baker",
		"Benton",
		"Clackamas",
		"Coos",
		"Crook",
		"Deschutes",
		"Douglas",
		"Jackson",
		"Josephine",
		"Klamath",
		"Lane",
		"Linn",
		"Malheur",
		"Marion",
		"Multnomah",
		"Polk",
		"Umatilla",
		"Union",
		"Washington",
		"Yamhill",
	],
	RI: ["Bristol", "Kent", "Newport", "Providence", "Washington"],
	SC: [
		"Aiken",
		"Anderson",
		"Beaufort",
		"Berkeley",
		"Charleston",
		"Dorchester",
		"Florence",
		"Georgetown",
		"Greenville",
		"Greenwood",
		"Horry",
		"Kershaw",
		"Lexington",
		"Oconee",
		"Orangeburg",
		"Pickens",
		"Richland",
		"Spartanburg",
		"Sumter",
		"York",
	],
	TN: [
		"Anderson",
		"Blount",
		"Bradley",
		"Cumberland",
		"Davidson",
		"Hamilton",
		"Knox",
		"Madison",
		"Maury",
		"Montgomery",
		"Putnam",
		"Robertson",
		"Rutherford",
		"Sevier",
		"Shelby",
		"Sullivan",
		"Sumner",
		"Washington",
		"Williamson",
		"Wilson",
	],
	TX: [
		"Bell",
		"Bexar",
		"Brazoria",
		"Cameron",
		"Collin",
		"Dallas",
		"Denton",
		"El Paso",
		"Fort Bend",
		"Galveston",
		"Harris",
		"Hidalgo",
		"Lubbock",
		"McLennan",
		"Montgomery",
		"Nueces",
		"Tarrant",
		"Travis",
		"Webb",
		"Williamson",
	],
	VA: [
		"Albemarle",
		"Alexandria",
		"Arlington",
		"Chesapeake",
		"Chesterfield",
		"Fairfax",
		"Hampton",
		"Henrico",
		"Loudoun",
		"Lynchburg",
		"Montgomery",
		"Newport News",
		"Norfolk",
		"Prince William",
		"Richmond City",
		"Roanoke City",
		"Rockingham",
		"Spotsylvania",
		"Stafford",
		"Virginia Beach",
	],
};

const appState = { state: "" };

// Eligibility check — 8 questions
function populateCounties() {
	const state = document.getElementById("el-state").value;
	const countySelect = document.getElementById("el-county");
	while (countySelect.options.length > 0) {
		countySelect.remove(0);
	}
	const placeholder = document.createElement("option");
	placeholder.value = "";
	placeholder.textContent = "Select your county";
	countySelect.appendChild(placeholder);
	if (state && SUPPORTED_COUNTIES[state]) {
		SUPPORTED_COUNTIES[state].forEach((c) => {
			var opt = document.createElement("option");
			opt.value = c;
			opt.textContent = c;
			countySelect.appendChild(opt);
		});
	}
}

function checkEligibility() {
	const state = document.getElementById("el-state").value;
	const county = document.getElementById("el-county").value;
	const isTenant = document.querySelector('input[name="el-tenant"]:checked');
	const isServed = document.querySelector('input[name="el-served"]:checked');
	const isResidential = document.querySelector(
		'input[name="el-residential"]:checked',
	);
	const isSection8 = document.querySelector(
		'input[name="el-section8"]:checked',
	);
	const isMilitary = document.querySelector(
		'input[name="el-military"]:checked',
	);
	const isBankruptcy = document.querySelector(
		'input[name="el-bankruptcy"]:checked',
	);

	const result = document.getElementById("el-result");

	// Validate all answered
	if (
		!state ||
		!county ||
		!isTenant ||
		!isServed ||
		!isResidential ||
		!isSection8 ||
		!isMilitary ||
		!isBankruptcy
	) {
		showResult("error", "Please answer all 8 questions.");
		return;
	}

	// 1. State check — hard block
	if (!SUPPORTED_STATES.includes(state)) {
		showResult(
			"error",
			"We don't serve " +
				(state || "that state") +
				" yet. We currently cover 20 states: " +
				SUPPORTED_STATES.join(", ") +
				".",
		);
		return;
	}

	// Store county for redirect
	appState.county = county;

	// 3. Tenant check — hard block
	if (isTenant.value === "no") {
		showResult(
			"error",
			"This service is only for tenants named in the eviction. We cannot prepare paperwork for anyone else.",
		);
		return;
	}

	// 4. Served check — SOFT warning (pre-eviction docs available)
	const wasServed = isServed.value === "yes";

	// 5. Residential check — hard block
	if (isResidential.value === "no") {
		showResult(
			"error",
			"This service is for residential evictions only. Commercial evictions have different rules and require an attorney.",
		);
		return;
	}

	// 6. Section 8 check — hard block
	if (isSection8.value === "yes") {
		showResult(
			"error",
			"Section 8 and public housing evictions have special federal rules. You need an attorney or legal aid — self-help paperwork is not appropriate for these cases.",
		);
		return;
	}

	// 7. Military check — hard block
	if (isMilitary.value === "yes") {
		showResult(
			"error",
			"Active military personnel have special protections under the SCRA. Please contact your base legal assistance office — they can help you at no cost.",
		);
		return;
	}

	// 8. Bankruptcy check — hard block
	if (isBankruptcy.value === "yes") {
		showResult(
			"error",
			"Bankruptcy triggers an automatic stay that affects eviction proceedings. Please contact your bankruptcy attorney before filing anything.",
		);
		return;
	}

	// ALL CHECKS PASSED
	appState.state = state;
	document.getElementById("eligibility-form").classList.add("hidden");
	document.getElementById("payment-section").classList.remove("hidden");
	document.getElementById("pay-email").focus();

	// Store whether served (used when redirecting to chat)
	appState.wasServed = wasServed;
}

function showResult(type, msg) {
	const result = document.getElementById("el-result");
	result.className = "alert alert-" + type;
	result.textContent = msg;
	result.classList.remove("hidden");
}

// Payment via Authorize.net — AcceptUI hosted form
// Called by Authorize.net AcceptUI after the user completes the hosted payment form
function authNetResponseHandler(response) {
	const btn = document.getElementById("btn-pay");

	if (response.messages.resultCode === "Error") {
		btn.disabled = false;
		btn.textContent = "Payment Failed — Try Again";
		return;
	}

	// Payment successful — get user info and submit
	const email = document.getElementById("pay-email").value.trim();
	const address = document.getElementById("pay-address").value.trim();
	const city = document.getElementById("pay-city").value.trim();
	const zip = document.getElementById("pay-zip").value.trim();

	if (!email || !address || !city) {
		alert("Please fill in your email, address, and city first.");
		btn.disabled = false;
		btn.textContent = "Pay $399 — Secure Checkout";
		return;
	}

	appState.email = email;
	appState.address = address;
	appState.city = city;
	appState.zip = zip;

	btn.disabled = true;
	btn.textContent = "Processing...";

	submitPayment(response.opaqueData, email);
}

async function submitPayment(opaqueData, email) {
	try {
		const res = await fetch("/api/v1/payment/charge", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({
				opaque_data: opaqueData,
				order_id: "order-" + Date.now(),
				customer_email: email,
				customer_name: "Tenant",
			}),
		});
		if (!res.ok) throw new Error("Payment failed");
		redirectToChat(email);
	} catch (e) {
		document.getElementById("btn-pay").disabled = false;
		document.getElementById("btn-pay").textContent =
			"Payment Failed — Try Again";
	}
}

function redirectToChat(email) {
	var url =
		"/chat?state=" +
		encodeURIComponent(appState.state) +
		"&email=" +
		encodeURIComponent(email) +
		"&address=" +
		encodeURIComponent(appState.address || "") +
		"&city=" +
		encodeURIComponent(appState.city || "") +
		"&county=" +
		encodeURIComponent(appState.county || "") +
		"&zip=" +
		encodeURIComponent(appState.zip || "") +
		"&served=" +
		(appState.wasServed ? "yes" : "no");
	window.location.href = url;
}

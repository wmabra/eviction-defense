/* Eviction Defense — Frontend Application Logic (Landing + Pre-Screen + Payment) */
const API_BASE = "/api/v1/intake";

// County data for all 20 supported states (from rental assistance resource databases)
const COUNTY_DATA = {
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
	AZ: [
		"Apache",
		"Cochise",
		"Coconino",
		"Gila",
		"Glendale Market",
		"Graham",
		"Greenlee",
		"La Paz",
		"Maricopa",
		"Mesa Market",
		"Mohave",
		"Navajo",
		"Phoenix Market",
		"Pima",
		"Pinal",
		"Santa Cruz",
		"Scottsdale Market",
		"Tucson Market",
		"Yavapai",
		"Yuma",
	],
	CA: [
		"Alameda",
		"Contra Costa",
		"Fresno",
		"Kern",
		"Los Angeles",
		"Monterey",
		"Orange",
		"Riverside",
		"Sacramento",
		"San Bernardino",
		"San Diego",
		"San Francisco",
		"San Joaquin",
		"San Mateo",
		"Santa Clara",
		"Solano",
		"Sonoma",
		"Stanislaus",
		"Tulare",
		"Ventura",
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
	FL: [
		"Brevard",
		"Broward",
		"Collier",
		"Duval",
		"Hillsborough",
		"Lake",
		"Lee",
		"Manatee",
		"Martin",
		"Miami-Dade",
		"Orange",
		"Osceola",
		"Palm Beach",
		"Pasco",
		"Pinellas",
		"Polk",
		"Sarasota",
		"Seminole",
		"St. Lucie",
		"Volusia",
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
	MA: [
		"Barnstable",
		"Berkshire",
		"Boston",
		"Bristol",
		"Cambridge",
		"Dukes",
		"Essex",
		"Franklin",
		"Hampden",
		"Hampshire",
		"Lowell",
		"Middlesex",
		"Nantucket",
		"New Bedford",
		"Norfolk",
		"Plymouth",
		"Springfield",
		"Suffolk",
		"Worcester",
		"Worcester City",
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
	NV: [
		"Carson City",
		"Churchill",
		"Clark",
		"Douglas",
		"Elko",
		"Eureka",
		"Henderson Market",
		"Humboldt",
		"Lander",
		"Lincoln",
		"Lyon",
		"Mesquite Market",
		"Mineral",
		"North Las Vegas Market",
		"Nye",
		"Pershing",
		"Sparks Market",
		"Storey",
		"Washoe",
		"White Pine",
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

// State
const appState = {
	state: "FL",
	county: "",
};

// ======================== NAVIGATION ========================

function showScreen(screenId) {
	document
		.querySelectorAll('[id^="screen-"]')
		.forEach((s) => s.classList.add("hidden"));
	document.getElementById(screenId).classList.remove("hidden");
}

// ======================== DYNAMIC COUNTY DROPDOWN ========================

function updateCountyDropdown(stateCode) {
	const select = document.getElementById("ps-county");
	if (!select) return;
	const counties = COUNTY_DATA[stateCode] || [];
	select.innerHTML =
		'<option value="">Select your county</option>' +
		counties.map((c) => `<option value="${c}">${c}</option>`).join("");
	appState.state = stateCode;
}

document.addEventListener("DOMContentLoaded", () => {
	const stateSelect = document.getElementById("ps-state");
	if (stateSelect) {
		stateSelect.addEventListener("change", (e) =>
			updateCountyDropdown(e.target.value),
		);
		updateCountyDropdown("FL");
	}
});

// ======================== PRE-SCREEN ========================

function getRadioValue(name) {
	const el = document.querySelector(`input[name="${name}"]:checked`);
	return el ? el.value : null;
}

function checkEligibility() {
	const btn = document.getElementById("btn-check-eligibility");
	btn.disabled = true;
	btn.innerHTML = '<span class="spinner"></span> Checking...';

	const data = {
		state: document.getElementById("ps-state").value,
		county: document.getElementById("ps-county").value,
		is_tenant: getRadioValue("ps_is_tenant") === "yes",
		is_residential: getRadioValue("ps_residential") === "yes",
		received_court_papers: getRadioValue("ps_court_papers") === "yes",
		has_writ_or_sheriff: getRadioValue("ps_writ") === "yes",
		is_section_8: getRadioValue("ps_section8") === "yes",
		is_active_military: getRadioValue("ps_military") === "yes",
		has_bankruptcy: getRadioValue("ps_bankruptcy") === "yes",
		has_documents_to_upload: getRadioValue("ps_docs") === "yes",
	};

	for (const [_key, val] of Object.entries(data)) {
		if (val === null) {
			showPreScreenResult(
				false,
				"Please answer all questions before checking eligibility.",
			);
			btn.disabled = false;
			btn.textContent = "Check Eligibility";
			return;
		}
	}

	fetch(`${API_BASE}/pre-screen`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(data),
	})
		.then((r) => r.json())
		.then((result) => {
			if (result.eligible) {
				appState.state = data.state;
				appState.county = data.county;
				showPreScreenResult(true, result.message);
				document.getElementById("btn-check-eligibility").textContent =
					"Continue to Purchase →";
				document.getElementById("btn-check-eligibility").onclick = () =>
					showScreen("screen-payment");
			} else {
				showPreScreenResult(false, result.message);
				const reasonEl = document.getElementById("ps-reasons");
				if (result.reason && reasonEl) reasonEl.textContent = result.reason;
				btn.disabled = false;
				btn.textContent = "Check Eligibility";
			}
		})
		.catch((_err) => {
			showPreScreenResult(false, "Network error. Please try again.");
			btn.disabled = false;
			btn.textContent = "Check Eligibility";
		});
}

function showPreScreenResult(success, message) {
	const el = document.getElementById("ps-result");
	el.className = success
		? "alert alert-success mt-4"
		: "alert alert-error mt-4";
	el.textContent = message;
	el.classList.remove("hidden");
	const reasonsEl = document.getElementById("ps-reasons");
	if (!success && reasonsEl && reasonsEl.textContent) {
		reasonsEl.classList.remove("hidden");
	} else if (reasonsEl) {
		reasonsEl.classList.add("hidden");
	}
}

// ======================== PAYMENT (Authorize.net Accept.js) ========================

function proceedToPayment() {
	if (typeof Accept === "undefined") {
		console.warn("Accept.js not loaded — redirecting to chat (dev mode)");
		window.location.href = "/chat";
		return;
	}

	const btn = document.getElementById("btn-pay");
	btn.disabled = true;
	btn.innerHTML = '<span class="spinner"></span> Processing Payment...';

	Accept.dispatchData({
		authData: {
			apiLoginID: "7wM69L5k7q2p",
			clientKey:
				"4r8CTQ7wQKYuGa266vv8WdXLD25pKfd8KgvA7j23NGs22mhLqVFVadczeXf5Gx42",
		},
		paymentData: {
			amount: 395.0,
			description: "Eviction Defense Packet",
		},
		callback: (response) => {
			if (response.messages.resultCode === "Error") {
				btn.disabled = false;
				btn.textContent = "Payment Failed — Try Again";
				console.error("Accept.js error:", response.messages.message);
				return;
			}
			submitPayment(response.opaqueData);
		},
	});
}

async function submitPayment(opaqueData) {
	const btn = document.getElementById("btn-pay");
	try {
		const res = await fetch("/api/v1/payment/charge", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({
				opaque_data: opaqueData,
				order_id: "order-" + Date.now(),
				customer_email: document.getElementById("ps-email")?.value || "",
				customer_name: "Tenant",
			}),
		});

		if (!res.ok) {
			const err = await res.json();
			throw new Error(err.detail || "Payment failed");
		}

		// Payment successful — redirect to AI chat intake
		window.location.href = "/chat";
	} catch (_err) {
		console.error("Payment error:", _err);
		btn.disabled = false;
		btn.textContent = "Payment Failed — Try Again";
	}
}

// ======================== INIT ========================

console.log("Eviction Defense app loaded");

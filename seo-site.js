window.EVICTIONS_HELP_CONFIG = window.EVICTIONS_HELP_CONFIG || {
	apiBase: "",
	useLivePreScreen: false,
	checkoutPath: "/checkout/",
	price: 399,
};
(() => {
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
		IN: [
			"Marion",
			"Lake",
			"Allen",
			"Hamilton",
			"St. Joseph",
			"Elkhart",
			"Tippecanoe",
			"Vanderburgh",
			"Porter",
			"Hendricks",
			"Johnson",
			"Monroe",
			"Madison",
			"Delaware",
			"Clark",
			"Vigo",
			"Howard",
			"LaPorte",
			"Bartholomew",
			"Boone",
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
		OH: [
			"Cuyahoga",
			"Franklin",
			"Hamilton",
			"Summit",
			"Montgomery",
			"Lucas",
			"Stark",
			"Butler",
			"Lorain",
			"Lake",
			"Mahoning",
			"Warren",
			"Clermont",
			"Trumbull",
			"Delaware",
			"Licking",
			"Greene",
			"Portage",
			"Fairfield",
			"Medina",
		],
		OK: [
			"Oklahoma",
			"Tulsa",
			"Cleveland",
			"Canadian",
			"Comanche",
			"Rogers",
			"Payne",
			"Wagoner",
			"Pottawatomie",
			"Creek",
			"Garfield",
			"Muskogee",
			"Grady",
			"Le Flore",
			"Washington",
			"Bryan",
			"Logan",
			"Carter",
			"Okmulgee",
			"Osage",
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

	const q = (s, c = document) => c.querySelector(s),
		qa = (s, c = document) => [...c.querySelectorAll(s)];
	const menu = q(".mobile-menu"),
		nav = q(".nav-links");
	if (menu && nav)
		menu.addEventListener("click", () => nav.classList.toggle("open"));
	qa(".directory-search").forEach((input) =>
		input.addEventListener("input", () => {
			const term = input.value.toLowerCase().trim();
			qa("[data-location-item]", input.closest("section") || document).forEach(
				(el) => (el.hidden = !!term && !el.dataset.locationItem.includes(term)),
			);
		}),
	);
	qa('a[href^="#eligibility"]').forEach((a) =>
		a.addEventListener("click", () =>
			setTimeout(
				() => q("#eligibility select, #eligibility input")?.focus(),
				350,
			),
		),
	);
	qa(".eligibility-form").forEach(initEligibility);
	const checkout = q("[data-checkout]");
	if (checkout) initCheckout(checkout);

	function initEligibility(form) {
		const steps = qa(".screen-step", form),
			bar = q(".progress span", form),
			back = q("[data-back]", form),
			answerData = {};
		const actions = q(".screen-actions", form);
		let next = null;
		if (actions) {
			next = document.createElement("button");
			next.type = "button";
			next.className = "btn btn-primary";
			next.setAttribute("data-next", "");
			next.textContent = "Next";
			actions.appendChild(next);
		}
		let idx = 0,
			advancing = false;
		const preset = {
			state: form.dataset.state || "",
			county: form.dataset.county || "",
			city: form.dataset.city || "",
		};
		const stateSel = q('[name="state"]', form),
			stateLocked = Boolean(preset.state);
		if (stateSel && stateLocked) {
			stateSel.value = preset.state;
			stateSel.setAttribute("aria-readonly", "true");
			answerData.state = preset.state;
		}
		const countyInput = q('[name="county"]', form),
			cityInput = q('[name="city"]', form);
		if (countyInput && preset.county) countyInput.value = preset.county;
		if (cityInput && preset.city) cityInput.value = preset.city;

		function populateCountyDropdown() {
			const sel = q('[name="county"]', form);
			if (!sel || sel.tagName !== "SELECT") return;
			const st = stateSel ? stateSel.value : preset.state;
			while (sel.options.length > 0) sel.remove(0);
			const ph = document.createElement("option");
			ph.value = "";
			ph.textContent = "Select a county";
			sel.appendChild(ph);
			if (st && SUPPORTED_COUNTIES[st]) {
				SUPPORTED_COUNTIES[st].forEach((c) => {
					var o = document.createElement("option");
					o.value = c;
					o.textContent = c;
					sel.appendChild(o);
				});
			}
		}

		function show(i) {
			idx = Math.max(0, Math.min(i, steps.length - 1));
			steps.forEach((s, n) => s.classList.toggle("active", n === idx));
			bar.style.width = (idx >= 8 ? 100 : ((idx + 1) / 8) * 100) + "%";
			if (back)
				back.hidden = idx === 0 || idx >= 8 || (stateLocked && idx === 2);
			if (next)
				next.hidden = idx >= 8;
			const focusable = q(
				'select,input:not([type="radio"]),input[type="radio"]',
				steps[idx],
			);
			if (focusable)
				setTimeout(() => focusable.focus({ preventScroll: true }), 120);
		}

		function shake(step) {
			step.classList.add("shake");
			setTimeout(() => step.classList.remove("shake"), 350);
		}

		function evaluate() {
			const stop = [];
			if (answerData.tenant === "no")
				stop.push(
					"The current program is designed for tenants, not landlords or property owners.",
				);
			if (answerData.residential === "no")
				stop.push(
					"The current program handles residential rental matters only.",
				);
			if (answerData.subsidized === "yes")
				stop.push(
					"Section 8, voucher, and public-housing cases may involve specialized rules that are outside the current automated service.",
				);
			if (answerData.military === "yes")
				stop.push(
					"Active-duty military cases may involve additional federal protections and need specialized review.",
				);
			if (answerData.bankruptcy === "yes")
				stop.push(
					"Bankruptcy can change whether and how an eviction may proceed, so the current automated service does not accept these cases.",
				);
			const result = q("[data-result]", form);
			if (stop.length) {
				result.className = "result-box result-stop";
				result.innerHTML =
					"<strong>This program may not be the right fit.</strong><br>" +
					stop.join(" ");
				q("[data-qualified]", form).hidden = true;
			} else {
				result.className =
					answerData.served === "no"
						? "result-box result-warn"
						: "result-box result-ok";
				result.innerHTML =
					answerData.served === "no"
						? "<strong>You may continue, but timing matters.</strong><br>You indicated that formal court papers have not yet been served. The intake can still collect your information, but court forms generally depend on the papers actually filed."
						: "<strong>You appear eligible to continue.</strong><br>Complete the contact and property details below. No payment is collected on this page.";
				q("[data-qualified]", form).hidden = false;
			}
			show(8);
		}

		function advance(field, stepIndex) {
			if (advancing || stepIndex !== idx || !field.value) return;
			advancing = true;
			answerData[field.name] = field.value;
			window.setTimeout(() => {
				if (stepIndex === 7) evaluate();
				else show(stepIndex + 1);
				advancing = false;
			}, 140);
		}

		if (stateSel) {
			stateSel.addEventListener("change", () => {
				populateCountyDropdown();
				advance(stateSel, 0);
			});
		}
		const countySel = q('[name="county"]', form);
		if (countySel && countySel.tagName === "SELECT") {
			countySel.addEventListener("change", () => advance(countySel, 1));
			populateCountyDropdown();
		}
		qa("input[type=radio]", form).forEach((r) =>
			r.addEventListener("click", () => {
				const step = r.closest(".screen-step");
				advance(r, steps.indexOf(step));
			}),
		);

		if (back)
			back.addEventListener("click", () => {
				if (idx === 1 && !stateLocked) {
					answerData.state = "";
					if (stateSel) stateSel.value = "";
					show(0);
				} else if (idx === 2 && !stateLocked) {
					show(1);
				} else {
					show(idx - 1);
				}
			});

		if (next)
			next.addEventListener("click", () => {
				const step = steps[idx];
				const sel = q("select", step);
				const radio = q('input[type="radio"]:checked', step);
				const field = sel || radio;
				if (field && field.value) {
					advance(field, idx);
				}
			});

		form.addEventListener("submit", async (e) => {
			e.preventDefault();
			const fd = new FormData(form),
				payload = Object.fromEntries(fd.entries());
			payload.eligibility = answerData;
			payload.source_url = location.href;
			sessionStorage.setItem("evictionsHelpIntake", JSON.stringify(payload));
			if (
				window.EVICTIONS_HELP_CONFIG.useLivePreScreen &&
				window.EVICTIONS_HELP_CONFIG.apiBase
			) {
				try {
					const res = await fetch(
						window.EVICTIONS_HELP_CONFIG.apiBase + "/api/v1/intake/pre-screen",
						{
							method: "POST",
							headers: { "Content-Type": "application/json" },
							body: JSON.stringify(payload),
						},
					);
					if (!res.ok) throw new Error("Pre-screen failed");
				} catch (err) {
					console.error(err);
					alert(
						"We could not reach the eligibility service. Please try again.",
					);
					return;
				}
			}
			const p = new URLSearchParams({
				state: payload.state || "",
				county: payload.county || "",
				city: payload.city || "",
				email: payload.email || "",
				address: payload.street || "",
			});
			location.href =
				window.EVICTIONS_HELP_CONFIG.checkoutPath + "?" + p.toString();
		});

		show(stateLocked ? 2 : 0);
	}

	function initCheckout(el) {
		let data = {};
		try {
			data = JSON.parse(sessionStorage.getItem("evictionsHelpIntake") || "{}");
		} catch (e) {}
		const params = new URLSearchParams(location.search);
		["state", "county", "city", "email", "address"].forEach((k) => {
			if (!data[k] && params.get(k)) data[k] = params.get(k);
		});
		qa("[data-bind]", el).forEach(
			(n) => (n.textContent = data[n.dataset.bind] || "Not provided"),
		);
		const btn = q("[data-payment-button]", el);
		if (!btn) return;

		btn.addEventListener("click", () => {
			if (typeof Accept === "undefined") {
				redirectAfterPayment(data);
				return;
			}

			btn.disabled = true;
			btn.textContent = "Processing...";

			Accept.dispatchData({
				authData: {
					apiLoginID: "7wM69L5k7q2p",
					clientKey:
						"4r8CTQ7wQKYuGa266vv8WdXLD25pKfd8KgvA7j23NGs22mhLqVFVadczeXf5Gx42",
				},
				paymentData: { amount: 399.0, description: "Eviction Defense Packet" },
				callback: (response) => {
					if (response.messages.resultCode === "Error") {
						btn.disabled = false;
						btn.textContent = "Payment Failed — Try Again";
						return;
					}
					submitPayment(response.opaqueData, data);
				},
			});
		});
	}

	async function submitPayment(opaqueData, intakeData) {
		const btn = q("[data-payment-button]");
		try {
			const res = await fetch("/api/v1/payment/charge", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					opaque_data: opaqueData,
					order_id: "order-" + Date.now(),
					customer_email: intakeData.email || "",
					customer_name: intakeData.street || "Tenant",
				}),
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				throw new Error(err.detail || "Payment failed");
			}
			redirectAfterPayment(intakeData);
		} catch (e) {
			if (btn) {
				btn.disabled = false;
				btn.textContent = "Payment Failed — Try Again";
			}
			console.error(e);
		}
	}

	function redirectAfterPayment(data) {
		var url =
			"/chat?state=" +
			encodeURIComponent(data.state || "") +
			"&email=" +
			encodeURIComponent(data.email || "") +
			"&address=" +
			encodeURIComponent(data.address || data.street || "") +
			"&city=" +
			encodeURIComponent(data.city || "") +
			"&county=" +
			encodeURIComponent(data.county || "") +
			"&served=" +
			(data.eligibility && data.eligibility.served === "yes" ? "yes" : "no");
		window.location.href = url;
	}
})();

/* evictions.help — Eligibility + Payment */
const SUPPORTED_STATES = [
	"AL",
	"AZ",
	"AR",
	"CA",
	"CO",
	"CT",
	"FL",
	"GA",
	"IL",
	"LA",
	"MA",
	"MI",
	"MN",
	"NV",
	"NM",
	"OR",
	"RI",
	"SC",
	"TN",
	"TX",
	"VA",
];
const appState = { state: "" };

// Eligibility check — 7 questions
function checkEligibility() {
	const state = document.getElementById("el-state").value;
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
		!isTenant ||
		!isServed ||
		!isResidential ||
		!isSection8 ||
		!isMilitary ||
		!isBankruptcy
	) {
		showResult("error", "Please answer all 7 questions.");
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

	// 2. Tenant check — hard block
	if (isTenant.value === "no") {
		showResult(
			"error",
			"This service is only for tenants named in the eviction. We cannot prepare paperwork for anyone else.",
		);
		return;
	}

	// 3. Served check — SOFT warning (pre-eviction docs available)
	const wasServed = isServed.value === "yes";

	// 4. Residential check — hard block
	if (isResidential.value === "no") {
		showResult(
			"error",
			"This service is for residential evictions only. Commercial evictions have different rules and require an attorney.",
		);
		return;
	}

	// 5. Section 8 check — hard block
	if (isSection8.value === "yes") {
		showResult(
			"error",
			"Section 8 and public housing evictions have special federal rules. You need an attorney or legal aid — self-help paperwork is not appropriate for these cases.",
		);
		return;
	}

	// 6. Military check — hard block
	if (isMilitary.value === "yes") {
		showResult(
			"error",
			"Active military personnel have special protections under the SCRA. Please contact your base legal assistance office — they can help you at no cost.",
		);
		return;
	}

	// 7. Bankruptcy check — hard block
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

// Payment via Authorize.net
function startPayment() {
	const email = document.getElementById("pay-email").value.trim();
	const address = document.getElementById("pay-address").value.trim();
	const city = document.getElementById("pay-city").value.trim();
	const county = document.getElementById("pay-county").value.trim();
	const zip = document.getElementById("pay-zip").value.trim();

	if (!email) {
		alert("Please enter your email address.");
		return;
	}
	if (!address || !city || !county) {
		alert("Please fill in your address, city, and county.");
		return;
	}

	appState.email = email;
	appState.address = address;
	appState.city = city;
	appState.county = county;
	appState.zip = zip;
	const btn = document.getElementById("btn-pay");
	btn.disabled = true;
	btn.innerHTML = '<span class="spinner"></span> Processing...';

	if (typeof Accept === "undefined") {
		redirectToChat(email);
		return;
	}

	Accept.dispatchData({
		authData: {
			apiLoginID: "7wM69L5k7q2p",
			clientKey:
				"4r8CTQ7wQKYuGa266vv8WdXLD25pKfd8KgvA7j23NGs22mhLqVFVadczeXf5Gx42",
		},
		paymentData: { amount: 395.0, description: "Eviction Defense Packet" },
		callback: (response) => {
			if (response.messages.resultCode === "Error") {
				btn.disabled = false;
				btn.textContent = "Payment Failed — Try Again";
				return;
			}
			submitPayment(response.opaqueData, email);
		},
	});
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

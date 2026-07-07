/* Eviction Defense — Frontend Application Logic */
const API_BASE = "/api/v1/intake";

// State
const appState = {
	caseId: null,
	county: "",
	uploadedDocs: [],
};

// ======================== NAVIGATION ========================

function showScreen(screenId) {
	document
		.querySelectorAll('[id^="screen-"]')
		.forEach((s) => s.classList.add("hidden"));
	document.getElementById(screenId).classList.remove("hidden");
}

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

	// Validate all questions answered
	for (const [key, val] of Object.entries(data)) {
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
				appState.county = data.county;
				showPreScreenResult(true, result.message);
				document.getElementById("btn-check-eligibility").textContent =
					"Continue to Purchase →";
				document.getElementById("btn-check-eligibility").onclick = () =>
					showScreen("screen-payment");
			} else {
				showPreScreenResult(false, result.message);
				// Show specific reasons too
				if (result.reason) {
					var reasonEl = document.getElementById('ps-reasons');
					if (reasonEl) reasonEl.textContent = result.reason;
				}
				btn.disabled = false;
				btn.textContent = "Check Eligibility";
			}
		})
		.catch((err) => {
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
	
	// Show specific reasons if rejected
	const reasonsEl = document.getElementById("ps-reasons");
	if (!success && reasonsEl && reasonsEl.textContent) {
		reasonsEl.classList.remove("hidden");
	} else if (reasonsEl) {
		reasonsEl.classList.add("hidden");
	}
}

// ======================== PAYMENT ========================

function proceedToPayment() {
	// For now, skip actual Stripe — go straight to intake
	// In production, this would create a Stripe Checkout Session
	startIntake();
}

// ======================== INTAKE FORM ========================

let currentIntakePage = 1;
const INTAKE_PAGES = 6;

function startIntake() {
	showScreen("screen-intake");
	currentIntakePage = 1;
	document.getElementById("i-county").value = appState.county;
	showIntakePage(1);
}

function showIntakePage(num) {
	document
		.querySelectorAll(".intake-page")
		.forEach((p) => p.classList.add("hidden"));
	document.getElementById(`intake-page-${num}`).classList.remove("hidden");
	document.getElementById("intake-step-num").textContent = 3;

	// Update progress bar
	document.querySelectorAll(".progress-step").forEach((s, i) => {
		const stepNum = i + 1;
		s.classList.remove("active", "completed");
		if (stepNum === num) s.classList.add("active");
		else if (stepNum < num) s.classList.add("completed");
	});
	document.querySelectorAll(".progress-line").forEach((l, i) => {
		const lineNum = i + 1;
		l.classList.toggle("completed", lineNum < num);
	});
}

function nextIntakePage(num) {
	currentIntakePage = num;
	showIntakePage(num);
	window.scrollTo(0, 0);
}

function prevIntakePage(num) {
	currentIntakePage = num;
	showIntakePage(num);
	window.scrollTo(0, 0);
}

// Conditional sections
document.addEventListener("change", (e) => {
	// Disagree amount section
	if (e.target.name === "i_agree_amount") {
		document
			.getElementById("i-disagree-section")
			.classList.toggle("hidden", e.target.value === "yes");
	}
	// 7-day repairs section
	if (e.target.name === "i_7day") {
		document
			.getElementById("i-repairs-section")
			.classList.toggle("hidden", e.target.value === "no");
	}
	// Hardship section
	if (e.target.name === "i_more_time") {
		document
			.getElementById("i-hardship-section")
			.classList.toggle("hidden", e.target.value === "no");
	}
	// Defense checkbox toggle
	if (e.target.classList.contains("def-checkbox")) {
		const item = e.target.closest(".defense-item");
		const explanation = item.querySelector(".defense-explanation");
		item.classList.toggle("checked", e.target.checked);
		explanation.classList.toggle("hidden", !e.target.checked);
	}
});

// Build intake review on page 6
const intakePage6Observer = new MutationObserver(() => {
	const page6 = document.getElementById("intake-page-6");
	if (!page6.classList.contains("hidden")) {
		buildIntakeReview();
	}
});
const intakeContainer = document.getElementById("screen-intake");
intakeContainer.addEventListener("transitionend", () => {});

// Simpler: just build review when clicking "Continue" to page 6
function nextIntakePage(num) {
	currentIntakePage = num;
	if (num === 6) buildIntakeReview();
	showIntakePage(num);
	window.scrollTo(0, 0);
}

function getIntakeData() {
	return {
		personal_info: {
			full_name: document.getElementById("i-full-name").value,
			also_known_as: document.getElementById("i-aka").value || null,
			co_tenants: document.getElementById("i-co-tenants").value
				? document
						.getElementById("i-co-tenants")
						.value.split(",")
						.map((s) => s.trim())
				: null,
			property_address: document.getElementById("i-property-address").value,
			property_city: document.getElementById("i-city").value,
			property_zip: document.getElementById("i-zip").value,
			county: document.getElementById("i-county").value,
			phone: document.getElementById("i-phone").value,
			email: document.getElementById("i-email").value,
			mailing_address: document.getElementById("i-mailing").value || null,
		},
		landlord_info: {
			landlord_name: document.getElementById("i-ll-name").value,
			landlord_address: document.getElementById("i-ll-address").value || null,
			landlord_phone: document.getElementById("i-ll-phone").value || null,
			landlord_email: document.getElementById("i-ll-email").value || null,
			landlord_attorney_name:
				document.getElementById("i-ll-attorney").value || null,
			landlord_attorney_email:
				document.getElementById("i-ll-attorney-email").value || null,
		},
		case_details: {
			case_number: document.getElementById("i-case-num").value,
			court_name: document.getElementById("i-court-name").value,
			received_3day_notice: getRadioValue("i_3day") === "yes",
			summons_service_date:
				document.getElementById("i-service-date").value || null,
			summons_service_method:
				document.getElementById("i-service-method").value || null,
			complaint_amount_claimed:
				parseFloat(
					document
						.getElementById("i-amount-claimed")
						.value.replace("$", "")
						.replace(",", ""),
				) || null,
			court_date: document.getElementById("i-court-date").value || null,
		},
		rent_payment: {
			monthly_rent:
				parseFloat(
					document
						.getElementById("i-monthly-rent")
						.value.replace("$", "")
						.replace(",", ""),
				) || 0,
			rent_due_day:
				parseInt(document.getElementById("i-rent-due-day").value) || 1,
			agree_with_amount: getRadioValue("i_agree_amount") !== "no",
			amount_tenant_believes_owed:
				parseFloat(
					document
						.getElementById("i-believed-owed")
						?.value?.replace("$", "")
						.replace(",", ""),
				) || null,
			why_disagree: document.getElementById("i-why-disagree")?.value || null,
			paid_after_notice: getRadioValue("i_paid_after") === "yes",
			sent_7day_repair_notice: getRadioValue("i_7day") === "yes",
			repair_notice_details:
				document.getElementById("i-repair-details")?.value || null,
			applied_for_rental_assistance: getRadioValue("i_rental_help") === "yes",
		},
		defenses: {
			def_repairs: getDefenseState("def_repairs"),
			def_amount: getDefenseState("def_amount"),
			def_attempted_pay: getDefenseState("def_attempted_pay"),
			def_paid: getDefenseState("def_paid"),
			def_waived: getDefenseState("def_waived"),
			def_retaliation: getDefenseState("def_retaliation"),
			def_fair_housing: getDefenseState("def_fair_housing"),
			def_accepted_rent: getDefenseState("def_accepted_rent"),
			def_corrected: getDefenseState("def_corrected"),
			def_not_owner: getDefenseState("def_not_owner"),
			def_bad_notice: getDefenseState("def_bad_notice"),
			def_other: getDefenseState("def_other"),
		},
		preferences: {
			needs_more_time: getRadioValue("i_more_time") === "yes",
			hardship_reason:
				document.getElementById("i-hardship-reason")?.value || null,
			wants_payment_plan: getRadioValue("i_payment_plan") === "yes",
			trial_by: getRadioValue("i_trial") || "judge",
		},
	};
}

function getDefenseState(key) {
	const item = document.querySelector(`.defense-item[data-defense="${key}"]`);
	if (!item) return { checked: false, explanation: null };
	const checkbox = item.querySelector(".def-checkbox");
	const explanation = item.querySelector(".def-explanation-input");
	return {
		checked: checkbox.checked,
		explanation: checkbox.checked ? explanation?.value || null : null,
	};
}

function buildIntakeReview() {
	const data = getIntakeData();
	const container = document.getElementById("intake-review");
	let html = '<div style="display: grid; gap: 0.75rem;">';

	const fields = [
		{ label: "Full name", value: data.personal_info.full_name },
		{
			label: "Property",
			value: `${data.personal_info.property_address}, ${data.personal_info.property_city}, FL ${data.personal_info.property_zip}`,
		},
		{ label: "County", value: data.personal_info.county },
		{ label: "Phone", value: data.personal_info.phone },
		{ label: "Email", value: data.personal_info.email },
		{ label: "Landlord", value: data.landlord_info.landlord_name },
		{ label: "Case number", value: data.case_details.case_number },
		{ label: "Court", value: data.case_details.court_name },
		{
			label: "Amount claimed",
			value: data.case_details.complaint_amount_claimed
				? `$${data.case_details.complaint_amount_claimed}`
				: "Not entered",
		},
	];

	fields.forEach((f) => {
		if (f.value) {
			html += `<div style="display: flex; gap: 0.5rem; font-size: 0.9rem; padding: 0.4rem 0; border-bottom: 1px solid var(--gray-100);">
                <span style="color: var(--gray-500); min-width: 120px;">${f.label}:</span>
                <span style="font-weight: 600;">${f.value}</span>
            </div>`;
		}
	});

	// Add defense count
	const defenseCount = Object.values(data.defenses).filter(
		(d) => d.checked,
	).length;
	html += `<div style="font-size: 0.9rem; padding: 0.4rem 0; border-bottom: 1px solid var(--gray-100);">
        <span style="color: var(--gray-500);">Defenses selected:</span>
        <span style="font-weight: 600;"> ${defenseCount}</span>
    </div>`;

	html += "</div>";
	container.innerHTML = html;
}

function submitIntake() {
	const data = getIntakeData();

	// Simple validation
	if (
		!data.personal_info.full_name ||
		!data.personal_info.phone ||
		!data.personal_info.email
	) {
		alert("Please fill in your name, phone, and email before submitting.");
		return;
	}
	if (!data.case_details.case_number) {
		alert("Please enter your case number from the summons.");
		return;
	}

	// For MVP, create a case ID locally and proceed to upload
	appState.caseId = "case-" + Date.now();

	// Store intake data in session for later use
	sessionStorage.setItem("intake_" + appState.caseId, JSON.stringify(data));

	showScreen("screen-upload");
	window.scrollTo(0, 0);
}

// ======================== DOCUMENT UPLOAD ========================

function triggerUpload(el) {
	const input = el.querySelector('input[type="file"]');
	if (input) input.click();
}

function handleUpload(input) {
	const file = input.files[0];
	if (!file) return;

	const zone = input.closest(".upload-zone");
	const doctype = zone.dataset.doctype;
	zone.classList.add("has-file");
	zone.querySelector(".upload-zone-text").textContent = `✅ ${file.name}`;

	appState.uploadedDocs.push({
		type: doctype,
		file: file,
		name: file.name,
	});

	// Upload to server immediately
	if (appState.caseId) {
		uploadToServer(file, doctype);
	}
}

async function uploadToServer(file, docType) {
	const formData = new FormData();
	formData.append("file", file);
	formData.append("doc_type", docType);

	try {
		const res = await fetch(`/api/v1/documents/upload/${appState.caseId}`, {
			method: "POST",
			body: formData,
		});
		if (!res.ok) {
			const err = await res.json();
			console.warn("Upload failed:", err.detail);
		}
	} catch (err) {
		console.warn("Upload network error:", err);
	}
}

async function startExtraction() {
	if (appState.uploadedDocs.length === 0) {
		alert("Please upload at least one document before proceeding.");
		return;
	}

	const btn = document.querySelector("#screen-upload .btn-primary");
	btn.disabled = true;
	btn.innerHTML = '<span class="spinner"></span> Processing Documents...';

	try {
		const res = await fetch(`/api/v1/documents/extract/${appState.caseId}`, {
			method: "POST",
		});
		const result = await res.json();

		if (result.status === "quality_issue") {
			alert(result.message + "\n\nPlease upload clearer copies.");
			btn.disabled = false;
			btn.textContent = "Process My Documents";
			return;
		}

		if (result.status === "extraction_error") {
			// Fall back to simulated data from intake form
			console.warn("Extraction error, using intake data:", result.message);
		}

		// Show confirmation with extracted data (or intake fallback)
		const extracted = result.extraction || buildFallbackExtraction();
		const conflicts = result.conflicts || [];
		showConfirmation({ fields: extracted, conflicts: conflicts });
	} catch (err) {
		console.warn("Extraction API error, using fallback:", err);
		const fallback = buildFallbackExtraction();
		showConfirmation({ fields: fallback, conflicts: [] });
	}
}

function buildFallbackExtraction() {
	return {
		full_name: document.getElementById("i-full-name").value,
		property_address: document.getElementById("i-property-address").value,
		county: appState.county,
		court_name: document.getElementById("i-court-name").value,
		case_number: document.getElementById("i-case-num").value,
		landlord_name: document.getElementById("i-ll-name").value,
		amount_claimed: document.getElementById("i-amount-claimed").value,
		notice_date: null,
		service_date: document.getElementById("i-service-date").value,
		court_date: document.getElementById("i-court-date").value || null,
		response_deadline: calculateDeadline(
			document.getElementById("i-service-date").value,
		),
	};
}

function calculateDeadline(serviceDate) {
	if (!serviceDate) return null;
	const d = new Date(serviceDate);
	let businessDays = 0;
	while (businessDays < 5) {
		d.setDate(d.getDate() + 1);
		const day = d.getDay();
		if (day !== 0 && day !== 6) businessDays++;
	}
	return d.toISOString().split("T")[0];
}

// ======================== CONFIRMATION SCREEN ========================

function showConfirmation(extracted) {
	showScreen("screen-confirmation");
	window.scrollTo(0, 0);

	const container = document.getElementById("confirmation-fields");
	const conflictsContainer = document.getElementById("confirmation-conflicts");

	// Show conflicts
	if (extracted.conflicts && extracted.conflicts.length > 0) {
		conflictsContainer.classList.remove("hidden");
		let conflictHtml = '<div class="conflict-banner">';
		conflictHtml +=
			'<div class="conflict-banner-title">⚠️ Data Conflicts Found</div>';
		extracted.conflicts.forEach((c) => {
			conflictHtml += `<div class="conflict-row"><strong>${c.field}:</strong> You said "<span style="color:var(--warning)">${c.intake_value}</span>" but document says "<span style="color:var(--warning)">${c.document_value}</span>"</div>`;
		});
		conflictHtml += "</div>";
		conflictsContainer.innerHTML = conflictHtml;
	}

	// Build field list
	const fields = [
		{
			key: "full_name",
			label: "Your full legal name",
			value: extracted.fields.full_name,
		},
		{
			key: "property_address",
			label: "Property address",
			value: extracted.fields.property_address,
		},
		{ key: "county", label: "County", value: extracted.fields.county },
		{
			key: "court_name",
			label: "Court name",
			value: extracted.fields.court_name,
		},
		{
			key: "case_number",
			label: "Case number",
			value: extracted.fields.case_number,
		},
		{
			key: "landlord_name",
			label: "Landlord / Plaintiff",
			value: extracted.fields.landlord_name,
		},
		{
			key: "amount_claimed",
			label: "Amount claimed",
			value: extracted.fields.amount_claimed,
		},
		{
			key: "service_date",
			label: "Date served",
			value: extracted.fields.service_date,
		},
		{
			key: "court_date",
			label: "Court date",
			value: extracted.fields.court_date || "None scheduled",
		},
		{
			key: "response_deadline",
			label: "Response deadline",
			value: extracted.fields.response_deadline || "Calculating...",
		},
	];

	let html = "";
	fields.forEach((f) => {
		html += `
            <div class="confirm-field" data-key="${f.key}">
                <div class="confirm-label">${f.label}</div>
                <div class="confirm-value" id="cf-${f.key}">${f.value || "—"}</div>
                <div class="confirm-status">✓ Confirmed</div>
                <div class="confirm-edit" onclick="editField('${f.key}')">Edit</div>
            </div>`;
	});
	container.innerHTML = html;

	// Enable checkbox listener
	document
		.getElementById("confirmation-sign")
		.addEventListener("change", function () {
			document.getElementById("btn-confirm").disabled = !this.checked;
		});
}

function editField(key) {
	const newVal = prompt(
		`Enter the correct value for "${key}":`,
		document.getElementById(`cf-${key}`).textContent,
	);
	if (newVal) {
		document.getElementById(`cf-${key}`).textContent = newVal;
	}
}

function confirmExtraction() {
	document.getElementById("btn-confirm").disabled = true;
	document.getElementById("btn-confirm").innerHTML =
		'<span class="spinner"></span> Generating Packet...';

	// In production, this would call the API to generate documents
	setTimeout(() => {
		showPacketReady();
	}, 2000);
}

// ======================== PACKET READY ========================

function showPacketReady() {
	showScreen("screen-ready");
	document.getElementById("ready-case-id").textContent = appState.caseId;
}

// ======================== INIT ========================

console.log("Eviction Defense app loaded");

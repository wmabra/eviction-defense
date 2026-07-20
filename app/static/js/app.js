/* evictions.help — Eligibility + Payment */
const COUNTY_DATA = {
  "AR": ["Benton","Columbia","Craighead","Crawford","Faulkner","Garland","Greene","Hempstead","Independence","Jefferson","Lonoke","Miller","Mississippi","Ouachita","Pulaski","Saline","Sebastian","Union","Washington","White"],
  "AZ": ["Apache","Cochise","Coconino","Gila","Glendale Market","Graham","Greenlee","La Paz","Maricopa","Mesa Market","Mohave","Navajo","Phoenix Market","Pima","Pinal","Santa Cruz","Scottsdale Market","Tucson Market","Yavapai","Yuma"],
  "CA": ["Alameda","Contra Costa","Fresno","Kern","Los Angeles","Monterey","Orange","Riverside","Sacramento","San Bernardino","San Diego","San Francisco","San Joaquin","San Mateo","Santa Clara","Solano","Sonoma","Stanislaus","Tulare","Ventura"],
  "CO": ["Adams","Arapahoe","Boulder","Broomfield","Denver","Douglas","Eagle","El Paso","Fremont","Garfield","Jefferson","La Plata","Larimer","Mesa","Montrose","Morgan","Pueblo","Routt","Summit","Weld"],
  "CT": ["Fairfield","Hartford","Litchfield","Middlesex","New Haven","New London","Tolland","Windham"],
  "FL": ["Brevard","Broward","Collier","Duval","Hillsborough","Lake","Lee","Manatee","Martin","Miami-Dade","Orange","Osceola","Palm Beach","Pasco","Pinellas","Polk","Sarasota","Seminole","St. Lucie","Volusia"],
  "GA": ["Bibb","Chatham","Cherokee","Clarke","Clayton","Cobb","Columbia","Coweta","DeKalb","Douglas","Fayette","Forsyth","Fulton","Gwinnett","Hall","Henry","Houston","Muscogee","Paulding","Richmond"],
  "IL": ["Champaign","Cook","DuPage","Kane","Kankakee","Kendall","LaSalle","Lake","Macon","Madison","McHenry","McLean","Peoria","Rock Island","Sangamon","St. Clair","Tazewell","Vermilion","Will","Winnebago"],
  "LA": ["Ascension","Bossier","Caddo","Calcasieu","East Baton Rouge","Iberia","Jefferson","Lafayette","Lafourche","Livingston","Orleans","Ouachita","Rapides","St. Charles","St. John the Baptist","St. Landry","St. Tammany","Tangipahoa","Terrebonne","Vernon"],
  "MA": ["Barnstable","Berkshire","Boston","Bristol","Cambridge","Dukes","Essex","Franklin","Hampden","Hampshire","Lowell","Middlesex","Nantucket","New Bedford","Norfolk","Plymouth","Springfield","Suffolk","Worcester","Worcester City"],
  "MI": ["Bay","Berrien","Calhoun","Eaton","Genesee","Ingham","Isabella","Jackson","Kalamazoo","Kent","Livingston","Macomb","Monroe","Muskegon","Oakland","Ottawa","Saginaw","St. Clair","Washtenaw","Wayne"],
  "MN": ["Anoka","Beltrami","Blue Earth","Carver","Clay","Crow Wing","Dakota","Hennepin","Kandiyohi","Olmsted","Otter Tail","Ramsey","Rice","Scott","Sherburne","St. Louis","Stearns","Washington","Winona","Wright"],
  "NM": ["Bernalillo","Chaves","Curry","Doña Ana","Eddy","Grant","Lea","Los Alamos","Luna","McKinley","Otero","Rio Arriba","Roosevelt","San Juan","San Miguel","Sandoval","Santa Fe","Taos","Torrance","Valencia"],
  "NV": ["Carson City","Churchill","Clark","Douglas","Elko","Eureka","Henderson Market","Humboldt","Lander","Lincoln","Lyon","Mesquite Market","Mineral","North Las Vegas Market","Nye","Pershing","Sparks Market","Storey","Washoe","White Pine"],
  "OR": ["Baker","Benton","Clackamas","Coos","Crook","Deschutes","Douglas","Jackson","Josephine","Klamath","Lane","Linn","Malheur","Marion","Multnomah","Polk","Umatilla","Union","Washington","Yamhill"],
  "RI": ["Bristol","Kent","Newport","Providence","Washington"],
  "SC": ["Aiken","Anderson","Beaufort","Berkeley","Charleston","Dorchester","Florence","Georgetown","Greenville","Greenwood","Horry","Kershaw","Lexington","Oconee","Orangeburg","Pickens","Richland","Spartanburg","Sumter","York"],
  "TN": ["Anderson","Blount","Bradley","Cumberland","Davidson","Hamilton","Knox","Madison","Maury","Montgomery","Putnam","Robertson","Rutherford","Sevier","Shelby","Sullivan","Sumner","Washington","Williamson","Wilson"],
  "TX": ["Bell","Bexar","Brazoria","Cameron","Collin","Dallas","Denton","El Paso","Fort Bend","Galveston","Harris","Hidalgo","Lubbock","McLennan","Montgomery","Nueces","Tarrant","Travis","Webb","Williamson"],
  "VA": ["Albemarle","Alexandria","Arlington","Chesapeake","Chesterfield","Fairfax","Hampton","Henrico","Loudoun","Lynchburg","Montgomery","Newport News","Norfolk","Prince William","Richmond City","Roanoke City","Rockingham","Spotsylvania","Stafford","Virginia Beach"]
};

const SUPPORTED_STATES = Object.keys(COUNTY_DATA);
const appState = { state: "", county: "" };

// Dynamic county dropdown
function updateCounties() {
  const state = document.getElementById("el-state").value;
  const select = document.getElementById("el-county");
  const counties = COUNTY_DATA[state] || [];
  select.innerHTML = '<option value="">Select your county</option>' +
    counties.map(c => '<option value="' + c + '">' + c + '</option>').join('');
  appState.state = state;
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("el-state").addEventListener("change", updateCounties);
});

// Eligibility check
function checkEligibility() {
  const btn = document.getElementById("btn-check");
  const state = document.getElementById("el-state").value;
  const county = document.getElementById("el-county").value;
  const isTenant = document.querySelector('input[name="el-tenant"]:checked');
  const isServed = document.querySelector('input[name="el-served"]:checked');
  const isResidential = document.querySelector('input[name="el-residential"]:checked');

  const result = document.getElementById("el-result");

  // Validate all fields
  if (!state || !county || !isTenant || !isServed || !isResidential) {
    result.className = "alert alert-error";
    result.textContent = "Please answer all 5 questions.";
    result.classList.remove("hidden");
    return;
  }

  // State check
  if (!SUPPORTED_STATES.includes(state)) {
    result.className = "alert alert-error";
    result.textContent = "We don't serve your state yet. We currently cover 20 states: " + SUPPORTED_STATES.join(", ") + ".";
    result.classList.remove("hidden");
    return;
  }

  // County check
  if (!COUNTY_DATA[state].includes(county)) {
    result.className = "alert alert-error";
    result.textContent = "We don't have " + county + " county available yet. We're expanding county by county.";
    result.classList.remove("hidden");
    return;
  }

  // Tenant check
  if (isTenant.value === "no") {
    result.className = "alert alert-error";
    result.textContent = "This service is for tenants named in the eviction. If you're not the tenant, we can't prepare your paperwork.";
    result.classList.remove("hidden");
    return;
  }

  // Served check
  if (isServed.value === "no") {
    result.className = "alert alert-info";
    result.textContent = "You need to have been served with court papers before we can prepare your answer. Please come back once you've received your summons.";
    result.classList.remove("hidden");
    return;
  }

  // Residential check
  if (isResidential.value === "no") {
    result.className = "alert alert-error";
    result.textContent = "We only handle residential evictions, not commercial. This service is not right for your situation.";
    result.classList.remove("hidden");
    return;
  }

  // ALL CHECKS PASSED — show payment
  appState.state = state;
  appState.county = county;
  result.classList.add("hidden");
  document.getElementById("eligibility-form").classList.add("hidden");
  document.getElementById("payment-section").classList.remove("hidden");
  document.getElementById("pay-email").focus();
}

// Payment via Authorize.net
function startPayment() {
  const email = document.getElementById("pay-email").value;
  if (!email) {
    alert("Please enter your email address for your receipt.");
    return;
  }

  const btn = document.getElementById("btn-pay");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Processing...';

  if (typeof Accept === "undefined") {
    // Dev mode — skip payment
    redirectToChat(email);
    return;
  }

  Accept.dispatchData({
    authData: {
      apiLoginID: "7wM69L5k7q2p",
      clientKey: "4r8CTQ7wQKYuGa266vv8WdXLD25pKfd8KgvA7j23NGs22mhLqVFVadczeXf5Gx42"
    },
    paymentData: { amount: 395.00, description: "Eviction Defense Packet" },
    callback: (response) => {
      if (response.messages.resultCode === "Error") {
        btn.disabled = false;
        btn.textContent = "Payment Failed — Try Again";
        return;
      }
      submitPayment(response.opaqueData, email);
    }
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
        customer_name: "Tenant"
      })
    });
    if (!res.ok) throw new Error("Payment failed");
    redirectToChat(email);
  } catch (e) {
    const btn = document.getElementById("btn-pay");
    btn.disabled = false;
    btn.textContent = "Payment Failed — Try Again";
  }
}

function redirectToChat(email) {
  window.location.href = "/chat?state=" + encodeURIComponent(appState.state) +
    "&county=" + encodeURIComponent(appState.county) +
    "&email=" + encodeURIComponent(email);
}

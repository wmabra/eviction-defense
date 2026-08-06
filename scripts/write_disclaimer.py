#!/usr/bin/env python3
"""Write proper legal disclaimer page for evictions.help."""

path = "/opt/eviction-defense/seo/disclaimer/index.html"

content = """<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Legal Disclaimer | evictions.help</title>
<meta name="description" content="Legal Disclaimer for evictions.help — a self-help eviction document preparation service.">
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="https://evictions.help/disclaimer/">
<link rel="icon" href="/assets/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="stylesheet" href="/assets/styles.css">
<meta property="og:type" content="website">
<meta property="og:image" content="https://evictions.help/assets/evictions-help-logo.png">
<meta property="og:site_name" content="evictions.help">
<meta property="og:title" content="Legal Disclaimer | evictions.help">
<meta property="og:description" content="Legal Disclaimer for evictions.help.">
<meta property="og:url" content="https://evictions.help/disclaimer/">
<meta name="twitter:card" content="summary_large_image">
</head><body>
<header class="site-header"><div class="container nav">
<a class="brand" href="/"><img src="/assets/evictions-help-logo.png" alt="evictions.help"></a>
<nav class="nav-links">
<a href="/#included">What's included</a><a href="/#how-it-works">How it works</a>
<a href="/#states">States</a><a href="/#faq">FAQ</a><a href="/contact">Contact</a>
<a class="nav-cta" href="/#eligibility">Check eligibility</a>
</nav></div></header>
<section class="section"><div class="container" style="max-width:800px">
<h1>Legal Disclaimer</h1>

<div class="notice" style="margin-bottom:24px">
<strong>Important:</strong> evictions.help is a self-help document preparation service. We are not a law firm, we do not provide legal advice, and we do not represent anyone in court.
</div>

<h2>Not Legal Advice</h2>
<p>The information and documents provided by evictions.help are for self-help purposes only. Nothing on this website, in our communications, or in the documents we prepare constitutes legal advice. Legal advice involves applying the law to your specific circumstances, which only a licensed attorney can do.</p>

<h2>No Attorney-Client Relationship</h2>
<p>Using evictions.help does not create an attorney-client relationship. Our service is a document preparation service. We do not represent you in court, negotiate with your landlord, or provide legal opinions about your case.</p>

<h2>No Guarantee of Results</h2>
<p>Every eviction case is unique. The outcome of your case depends on many factors, including the facts of your situation, applicable laws, the judge assigned to your case, and the actions of your landlord. evictions.help cannot predict or guarantee any particular outcome.</p>

<h2>Court Filing Responsibility</h2>
<p>You are solely responsible for reviewing your documents for accuracy, filing them with the appropriate court, meeting all deadlines, serving copies on the opposing party, and following all applicable court rules. Deadlines in eviction cases are strict. Failure to meet a deadline may result in a default judgment against you.</p>

<h2>Accuracy of Information</h2>
<p>Our documents are prepared based on the information you provide. You are responsible for ensuring that all information is accurate and complete. We recommend reviewing your documents carefully before filing.</p>

<h2>Consult an Attorney</h2>
<p>If you have questions about your legal rights, defenses, or court procedures, we recommend consulting with a licensed attorney in your state. Many areas have legal aid organizations that provide free or low-cost assistance to qualifying tenants. Your packet includes a resource sheet with contact information for legal aid organizations in your area.</p>

<h2>State-Specific Variations</h2>
<p>Eviction laws and procedures vary by state and sometimes by county. While we make efforts to tailor documents to your jurisdiction, you are responsible for confirming that all documents comply with local court requirements.</p>

<h2>Limitation of Liability</h2>
<p>To the fullest extent permitted by law, evictions.help disclaims all liability for any damages arising from your use of our service or reliance on the documents we prepare. Our liability is limited to the amount you paid for our service.</p>
</div></section>
<footer class="footer"><div class="container"><div class="footer-grid">
<div><img src="/assets/evictions-help-logo.png" alt="evictions.help"><p>AI-assisted self-help document preparation for residential tenants facing eviction. Flat fee: $399.</p></div>
<div><h3>Program</h3><div class="footer-links"><a href="/#included">Packet contents</a><a href="/#how-it-works">How it works</a><a href="/#states">Supported states</a><a href="/#faq">Frequently asked questions</a></div></div>
<div><h3>Important</h3><div class="footer-links"><a href="/terms/">Terms of use</a><a href="/privacy/">Privacy</a><a href="/disclaimer/">Legal disclaimer</a><a href="mailto:support@evictions.help">support@evictions.help</a></div></div>
</div><div class="footer-bottom">&copy; 2026 evictions.help. Self-help document preparation. Not a law firm. Not legal advice.</div></div></footer>
<script src="/assets/site.js" defer></script>
</body></html>"""

try:
    with open(path, "w") as f:
        f.write(content)
    print("Disclaimer written")
except OSError as e:
    print(f"Error: {e}")

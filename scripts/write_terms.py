#!/usr/bin/env python3
"""Write proper terms of use page for evictions.help."""

path = "/opt/eviction-defense/seo/terms/index.html"

content = """<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Terms of Use | evictions.help</title>
<meta name="description" content="Terms of Use for evictions.help — a self-help eviction document preparation service.">
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="https://evictions.help/terms/">
<link rel="icon" href="/assets/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="stylesheet" href="/assets/styles.css">
<meta property="og:type" content="website">
<meta property="og:image" content="https://evictions.help/assets/evictions-help-logo.png">
<meta property="og:site_name" content="evictions.help">
<meta property="og:title" content="Terms of Use | evictions.help">
<meta property="og:description" content="Terms of Use for evictions.help.">
<meta property="og:url" content="https://evictions.help/terms/">
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
<h1>Terms of Use</h1>
<p style="color:var(--muted)">Last updated: January 2026</p>

<h2>1. About evictions.help</h2>
<p>evictions.help is a self-help document preparation service. For a flat fee of $399, we prepare eviction defense paperwork based on information you provide. We are not a law firm. We do not provide legal advice, legal representation, or legal opinions. Nothing on this website or in our communications should be construed as legal advice.</p>

<h2>2. No Attorney-Client Relationship</h2>
<p>Your use of evictions.help does not create an attorney-client relationship. Our document preparation specialists are not attorneys and cannot provide legal advice. If you need legal advice, we recommend consulting with a licensed attorney in your state.</p>

<h2>3. Accuracy of Information</h2>
<p>You are responsible for providing accurate and complete information during the intake process. The documents we prepare are based solely on the information you provide. You must review all documents for accuracy before filing them with the court. evictions.help is not responsible for errors resulting from incorrect or incomplete information you provide.</p>

<h2>4. Document Filing and Court Procedures</h2>
<p>You are solely responsible for filing your documents with the appropriate court, serving copies on the opposing party, meeting all court deadlines, and following all applicable court rules and procedures. While our packet includes filing checklists and instructions, you bear ultimate responsibility for timely and proper filing.</p>

<h2>5. No Guaranteed Outcome</h2>
<p>evictions.help does not guarantee any particular outcome in your eviction case. Every case is different, and results depend on many factors including the facts of your case, the judge assigned, local court practices, and the actions of your landlord. We cannot predict or guarantee what will happen in court.</p>

<h2>6. Payment and Refunds</h2>
<p>The fee for our document preparation service is $399. Payment is processed through Authorize.net. Once your document packet has been generated and delivered, the fee is non-refundable. If we are unable to prepare your packet for any reason before delivery, you will receive a full refund. Refund requests should be directed to support@evictions.help.</p>

<h2>7. Eligibility</h2>
<p>Our service is available to residential tenants facing eviction in the 20 states we serve. We reserve the right to decline service to anyone for any reason, including but not limited to cases involving commercial property, cases where the tenant has already been evicted, cases involving criminal activity, or cases that fall outside our service capabilities.</p>

<h2>8. Intellectual Property</h2>
<p>All content on this website, including text, graphics, logos, and document templates, is the property of evictions.help and is protected by copyright and other intellectual property laws. You may not reproduce, distribute, or create derivative works from our content without our express written permission.</p>

<h2>9. Limitation of Liability</h2>
<p>To the fullest extent permitted by law, evictions.help and its owners, employees, and agents shall not be liable for any direct, indirect, incidental, consequential, or special damages arising from your use of our service, including but not limited to damages resulting from eviction, monetary judgments, or any other legal outcome.</p>

<h2>10. Third-Party Links and Resources</h2>
<p>Our website may contain links to third-party websites and resources, including legal aid organizations, rental assistance programs, and court websites. We do not endorse and are not responsible for the content, accuracy, or availability of these external resources.</p>

<h2>11. Changes to Terms</h2>
<p>We reserve the right to modify these terms at any time. Changes will be effective when posted on this page. Your continued use of our service after changes are posted constitutes acceptance of the modified terms.</p>

<h2>12. Governing Law</h2>
<p>These terms are governed by the laws of the State of Florida, without regard to conflict of law principles. Any disputes arising from these terms or your use of evictions.help shall be resolved in the courts of Palm Beach County, Florida.</p>

<h2>13. Contact</h2>
<p>For questions about these terms, contact us at support@evictions.help.</p>
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
    print("Terms of use written")
except OSError as e:
    print(f"Error: {e}")

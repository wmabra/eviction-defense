#!/usr/bin/env python3
"""Write proper privacy policy page for evictions.help."""
import os

path = "/opt/eviction-defense/seo/privacy/index.html"

content = """<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Privacy Policy | evictions.help</title>
<meta name="description" content="Privacy Policy for evictions.help — a self-help eviction document preparation service.">
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="https://evictions.help/privacy/">
<link rel="icon" href="/assets/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="stylesheet" href="/assets/styles.css">
<meta property="og:type" content="website">
<meta property="og:image" content="https://evictions.help/assets/evictions-help-logo.png">
<meta property="og:site_name" content="evictions.help">
<meta property="og:title" content="Privacy Policy | evictions.help">
<meta property="og:description" content="Privacy Policy for evictions.help.">
<meta property="og:url" content="https://evictions.help/privacy/">
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
<h1>Privacy Policy</h1>
<p style="color:var(--muted)">Last updated: January 2026</p>

<h2>Information We Collect</h2>
<p>When you use evictions.help, we collect the information you provide during the eligibility screening and intake process. This includes your name, email address, phone number, property address, details about your eviction case, landlord information, and uploaded documents. We also collect payment information processed through Authorize.net, our secure payment processor.</p>

<h2>How We Use Your Information</h2>
<p>Your information is used solely to prepare your eviction defense document packet and to communicate with you about your order. We do not sell, rent, or share your personal information with third parties for marketing purposes. Your case details are used exclusively for document preparation and related support communications.</p>

<h2>Payment Processing</h2>
<p>All payments are processed through Authorize.net, a secure PCI-compliant payment gateway. We do not store your full credit card number on our servers. Your payment information is transmitted directly to Authorize.net using their Accept.js secure tokenization.</p>

<h2>Data Security</h2>
<p>We implement industry-standard security measures to protect your personal information. Your data is transmitted over encrypted connections, and access to stored data is restricted to authorized personnel only. However, no method of electronic storage is 100% secure, and we cannot guarantee absolute security.</p>

<h2>Data Retention</h2>
<p>We retain your case information and prepared documents for as long as reasonably necessary to provide our service and comply with legal obligations. You may request deletion of your data by contacting us at support@evictions.help. Please note that we may retain certain information as required by law or for legitimate business purposes.</p>

<h2>Cookies and Tracking</h2>
<p>Our site uses essential cookies for session management and checkout functionality. We do not use tracking cookies for advertising or analytics purposes. Your eligibility answers may be temporarily stored in your browser session storage to maintain your place in the intake flow.</p>

<h2>Third-Party Services</h2>
<p>We use Authorize.net for payment processing, and may use email delivery services for order confirmations and support communications. These providers have their own privacy policies governing their use of your information. We do not control and are not responsible for their practices.</p>

<h2>Your Rights</h2>
<p>You have the right to access, correct, or delete your personal information. To exercise these rights, contact us at support@evictions.help. We will respond to your request within a reasonable timeframe.</p>

<h2>Children's Privacy</h2>
<p>Our service is not directed to individuals under 18 years of age. We do not knowingly collect personal information from children.</p>

<h2>Changes to This Policy</h2>
<p>We may update this privacy policy from time to time. Changes will be posted on this page with an updated effective date.</p>

<h2>Contact</h2>
<p>For questions about this privacy policy or our data practices, email us at support@evictions.help.</p>
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
    print("Privacy policy written")
except OSError as e:
    print(f"Error: {e}")

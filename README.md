# AI-Visibility Audit: zero-cost daily money machine

**Service:** productized "Can ChatGPT / Perplexity / Google AI find and cite your business?" audit for local SMBs.
Free scored report (lead magnet) -> $49 full fix-list + code -> $29/mo monthly re-check. Agencies buy white-label.

**Why this niche (honest view):** AI-answer visibility (GEO/AEO) is a new line item SMB owners are hearing about; most vendor tools target
marketers at $100+/mo, few sell a cheap, concrete, local-business fix. Evidence found is vendor-written, so *validate with 20 real
pitches before investing time*. Revenue is not guaranteed. Your conversion rate decides everything.

## Zero-cost stack
GitHub Actions (cron, free) -> `src/daily.py` -> reports in `docs/` on GitHub Pages (free) -> Stripe/Payfast/PayPal payment link
(fee only on sale) -> Gmail (your own, manual send) -> Claude Pro for writing fixes/pitches.

## Daily loop (automated part = steps 1-3, ~0 min of your time)
1. Add leads to `data/leads.csv` (name,url,email). Source free: Google Maps / directories / Facebook business pages, 25 a day.
2. Action audits new leads, writes `docs/<site>.html` and `data/outreach-<date>.md` drafts.
3. You (10 min/day on phone): open drafts, send 10-25 personalised emails/WhatsApps. Never mass-blast; include sender identity + opt-out (CAN-SPAM/GDPR/POPIA).
4. Buyer pays -> ask Claude to generate their fix pack from the audit JSON -> deliver in 24h.

## Setup (once)
```
gh repo settings: Pages -> branch main /docs ; Variables: PAY_URL (payment link), SITE_BASE (pages URL)
```
Test: `python3 -m unittest discover -s tests -v`   Run: `python3 src/daily.py`   Single: `python3 src/audit.py example.com`

## Targets
Week 1: 100 audits, 25 pitches/day. Expect ~1-3% reply, ~20-30% of replies buy. Month 1 goal: 5 sales ($245). Then upsell monthly.
Scale only what converts; kill it after 150 pitches with zero sales.

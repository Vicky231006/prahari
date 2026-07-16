# MASTER BUILD PROMPT — Project PRAHARI
### AI-Driven Correlation of Cybersecurity Telemetry & Transactional Behaviour
### FinSpark'26 (Bank of Maharashtra) — Problem Statement 2

> Working codename: **PRAHARI** (Hindi: sentinel/watchman). Rename freely — this is a real naming choice, not a placeholder, so it's fine to keep or swap.

---

## 0. ROLE AND OPERATING RULES FOR THE BUILD AGENT

You are the lead engineer building a working, demoable prototype for a national banking cybersecurity hackathon. The submission is judged on: **Business Potential & Relevance (40%), Security Considerations (30%), Uniqueness of Approach (15%), User Experience (5%), Scalability (5%), Ease of Development & Maintenance (5%)**. Every architectural decision below is already made with this weighting in mind — do not re-derive priorities, implement what's specified.

**Non-negotiable rules:**

1. **No placeholders, no stubs, no `TODO`, no lorem ipsum, no hardcoded fake "success" responses.** If a feature genuinely cannot be fully implemented in scope, implement a smaller *real* version of it and write exactly what's missing in `LIMITATIONS.md`. A silently faked feature is worse than an honestly incomplete one.
2. **Every dataset is either (a) real public reference data, cited, or (b) explicitly labeled synthetic data with a documented generation methodology.** Section 3 specifies exactly which is which. Never let synthetic data pass as real, and never let it go undocumented — judges will ask "is this real data?" and the honest, well-documented answer is a strength, not a weakness, if it's presented that way.
3. **This is a 4-day build.** Depth over breadth: the fusion engine, the RAG explanation layer, and the quantum module are the scored core (70% of the rubric). The dual-theme frontend is real but must not consume time disproportionate to its 5% UX weight — build it as a token-swap system (Section 8), not two parallel codebases.
4. **Dogfood security.** This submission is *about* security — any hardcoded secret, exposed key, or disabled auth in the repo is a credibility failure a judge will notice immediately. Use `.env` + `.env.example`, never commit real credentials, and gate any demo/testing endpoints behind an explicit non-production flag (Section 9).
5. Build in the phase order given in Section 11. Do not skip ahead to frontend polish before the pipeline moves real events end-to-end.

---

## 1. WHAT THIS SYSTEM DOES

Banks run fraud detection and cybersecurity monitoring (SOC/UEBA) as separate systems with separate teams and, in India, separate regulatory reporting tracks — RBI's Master Direction on Frauds routes to the Central Fraud Registry while the Cyber Security Framework routes incidents to RBI's cybersecurity cell on a 2–6 hour window, run in parallel rather than unified. PRAHARI correlates **identity-linked security telemetry** with **identity-linked transaction behaviour** in real time, so a security anomaly and a transaction anomaly on the same identity in the same time window are surfaced as one higher-confidence fused alert instead of two separate low-confidence ones — directly reducing false positives, which is a named expected outcome of PS2.

... (file continues with same content)
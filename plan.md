# plan.md — Vireo Audio Support Tickets (Set A)

## 0. Constraints & ground rules

- **Window:** 48 h from receipt. **Effort cap: ~5 h** — going over is not rewarded and is detectable. Cutting scope with stated reasons is graded.
- **Who reads the output (from the email thread):** Priya (CX) wants digest + leaderboard; **Arjun (Finance) wants to know what it saves and no surprise model bills**; **Neha (Ops) warns the leaderboard must not unfairly rank Warranty/Tier 2 and flags repeat contacts**. The memo and form answers must speak to all three.
- **Graded signals (submission form):** business number + money, cost-per-run arithmetic, validation/error rate, pushback on the ask, honest flaws, AI disclosure.
- Deliverables: (1) working tool, (2) business goal as a number, (3) proof it works, (4) one-page memo to Priya, (5) ≤3-min recording, (6) filled `submission-form.md`.

## 1. File inventory (as present in this workspace)

| Assignment file | Local name (UUID-prefixed) |
|---|---|
| tickets.csv | `cded5ec7-…-tickets.csv` (12,527 rows, 1 Jan 2025 → 30 Jun 2026) |
| agents.csv | `1bb95ea8-…-agents.csv` (44 agents, 44 rows — one per agent here) |
| orders.csv | `e5c326e5-…-orders.csv` (15,000 orders) |
| customers.csv | `52fbee44-…-customers.csv` (9,500 customers) |
| products.csv | `8e1b3214-…-products.csv` (14 SKUs) |
| support-policy.pdf | `(anonymous) - …-support-policy.pdf` |
| README.txt | `aa51ab7e-…-README.txt.pdf` (**actually a PDF**) |
| email-thread.txt | `1371b718-…-email-thread.txt.pdf` (**actually a PDF**) |

- [x] Extracted all three PDFs with `pdftotext -layout`; read email thread, README, policy v3.2.
- [ ] Step 0 of the tool: copy files to clean names (`data/tickets.csv` etc.) or handle names in config.

## 2. Data traps — confirmed by probe, must be handled in code

1. **Duplicate ticket_ids: 653 rows.** Policy §9: legacy Freshdesk tickets were re-imported during reconciliation — some tickets exist under both `source_system` values. **Deduplicate before any counting**, or the leaderboard and digest double-count.
2. **CSAT: 2,083 rows have `0`, 4,856 blank.** Policy §8: both mean "no response" → **exclude from averages, never treat as zero**.
3. **Legacy monetary units:** policy §9 says the legacy tool stored money in "its own native unit." Medians look similar (₹2,374 legacy vs ₹2,499 helpdesk) but per-row values need a sanity check (e.g., refund > retail price, sub-₹100 refunds) before summing any rupees.
4. **`transfers` exists only in the current helpdesk** — any transfer-cost math covers only helpdesk rows; say so.
5. **Blank `order_id`: 4,218 rows** — fallback join is `customer_id + product_sku` (README).
6. **644 tickets open/pending** with no `resolved_at` — exclude from resolution/leaderboard math, count as in-flight.
7. **Timestamps:** exports are IST-as-displayed, but legacy resolution times were reconstructed from a UTC event log; helpdesk API exports UTC. Keep everything in IST and note the caveat.
8. **Volume reality-check:** 12,527 tickets / 78 weeks ≈ **160 tickets/week in the export**, while the form says "Vireo's volume ≈ 650 tickets/week." Decision: run cost math at the form's 650/wk (that's what Vireo will hold us to) and note the export discrepancy in `DECISIONS.md`.
9. **Agents roster here is 1 row per agent**, but README says multiple rows per agent are possible — the tool should join on roster dates anyway (agent may have changed site/shift mid-18-months).
10. **Policy §5 hard rule:** no customer may receive **both** a refund and a replacement for the same order — worth an anomaly check; genuine findings here are free credibility.

## 3. Find the business number — *target: 45 min*

Cost standards from policy §3–4: contact cost chat ₹210 / email ₹260 / voice ₹520 / social ₹240 (blended ₹290); **SLA breach auto-issues ₹350 store credit**; internal transfer ₹305; agent ₹165/h. Arjun's hook: *"if it takes contacts out of the queue I'm interested."* Candidates, then pick the strongest:

- [ ] **First-response SLA breaches** (chat 15 min / voice 2 h / social 4 h / email 8 h): measure breach % by channel/team/shift; each breach = ₹350 credit. Goal shape: *"Cut chat breach rate from X% to Y%, saving ₹Z/quarter."*
- [ ] **Repeat contacts (policy §10):** same customer, same issue, within 30 days of resolution, costed at channel contact cost. Neha's "I already told your colleague this" complaint is a hint this is material — and the digest/classifier is exactly what surfaces their root causes. Likely the headline number.
- [ ] **Avoidable transfers:** transfers × ₹305, by routing/team.
- [ ] **Refund anomalies:** refund+replacement double-issuance, legacy unit errors, duplicate-ticket refunds.

**Output:** one line like *"Cut repeat contacts from X% → Y%, worth about ₹Z a quarter"* + a `DECISIONS.md` entry on why this metric over the others.

## 4. Build the tool — *target: 2 h, hard stop*

- [ ] **Stack:** Python + pandas + one LLM classification pass over free text; CLI that regenerates all outputs from the CSVs in one command. No web app.
- [ ] **Outputs Priya asked for:**
  - `weekly_digest.md` — complaints classified from `customer_message` (+`category` as prior), counts per week, week-over-week deltas, top movers.
  - `agent_leaderboard.csv` — **tickets closed per agent per week**, with the fairness fixes Neha's email + policy §6 demand: **Tier 2/Warranty shown separately or excluded** (multi-day cases by design), and per-agent attendance normalized by weeks active (roster `from_date`/`to_date`).
  - Cost summary of SLA credits / repeat-contact spend tied to the business number.
- [ ] **AI layer:** LLM classifies opening messages into a fixed category list with short rationale; **cache per ticket_id** so re-runs cost nothing; batch calls; log tokens+price per run to `run_costs.jsonl` (Arjun's "no surprise bill" → cost arithmetic becomes real).
- [ ] **README:** exact commands, deps, expected outputs; verify on a fresh venv.

## 5. Prove it works — *target: 45 min*

- [ ] Hand-label ~100 sampled `customer_message` rows; report accuracy, error rate, and **the kind of case it gets wrong** (Hinglish, multi-issue messages, "hii cannot login" style ambiguity).
- [ ] Deterministic cross-checks: leaderboard totals vs raw counts after dedup; SLA breach calc recomputed independently (e.g., pandas vs SQL); week-bucketing edge cases.
- [ ] Write `VALIDATION.md` — feeds form Q3 directly.

## 6. Memo to Priya Raman — *target: 30 min*

- [ ] One page, non-technical, ≤11 min read. Structure: the number and the money → what this month's digest shows → leaderboard with its caveat (volume ≠ quality; Tier 2 excluded by design) → what we'd do next quarter.
- [ ] Answer Arjun's cost question in the memo, not just the form.

## 7. Recording — *target: 30 min, ≤3 min video*

- [ ] Show: prompts used → what changed between versions → what was thrown away. Keep dead-end scripts and v1 prompts as artifacts so this is demonstrably true.

## 8. Submission form + repo hygiene — *target: 45 min*

- [ ] Fill **every** field of `submission-form.md` (unfilled = incomplete), including: outcome number + money; cost/run and monthly cost at 650 tickets/wk **with arithmetic**; validation stats; **pushback/narrowing** (can only raise the score — e.g., leaderboard fairness fix, digest alone doesn't move money without a costed metric); **known flaws** (can only raise the score); deliberate cuts; AI usage + video link; Drive link + the 3 things a Monday pickup needs; honest hours; GitHub link.
- [ ] Repo: clean-named data or config, README (clean-machine start), `DECISIONS.md`, `VALIDATION.md`, memo, recording link.

## Deliberate cut list (pick 3–4 and justify in the form)

- Dashboard/UI beyond markdown/CSV outputs.
- Deep NLP on `agent_notes` (only use it to validate classifier vs re-tags).
- Per-agent quality/CSAT scoring (low response rate ~45%, penalizes honest agents).
- Forecasting/trend prediction.
- Order/value joins beyond what the headline metric needs (blank order_id fallback only where necessary).
- Duplicate-detection sophistication beyond `ticket_id` dedup + spot checks.

## Time budget

| Phase | Target |
|---|---|
| ✅ Setup, PDFs, data probe | done (~45 min spent) |
| Business number | 45 min |
| Build | 2 h |
| Validation | 45 min |
| Memo | 30 min |
| Recording | 30 min |
| Form & repo | 45 min |
| **Remaining** | **~5 h → compress: label fewer tickets, memo drafts from form answers, one-script tool** |

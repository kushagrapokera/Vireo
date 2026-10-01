# implementation.md — what to build, phase by phase

Companion to `plan.md` (which covers the assignment strategy). This file is the **build plan**: modules, order of construction, outputs, and done-criteria for each phase. Shorthand: **P0–P6** below mean Phase 0 through Phase 6 as defined here.

## Architecture at a glance

```
data/*.csv ──► [P1 clean] ──► [P2 metrics] ──► [P4 report] ──► outputs/
                                  ▲                 ▲
                       [P3 classify: LLM + cache + fallback]
                                        [P5 validate] ──► VALIDATION.md
```

- **One CLI command regenerates everything:** `python -m vireo run` (or `make run`).
- **Every module independently runnable** so debugging and the recording have clean stages.
- No web app, no database, no scheduler. Python 3.11 + pandas + one LLM client.

## Repo layout

```
vireo-support-digest/
├── README.md              # clean-machine start: exact commands
├── requirements.txt
├── config.py              # paths + POLICY constants (single source of truth)
├── vireo/
│   ├── __init__.py
│   ├── load.py            # P1: read CSVs, handle UUID filenames
│   ├── clean.py           # P1: dedup, CSAT, refunds, fallback joins
│   ├── metrics.py         # P2: SLA, repeat contacts, leaderboard math
│   ├── classify.py        # P3: LLM categories + heuristic fallback + cache
│   ├── report.py          # P4: weekly_digest.md, agent_leaderboard.csv, costs
│   └── validate.py        # P5: sampling, cross-checks
├── data/                  # UUID-named originals (or renamed copies)
├── cache/                 # classifications.json (per ticket_id), never committed
├── outputs/               # weekly_digest.md, agent_leaderboard.csv, data_quality_report.md
├── run_costs.jsonl        # every paid call: ts, model, tokens, price
├── DECISIONS.md           # running log, started in P0
├── VALIDATION.md          # P5 output
└── memo.md                # P6
```

## POLICY constants (config.py — from support-policy.pdf, never hardcode inline)

| Constant | Value | Source |
|---|---|---|
| CONTACT_COST | chat ₹210, email ₹260, voice ₹520, social ₹240 | §4 |
| SLA_BREACH_CREDIT | ₹350 auto-issued on breach | §3 |
| SLA_TARGET | chat 15 min, voice 2 h, social 4 h, email 8 h | §3 |
| TRANSFER_COST | ₹305 | §4 |
| AGENT_HOUR | ₹165 | §4 |
| REPEAT_WINDOW | 30 days post-resolution | §10 |
| ATTENDANCE | status ∈ {resolved, closed} | §10 |

---

## Phase 0 — Skeleton & data access *(20 min)*

- [ ] `requirements.txt` (pandas, python-dotenv, openai or equivalent), repo init, `DECISIONS.md` opened.
- [ ] `load.py`: read the UUID-named files from a config dict — **no filename editing by hand**; fallback: copy to `data/` with clean names.
- [ ] Types: `created_at`, `first_response_at`, `resolved_at` → datetime (IST); category/priority/channel → ordered categoricals.
- **Done when:** `python -c "from vireo import load; load.tickets().shape"` prints `(12527, 21)`.

## Phase 1 — Cleaning & data-quality report *(45 min)* → `clean.py`

Order matters; each step logs its effect:

- [ ] **Dedup `ticket_id`** (653 dup rows): keep the `helpdesk` row over `legacy_fd`; if both legacy, keep latest `resolved_at`. Log count dropped.
- [ ] **CSAT:** `0` and blank → `NaN` (policy §8). Never averaged as zero.
- [ ] **Refund unit audit:** flag refund > product retail price, refund < ₹50, and compare legacy vs helpdesk distributions; decide (and log) a correction factor or exclusion rule for legacy refunds.
- [ ] **Fallback order join:** blank `order_id` (4,218 rows) → join on `customer_id + product_sku`; count matches recovered.
- [ ] **In-flight tickets:** 644 open/pending → excluded from resolution metrics, counted separately.
- [ ] Emit `outputs/data_quality_report.md` — every trap found, counts, and what we did. *This doubles as material for form Q5 ("what's wrong with this").*
- **Done when:** `clean.run()` returns a deduped frame with zero duplicate ticket_ids and the report file lists all checks with numbers.

## Phase 2 — Metrics engine *(45 min)* → `metrics.py`

Pure functions over the cleaned frame; no I/O beyond returning DataFrames.

- [ ] `sla_breaches()`: `first_response_at - created_at` vs per-channel target → breach flag; breach % by channel/team/week; cost = breaches × ₹350.
- [ ] `repeat_contacts()`: same `customer_id` with a new ticket within 30 days of a prior resolution (policy §10); cost = repeat count × channel contact cost. Needs the complaint tag from P3 to group "same issue" — v1 uses same `category`, upgrade in P4 to classifier label.
- [ ] `transfers_cost()`: sum(transfers) × ₹305, **helpdesk rows only** (field doesn't exist in legacy — log the caveat).
- [ ] `leaderboard()`: attendance (resolved+closed) per agent per week; join agents.csv on roster `from_date/to_date` → **weeks active**; output both raw and per-active-week; **Tier 2/Warranty agents in a separate table** (policy §6, Neha's email).
- [ ] `weekly_complaints()`: counts per category per ISO week, with week-over-week deltas.
- **Done when:** each function has a doctest/sanity assertion (e.g., leaderboard weekly totals == cleaned-frame weekly resolved counts).

## Phase 3 — AI classification *(60 min)* → `classify.py`

- [ ] Build the fixed category list: derive top labels from the existing intake-bot `category` column + skim ~50 messages; freeze ~8–12 categories + `unclear`.
- [ ] `heuristic_classify()`: keyword rules (cheap, deterministic, zero-cost) — **the always-works baseline**.
- [ ] `llm_classify()`: batched calls (50–100 messages/call), fixed JSON schema: `{ticket_id, category, confidence, rationale}`; temperature 0.
- [ ] **Cache per ticket_id** in `cache/classifications.json` → re-runs cost ₹0 (Arjun's no-surprise-bill requirement).
- [ ] **Cost logging:** append every call to `run_costs.jsonl`; `report.py` totals it.
- [ ] **No-API-key mode:** if no key in env, tool runs fully on the heuristic classifier and says so in the digest footer — clean-machine run never hard-fails.
- **Done when:** a 500-ticket sample classifies end-to-end with cache hits on second run and `run_costs.jsonl` shows real token counts.

## Phase 4 — Reports & headline number *(45 min)* → `report.py`

- [ ] `weekly_digest.md`: complaint categories × week table, week-over-week movers, SLA-credit spend, repeat-contact %, transfers cost; footer states classifier mode (LLM/heuristic) and run cost.
- [ ] `agent_leaderboard.csv`: per agent — weekly closes, weeks active, closes/active-week, Tier 2 separated; caveat line embedded as a comment row.
- [ ] `headline.md` (or digest header): the business goal as a number, e.g. *"Repeat contacts are X% of volume; cutting to Y% saves ₹Z/quarter — arithmetic shown"* — assembled from P2 outputs, no hand-typed numbers.
- [ ] Wire the CLI: `python -m vireo run` = load → clean → classify → metrics → reports.
- **Done when:** fresh venv + one command produces all three outputs without edits; numbers in headline.md re-derive from run_costs/data, not copy-paste.

## Phase 5 — Validation *(45 min)* → `validate.py`, `VALIDATION.md`

- [ ] `sample_for_labeling(n=100)`: stratified sample (by channel × category) → `labeling_sample.csv`; hand-label against classifier output.
- [ ] Report: accuracy, error rate, **failure taxonomy** (Hinglish, multi-issue, empty/one-word messages like "hii").
- [ ] Independent recomputation: SLA breach % and leaderboard totals via SQL (duckdb/sqlite) vs pandas; week-boundary edge cases (Mon/Sun starts, missing timestamps).
- [ ] `VALIDATION.md`: sample size, method, error rate, failure modes, what we'd fix with more time.
- **Done when:** every number quoted in the digest is either cross-checked or flagged as unchecked.

## Phase 6 — Packaging & deliverables *(45 min)*

- [ ] `README.md`: 3 commands (install, set key *optional*, run), expected outputs, data-file placement.
- [ ] Fresh-machine test: clone → venv → run.
- [ ] `memo.md` (one page to Priya — see plan.md §6), record the ≤3-min screen capture, fill `submission-form.md`, final `DECISIONS.md` pass.
- **Done when:** a stranger can run it from README alone, and every form field is filled.

---

## Skills in use (installed at `.agents/skills/`)

From `florianbuetow/claude-code` (note: `hatlesswizard/clean-code-skills` was rejected by the installer — broken YAML frontmatter in all 18 SKILL.md files):

| Skill | When it applies in this build |
|---|---|
| **kiss** | Guardrail while building P0–P4: run against new modules to catch over-abstraction, dead code, and unnecessary indirection. The tool must stay small — this is the enforcement. Also invoked before shipping ("kiss all" on `vireo/`). |
| **clean-code** | Pre-submission audit of the final codebase (naming, functions, error-handling, tests dimensions matter most here). Findings feed form Q5 ("what's wrong with what you're handing us") as honest, specific flaws. |
| **python-testing-patterns** (wshobson/agents) | Test suite for P2/P5: pytest fixtures + parametrized tests for dedup/CSAT/SLA edge cases, mocking for the LLM layer, coverage report cited in VALIDATION.md. Load when writing `tests/` in P1–P2, not after. |

Usage rule: kiss *during* each phase (cheap, catches bloat early); clean-code once after P5 freeze, before recording the walkthrough video — its findings should already be fixed or consciously accepted and documented.

## Build order & fallbacks

| If this slips | Cut in this order |
|---|---|
| Time pressure | LLM batching (use heuristic only, disclose) → SQL cross-check in P5 → repeat-contact upgrade in P4 (keep category-based v1) |
| API key/budget | Heuristic classifier is the shipped baseline; LLM is the upgrade, never the dependency |
| A phase fails | Ship P1–P2 (deterministic digest + leaderboard + headline number) — it stands alone; P3 improves complaint granularity |

**Never cut:** dedup logic (P1), leaderboard fairness (P2), cost logging (P3), validation honesty (P5). These are what the form scores.

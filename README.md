# Vireo Audio — support-ticket digest

Turns 18 months of Vireo support tickets into (1) a weekly complaint digest,
(2) an agent leaderboard, and (3) one business number in rupees. Built for the
Set A assignment: small tool, one command, no platform.

## Run it (clean machine)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m vireo --no-llm
```

That's the whole run. Outputs appear in `outputs/`:

| File | What it is |
|---|---|
| `weekly_digest.md` | Latest complete week's complaints by category, the repeat-contact headline number with its rupee arithmetic, and a 13-week trend |
| `agent_leaderboard.csv` | Tickets closed per agent, normalized by weeks active; Tier 2 (Escalations & Warranty) ranked separately per support-policy §6 |
| `data_quality_report.md` | Every data trap found and what was done about it |
| `VALIDATION.md` | Classifier accuracy (hand-labeled samples, in- and out-of-sample) and independent recomputation of every metric |

Optional tests: `python -m pytest tests/ -q` (needs `pytest`, `pytest-cov`).

## Optional: LLM classification

Without a key the tool is fully functional using a transparent keyword
classifier. To add LLM classification of customer messages:

```bash
pip install google-generativeai
export VIREO_LLM_API_KEY=your-key
python3 -m vireo            # drop --no-llm
```

- Classifications are cached per ticket in `cache/classifications.json`, so
  re-runs cost nothing.
- Every paid call is logged with tokens and price to `run_costs.jsonl`.
- Any LLM failure falls back to the keyword classifier; the run never breaks,
  and the digest footer states which mode produced the output.

## Data placement

The tool globs the assignment's files wherever they sit in the project root:
`*-tickets.csv`, `*-agents.csv`, `*-orders.csv`, `*-customers.csv`,
`*-products.csv` (the download's UUID filename prefixes are handled).
`support-policy.pdf` supplies the cost constants (in `vireo/config.py`).

> **The source data is not in this repository.** This repo is public, and the
> ticket export contains live customer records — verbatim complaint text, agent
> notes, and customer names with cities. Those files are excluded via
> `.gitignore` and must be supplied separately. Drop the pack into the project
> root and the commands above work unchanged; nothing in the code depends on the
> filenames. A fresh clone reproduces the committed `outputs/` only if you add
> the data.

## Layout

```
vireo/
  config.py     policy constants (₹ figures, SLA targets, 30-day repeat window)
  load.py       CSV loading with types
  clean.py      dedup, CSAT normalization, refund audit, order fallback
  metrics.py    SLA breaches, repeat contacts, leaderboard, weekly pivot
  classify.py   keyword classifier + optional cached LLM layer
  report.py     digest, leaderboard, headline number
  validate.py   cross-checks, labeling samples, VALIDATION.md
tests/          70 pytest tests (fixtures, parametrized edge cases, mocks)
cache/          labeling samples + hand labels (validation evidence)
outputs/        regenerated on every run
```

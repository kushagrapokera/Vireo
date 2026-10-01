# Validation — how we know the outputs are correct

## 1. Classifier accuracy (the AI-assisted part)

- Sample: **88 messages**, stratified across all 11 categories
  (8 per category where available), drawn from the cleaned attendance set.
- Method: each message labeled by hand from the customer's own words, then compared
  with the heuristic classifier the digest would use. LLM mode is optional and cached;
  the heuristic is the always-on baseline being measured here.
- **Accuracy: 100% out-of-sample** (88/88); 100% on the tuning draw (88/88)

### The kind of case it gets wrong

- None in this sample.

## 2. Independent recomputation of the metrics

| Check | Result |
|---|---|
| SLA breaches: vectorized vs per-row recomputation agree | yes (992) |
| Repeat contacts: shift-based vs loop-based recomputation agree | yes (1460) |
| Leaderboard closes sum to attended tickets | yes |
| Tier 2 kept out of the Tier 1 ranking | yes |
| Attendance rows balance (attended + in-flight = unique tickets) | yes |
| Unique ticket ids after dedup | yes |
| Week bucketing handles missing timestamps | yes |

## 3. What is still unvalidated

- Repeat-contact 'same issue' uses the (classified) category as a proxy; genuinely
  different problems in the same category count as repeats. The rate is therefore an
  upper bound, and the cost saving is stated on the same basis.
- The LLM path is validated only by its fallback guarantees (taxonomy check + heuristic
  fallback on failure); no paid batch was needed to produce this digest.
- CSAT and refund-amount fields were cleaned but are not part of any headline number.

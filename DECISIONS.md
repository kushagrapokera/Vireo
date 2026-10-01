# DECISIONS.md — decisions log

What we decided and why, in the order the work demanded it. The assignment
brief grades these explicitly.

## Data handling

1. **Dedup rule: prefer the helpdesk row over legacy_fd.** 653 tickets appear
   twice (Freshdesk re-import, policy §9). Duplicate pairs differ by exactly
   5h30m in `resolved_at` — the legacy event log stores UTC, the helpdesk
   displays IST — so the helpdesk row carries the trustworthy timestamp.
2. **CSAT `0` = blank = "no response".** Policy §8 says both mean no response;
   both are excluded from averages, never treated as zero.
3. **Refund units: no conversion.** Policy §9 warns the legacy tool stored
   money "in its own native unit". Checked empirically: legacy and helpdesk
   refund distributions agree (median 2374 vs 2499, identical max), zero refunds
   above 3x retail. All amounts are rupees; the §9 warning was a red herring in
   this export. The 3x-retail check stays in the pipeline as a tripwire.
4. **Order fallback is temporal, not arbitrary.** README says blank `order_id`
   joins on customer_id + product_sku, but 720 blank-order tickets match
   several orders and 456 naive picks were orders placed *after* the ticket —
   impossible. Rule: latest order dated on/before the ticket; 101 tickets have
   no such order and stay blank.
5. **Legacy `resolved_at < created_at` rows kept as-is.** The UTC
   reconstruction produces a small number of these; metrics treat them as
   ordinary resolutions, and the count is disclosed in the quality report.
6. **Volume discrepancy noted, not silently accepted.** The export runs ~160
   tickets/week over 78 weeks; the form says Vireo's volume is ~650/week. The
   export is presumably a filtered/eligible subset. Cost-per-run math in the
   form uses the form's 650 figure.

## Metrics

7. **Repeat-contact "same issue" = same category (classifier label), per §10.**
   A proxy: two genuinely different problems in one category count as repeats.
   The 13.0% rate is therefore an upper bound — stated wherever the number
   appears. Refining would need agent resolution notes, which are free text
   with their own noise.
8. **Leaderboard tier from the roster, not the ticket.** Tier 2 certification
   (§6) is a property of the agent. An earlier per-ticket version let one
   routed Warranty ticket re-tier a Tier-1 agent; the roster (6 Tier-2 agents)
   is authoritative. Tier 2 is displayed, never volume-ranked (Neha's email).
9. **Closes normalized by roster weeks active.** Raw closes punish agents who
   joined mid-window. The normalization is per active week, from roster dates.
10. **Repeat-flag chains through unresolved tickets.** A re-contact 2 days
    after a resolution is a repeat even if it is still open, and the next
    ticket must chain to the last actual resolution — found by the independent
    cross-check, regression-tested.

## Classifier

11. **Heuristic classifier is the shipped baseline; LLM is an optional upgrade.**
    Arjun's "no surprise model bill" and the clean-machine requirement both
    point the same way: zero paid calls must produce the full output.
12. **Vent-stripping before keyword matching.** Angry templates end with
    "I want my money back" regardless of the fault; without stripping, Returns
    & Refunds swallowed half the corpus (baseline accuracy 44%).
13. **First-fragment-wins matching.** Humans label the first issue mentioned;
    the classifier splits the message into fragments and takes the first match,
    so a later "Expected: refund" tail cannot override the real fault.
14. **Template messages are read via their Issue field.** The
    "Product: X ... Issue: ... Tried: ... Expected:" format is machine-written;
    the Issue field carries the fault, the Expected field is filler.
15. **Two labeled draws, not one.** Keywords tuned on an 88-message draw
    (seed 7), then scored on a fresh 88-message draw (seed 123) never seen
    during tuning. The out-of-sample number is the honest one.
16. **Labels are the customer's underlying issue, not the intake bot's tag.**
    12 of 88 tuning labels and 11 of 88 fresh labels differ from `category`
    (e.g. "box says Pulse 2 but inside is not what I paid for" = Delivery,
    not Returns). The bot's tag is a prior, not ground truth.

## Product

17. **No dashboard.** Priya: "Keep it simple, I don't need a platform."
    Markdown + CSV regenerate in one command.
18. **Digest uses the latest COMPLETE week.** The export ends mid-week; using
    the partial final week made every delta look like a crash (▲/▼ noise).
19. **The 10% target must be observed, not asserted.** Target = best rolling
    13-week repeat rate actually achieved in this export (9.3%). If no window
    had beaten 10%, the tool would print the 10% goal flagged as an assumption.
20. **CSAT deliberately absent from headline metrics.** ~45% response rate and
    a design that surveys auto-closed tickets make per-agent CSAT unfair; also
    explicitly out of the client ask.

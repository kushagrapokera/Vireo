"""Clean the ticket export (P1): dedup, CSAT, refund audit, order fallback.

Every step returns counts so data_quality_report can state what was done.
"""
import pandas as pd

from vireo import config

SOURCE_PRIORITY = {config.LEGACY_SOURCE: 0, "helpdesk": 1}


def drop_duplicate_imports(tickets: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """One row per ticket_id. Legacy Freshdesk rows were re-imported under both
    source systems (policy §9); prefer the helpdesk row — its resolved_at is
    stored in IST, while legacy rows keep the UTC event-log timestamp (observed
    delta: exactly 5h30m). Within a source, keep the latest resolved_at."""
    ranked = tickets.assign(_prio=tickets["source_system"].map(SOURCE_PRIORITY).fillna(-1))
    ranked = ranked.sort_values(["_prio", "resolved_at"])
    deduped = ranked.drop_duplicates(subset="ticket_id", keep="last").drop(columns="_prio")
    stats = {
        "rows_in": len(tickets),
        "duplicate_rows_dropped": len(tickets) - len(deduped),
        "unique_tickets": len(deduped),
    }
    return deduped, stats


def normalize_csat(tickets: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """0 and blank both mean 'no response' (policy §8) — exclude, never zero."""
    zeros = int((tickets["csat_score"] == 0).sum())
    blanks = int(tickets["csat_score"].isna().sum())
    tickets = tickets.copy()
    tickets.loc[tickets["csat_score"] == 0, "csat_score"] = pd.NA
    stats = {"csat_zeros_treated_as_no_response": zeros, "csat_blanks": blanks}
    return tickets, stats


def audit_refunds(tickets: pd.DataFrame, products: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Policy §9 says the legacy tool stored money in its own native unit.
    Checked: legacy and helpdesk refund distributions agree (median 2374 vs
    2499, same max) — no unit conversion applied. Flag-only guard: refunds
    above 3x retail price are reported, never silently dropped."""
    price_by_sku = products.set_index("sku")["retail_price_inr"]
    ceiling = tickets["product_sku"].map(price_by_sku)
    refund = tickets["refund_amount_inr"]
    implausible = refund.notna() & ceiling.notna() & (refund > ceiling * 3)
    stats = {
        "refund_rows": int(refund.notna().sum()),
        "refunds_over_3x_retail_flagged": int(implausible.sum()),
    }
    return tickets, stats


def fallback_order_join(tickets: pd.DataFrame, orders: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Blank order_id (README): customer_id + product_sku is the fallback join.
    Customers hold several orders of the same SKU, so pick the latest order
    dated on/before the ticket — a ticket cannot reference a future order.
    Tickets with no such order stay blank and are counted."""
    blank = tickets["order_id"].isna() & tickets["customer_id"].notna() & tickets["product_sku"].notna()
    candidates = orders.rename(columns={"sku": "product_sku"})[
        ["order_id", "customer_id", "product_sku", "order_date"]
    ].dropna(subset=["order_date"])
    matched = tickets.loc[blank, ["ticket_id", "created_at", "customer_id", "product_sku"]].merge(
        candidates, on=["customer_id", "product_sku"], how="left"
    )
    matched = matched[matched["order_id"].notna()]
    eligible = matched[matched["order_date"] <= matched["created_at"]]
    best = eligible.sort_values("order_date").groupby("ticket_id")["order_id"].last()

    tickets = tickets.copy()
    recovered = tickets["ticket_id"].map(best)
    tickets.loc[recovered.notna() & blank, "order_id"] = recovered[recovered.notna() & blank]
    stats = {
        "orders_blank_before": int(blank.sum()),
        "orders_recovered_via_fallback": int((recovered.notna() & blank).sum()),
        "orders_left_blank_no_prior_order": int((recovered.isna() & blank).sum()),
    }
    return tickets, stats


def split_inflight(tickets: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Open/pending tickets have no resolution (§10) — metrics use only the
    attendance set; in-flight rows stay visible in the quality report."""
    is_attended = tickets["status"].isin(config.ATTENDANCE_STATUSES)
    stats = {"inflight_tickets": int((~is_attended).sum()), "attended_tickets": int(is_attended.sum())}
    return tickets[is_attended].copy(), tickets[~is_attended].copy(), stats


def run(tickets: pd.DataFrame, orders: pd.DataFrame, products: pd.DataFrame) -> dict:
    """Full cleaning pass. Returns frames plus per-step stats for the report."""
    deduped, dedup_stats = drop_duplicate_imports(tickets)
    deduped, csat_stats = normalize_csat(deduped)
    deduped, refund_stats = audit_refunds(deduped, products)
    deduped, order_stats = fallback_order_join(deduped, orders)
    attended, inflight, inflight_stats = split_inflight(deduped)
    return {
        "tickets": deduped,
        "attended": attended,
        "inflight": inflight,
        "stats": {**dedup_stats, **csat_stats, **refund_stats, **order_stats, **inflight_stats},
    }

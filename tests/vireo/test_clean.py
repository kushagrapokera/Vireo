"""P1 cleaning: dedup, CSAT, refund audit, order fallback, in-flight split."""
import pandas as pd

from vireo import clean


def orders_for_end_to_end() -> pd.DataFrame:
    """C1 bought one unit before the TK-1 ticket date."""
    return pd.DataFrame(
        {
            "order_id": ["O9"],
            "customer_id": ["C1"],
            "sku": ["VA-EB-PL1"],
            "order_date": pd.to_datetime(["2026-05-01"]),
        }
    )


def _with_legacy_duplicate(tickets: pd.DataFrame) -> pd.DataFrame:
    legacy = tickets[tickets["ticket_id"] == "TK-1"].copy()
    legacy["source_system"] = "legacy_fd"
    legacy["resolved_at"] = legacy["resolved_at"] - pd.Timedelta(hours=5, minutes=30)
    return pd.concat([tickets, legacy], ignore_index=True)


def test_drop_duplicate_imports_keeps_helpdesk_row_over_legacy(tickets):
    duplicated = _with_legacy_duplicate(tickets)

    deduped, stats = clean.drop_duplicate_imports(duplicated)

    assert len(deduped) == len(tickets)
    assert stats["duplicate_rows_dropped"] == 1
    kept = deduped[deduped["ticket_id"] == "TK-1"].iloc[0]
    assert kept["source_system"] == "helpdesk"
    assert kept["resolved_at"] == pd.Timestamp("2026-06-01 12:00")


def test_drop_duplicate_imports_on_clean_frame_changes_nothing(tickets):
    deduped, stats = clean.drop_duplicate_imports(tickets)

    assert stats["duplicate_rows_dropped"] == 0
    assert len(deduped) == len(tickets)


def test_normalize_csat_maps_zero_to_no_response(tickets):
    normalized, stats = clean.normalize_csat(tickets)

    assert stats["csat_zeros_treated_as_no_response"] == 1
    assert normalized.loc[tickets["ticket_id"] == "TK-2", "csat_score"].isna().all()


def test_audit_refunds_flags_but_never_drops_implausible_amounts(tickets, products):
    tickets.loc[tickets["ticket_id"] == "TK-3", "refund_amount_inr"] = 50_000.0  # > 3x retail 2499
    tickets.loc[tickets["ticket_id"] == "TK-4", "refund_amount_inr"] = 2000.0  # plausible

    audited, stats = clean.audit_refunds(tickets, products)

    assert stats["refunds_over_3x_retail_flagged"] == 1
    assert stats["refund_rows"] == 2
    assert audited.loc[audited["ticket_id"] == "TK-3", "refund_amount_inr"].iloc[0] == 50_000.0


def test_fallback_order_join_recovers_latest_prior_order(tickets):
    orders = pd.DataFrame(
        {
            "order_id": ["O9", "O10"],
            "customer_id": ["C1", "C1"],
            "sku": ["VA-EB-PL1", "VA-EB-PL1"],
            "order_date": pd.to_datetime(["2026-05-01", "2026-05-20"]),
        }
    )
    tickets.loc[tickets["ticket_id"] == "TK-1", "order_id"] = None  # ticket 2026-06-01

    joined, stats = clean.fallback_order_join(tickets, orders)

    assert stats["orders_recovered_via_fallback"] == 1
    assert joined.loc[joined["ticket_id"] == "TK-1", "order_id"].iloc[0] == "O10"


def test_fallback_order_join_never_picks_future_order(tickets):
    orders = pd.DataFrame(
        {
            "order_id": ["O11"],
            "customer_id": ["C2"],
            "sku": ["VA-EB-PL1"],
            "order_date": pd.to_datetime(["2026-07-01"]),  # after ticket 2026-06-01
        }
    )
    tickets.loc[tickets["ticket_id"] == "TK-2", "order_id"] = None

    joined, stats = clean.fallback_order_join(tickets, orders)

    assert stats["orders_recovered_via_fallback"] == 0
    assert pd.isna(joined.loc[joined["ticket_id"] == "TK-2", "order_id"].iloc[0])


def test_fallback_order_join_leaves_unknown_customers_blank(tickets):
    empty_orders = pd.DataFrame(columns=["order_id", "customer_id", "sku", "order_date"])
    tickets.loc[tickets["ticket_id"] == "TK-2", "order_id"] = None  # C2 has no orders

    joined, stats = clean.fallback_order_join(tickets, empty_orders)

    assert stats["orders_recovered_via_fallback"] == 0
    assert pd.isna(joined.loc[joined["ticket_id"] == "TK-2", "order_id"].iloc[0])


def test_split_inflight_separates_open_and_pending(tickets):
    tickets.loc[tickets["ticket_id"] == "TK-5", "status"] = "open"
    tickets.loc[tickets["ticket_id"] == "TK-6", "status"] = "pending"

    attended, inflight, stats = clean.split_inflight(tickets)

    assert stats["attended_tickets"] == 6
    assert stats["inflight_tickets"] == 2
    assert set(inflight["status"]) == {"open", "pending"}


def test_run_end_to_end_applies_all_steps(tickets, products):
    duplicated = _with_legacy_duplicate(tickets)
    duplicated.loc[duplicated["ticket_id"] == "TK-7", "status"] = "open"
    duplicated.loc[duplicated["ticket_id"] == "TK-3", "refund_amount_inr"] = 50_000.0
    duplicated.loc[duplicated["ticket_id"] == "TK-1", "order_id"] = None  # recovered via (C1, SKU) fallback

    result = clean.run(duplicated, orders_for_end_to_end(), products)

    assert result["stats"]["duplicate_rows_dropped"] == 1
    assert result["stats"]["inflight_tickets"] == 1
    assert result["stats"]["refunds_over_3x_retail_flagged"] == 1
    assert result["stats"]["orders_recovered_via_fallback"] == 1
    assert result["attended"]["ticket_id"].is_unique

"""Cross-checks: independent recomputation must agree with P1/P2 results."""
import pandas as pd

from vireo import clean, validate


def _with_legacy_duplicate(tickets: pd.DataFrame) -> pd.DataFrame:
    legacy = tickets[tickets["ticket_id"] == "TK-1"].copy()
    legacy["source_system"] = "legacy_fd"
    legacy["resolved_at"] = legacy["resolved_at"] - pd.Timedelta(hours=5, minutes=30)
    return pd.concat([tickets, legacy], ignore_index=True)


def test_cross_check_attended_balances_and_is_unique(tickets):
    result = clean.run(_with_legacy_duplicate(tickets), _orders(), _products())

    checks = validate.cross_check_attended(result)

    assert checks == {
        "unique_ticket_ids": True,
        "row_balance": True,
        "attended_matches_status_union": True,
    }


def test_cross_check_sla_paths_agree(tickets):
    tickets.loc[tickets["ticket_id"] == "TK-2", "first_response_at"] = pd.Timestamp("2026-06-01 10:40")

    checks = validate.cross_check_sla(tickets)

    assert checks["agree"] is True
    assert checks["vectorized_breaches"] == checks["per_row_breaches"] == 1


def test_cross_check_repeats_paths_agree(tickets):
    tickets.loc[tickets["ticket_id"] == "TK-2", ["customer_id", "created_at", "first_response_at", "resolved_at"]] = [
        "C1",
        pd.Timestamp("2026-06-03 10:00"),
        pd.Timestamp("2026-06-03 10:40"),
        pd.Timestamp("2026-06-03 12:00"),
    ]

    checks = validate.cross_check_repeats(tickets)

    assert checks["agree"] is True
    assert checks["shift_based"] == checks["loop_based"] == 1



def _orders() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": ["O9"],
            "customer_id": ["C1"],
            "sku": ["VA-EB-PL1"],
            "order_date": pd.to_datetime(["2026-05-01"]),
        }
    )


def _products() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sku": ["VA-EB-PL1"],
            "retail_price_inr": [2499],
        }
    )


def test_cross_check_leaderboard_flags_misplaced_tier2(attended_tickets, agents):
    from vireo import metrics

    board = metrics.agent_leaderboard(attended_tickets, agents)
    checks = validate.cross_check_leaderboard(attended_tickets, board)

    assert checks == {
        "closes_sum_matches_attended": True,
        "tier2_rows_present": True,
        "no_tier2_in_tier1_ranking": True,
    }

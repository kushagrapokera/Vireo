"""Shared fixtures: small synthetic frames mirroring the export schema."""
import pandas as pd
import pytest


@pytest.fixture
def agents() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "agent_id": ["A1", "A2", "A3"],
            "name": ["Ann", "Ben", "Cai"],
            "site": ["Bengaluru", "Indore", "Bengaluru"],
            "team": ["Chat Frontline", "Chat Frontline", "Escalations & Warranty"],
            "shift": ["Day", "Night", "Day"],
            "tier": [1, 1, 2],
            "from_date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-01"]),
            "to_date": [pd.NaT, pd.NaT, pd.NaT],
        }
    )


@pytest.fixture
def tickets() -> pd.DataFrame:
    base = {
        "ticket_id": [f"TK-{i}" for i in range(1, 9)],
        "created_at": pd.to_datetime(
            [
                "2026-06-01 10:00", "2026-06-01 10:00", "2026-06-02 10:00",
                "2026-06-03 10:00", "2026-06-04 10:00", "2026-06-05 10:00",
                "2026-06-06 10:00", "2026-06-07 10:00",
            ]
        ),
        "first_response_at": pd.to_datetime(
            [
                "2026-06-01 10:05", "2026-06-01 10:40", "2026-06-02 11:00",
                "2026-06-03 10:05", "2026-06-04 10:05", "2026-06-05 10:05",
                "2026-06-06 10:05", "2026-06-07 10:05",
            ]
        ),
        "resolved_at": pd.to_datetime(
            [
                "2026-06-01 12:00", "2026-06-01 12:00", "2026-06-02 12:00",
                "2026-06-03 12:00", "2026-06-04 12:00", "2026-06-05 12:00",
                "2026-06-06 12:00", "2026-06-07 12:00",
            ]
        ),
        "status": ["resolved"] * 7 + ["closed"],
        "channel": ["chat", "chat", "email", "voice", "social", "chat", "chat", "email"],
        "customer_id": [f"C{i}" for i in range(1, 9)],
        "order_id": [f"O{i}" for i in range(1, 9)],
        "product_sku": ["VA-EB-PL1"] * 8,
        "category": ["Connectivity"] * 8,
        "priority": ["Normal"] * 8,
        "assigned_team": ["Chat Frontline"] * 7 + ["Email Frontline"],
        "agent_id": ["A1", "A1", "A2", "A2", "A1", "A1", "A1", "A2"],
        "transfers": [0, 1, 0, 2, 0, 0, 0, 0],
        "csat_score": [5, 0, 4, None, 3, None, 5, 2],
        "refund_amount_inr": [None, None, 5000.0, None, None, None, None, None],
        "refund_reason_code": [None] * 8,
        "replacement_issued": ["N"] * 8,
        "customer_message": ["msg"] * 8,
        "agent_notes": ["note"] * 8,
        "source_system": ["helpdesk"] * 8,
    }
    return pd.DataFrame(base)


@pytest.fixture
def products() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sku": ["VA-EB-PL1"],
            "product_name": ["Pulse True Wireless Earbuds"],
            "family": ["earbuds"],
            "launch_date": pd.to_datetime(["2024-03-01"]),
            "unit_cost_inr": [1120],
            "retail_price_inr": [2499],
            "warranty_months": [12],
        }
    )



@pytest.fixture
def attended_tickets(tickets):
    """Attendance set where A1/A2 are Tier 1 and A3 is Tier 2 (via assigned_team)."""
    tickets.loc[tickets["ticket_id"] == "TK-8", "assigned_team"] = "Escalations & Warranty"
    tickets.loc[tickets["ticket_id"] == "TK-8", "agent_id"] = "A3"
    return tickets

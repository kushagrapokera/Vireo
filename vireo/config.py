"""Paths and policy constants — single source of truth (support-policy.pdf v3.2)."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data files carry UUID prefixes from the download; glob so renaming stays unnecessary.
DATA_FILES = {
    "tickets": "*-tickets.csv",
    "agents": "*-agents.csv",
    "orders": "*-orders.csv",
    "customers": "*-customers.csv",
    "products": "*-products.csv",
}

# §4 — fully loaded cost per contact by channel (INR)
CONTACT_COST_INR = {"chat": 210, "email": 260, "voice": 520, "social": 240}

# §3 — first-response targets (minutes) and automatic breach credit
SLA_TARGET_MIN = {"chat": 15, "voice": 120, "social": 240, "email": 480}
SLA_BREACH_CREDIT_INR = 350

# §4 — internal transfer re-handling cost (current helpdesk rows only)
TRANSFER_COST_INR = 305

# §10 — repeat contact: same customer, same issue, within 30 days of resolution
REPEAT_WINDOW_DAYS = 30

# §10 — attendance = resolved or closed
ATTENDANCE_STATUSES = ("resolved", "closed")

# §6 — Tier 2 owns Escalations & Warranty; measured in days, never ranked on volume
TIER2_TEAM = "Escalations & Warranty"

LEGACY_SOURCE = "legacy_fd"

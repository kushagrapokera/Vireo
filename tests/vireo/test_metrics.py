"""P2 metrics: SLA breaches, repeat contacts, transfers, leaderboard, weekly."""
import pandas as pd
import pytest

from vireo import config, metrics


# --- SLA breaches -----------------------------------------------------------

def test_with_sla_breach_flags_only_late_first_response(tickets):
    # TK-1 chat answered in 5 min (target 15) -> no breach
    # TK-2 chat answered in 40 min -> breach
    # TK-3 email answered in 60 min (target 480) -> no breach
    flagged = metrics.with_sla_breach(tickets)

    assert not flagged.loc[flagged["ticket_id"] == "TK-1", "sla_breach"].iloc[0]
    assert flagged.loc[flagged["ticket_id"] == "TK-2", "sla_breach"].iloc[0]
    assert not flagged.loc[flagged["ticket_id"] == "TK-3", "sla_breach"].iloc[0]


def test_sla_breach_skips_tickets_without_first_response(tickets):
    tickets.loc[tickets["ticket_id"] == "TK-2", "first_response_at"] = pd.NaT

    flagged = metrics.with_sla_breach(tickets)

    assert not flagged.loc[flagged["ticket_id"] == "TK-2", "sla_breach"].iloc[0]


def test_sla_breach_summary_costs_350_per_breach(tickets):
    tickets.loc[tickets["ticket_id"] == "TK-2", "first_response_at"] = pd.Timestamp("2026-06-01 10:40")

    summary = metrics.sla_breach_summary(tickets)

    assert summary.loc["chat", "breaches"] == 1
    assert summary.loc["chat", "breach_cost_inr"] == config.SLA_BREACH_CREDIT_INR
    assert summary.loc["chat", "breach_rate"] == pytest.approx(1 / 4)


@pytest.mark.parametrize(
    "channel,response_min,expected",
    [
        ("chat", 15, False),      # at target: not a breach
        ("chat", 16, True),
        ("email", 480, False),    # 8h target
        ("voice", 121, True),     # 2h target
        ("social", 241, True),    # 4h target
    ],
)
def test_sla_targets_per_channel(tickets, channel, response_min, expected):
    row = tickets[tickets["channel"] == channel].iloc[0]
    tickets.loc[tickets["ticket_id"] == row["ticket_id"], "first_response_at"] = (
        row["created_at"] + pd.Timedelta(minutes=response_min)
    )

    flagged = metrics.with_sla_breach(tickets)

    actual = bool(flagged.loc[flagged["ticket_id"] == row["ticket_id"], "sla_breach"].iloc[0])
    assert actual is expected


# --- Repeat contacts --------------------------------------------------------

def test_with_repeat_flag_detects_contact_within_30_days_same_issue(tickets):
    # C1 again three days after TK-1 resolved: same category -> repeat contact
    tickets.loc[tickets["ticket_id"] == "TK-2", ["customer_id", "created_at", "first_response_at", "resolved_at"]] = [
        "C1",
        pd.Timestamp("2026-06-03 10:00"),
        pd.Timestamp("2026-06-03 10:40"),
        pd.Timestamp("2026-06-03 12:00"),
    ]

    flagged = metrics.with_repeat_flag(tickets)

    assert flagged.loc[flagged["ticket_id"] == "TK-2", "repeat_contact"].iloc[0]
    assert not flagged.loc[flagged["ticket_id"] == "TK-1", "repeat_contact"].iloc[0]


def test_with_repeat_flag_ignores_different_category(tickets):
    tickets.loc[tickets["ticket_id"] == "TK-2", ["customer_id", "category", "created_at", "first_response_at", "resolved_at"]] = [
        "C1",
        "Billing & Payments",
        pd.Timestamp("2026-06-03 10:00"),
        pd.Timestamp("2026-06-03 10:40"),
        pd.Timestamp("2026-06-03 12:00"),
    ]

    flagged = metrics.with_repeat_flag(tickets)

    assert not flagged.loc[flagged["ticket_id"] == "TK-2", "repeat_contact"].iloc[0]


def test_with_repeat_flag_ignores_contact_after_window(tickets):
    tickets.loc[tickets["ticket_id"] == "TK-2", ["customer_id", "created_at", "first_response_at", "resolved_at"]] = [
        "C1",
        pd.Timestamp("2026-07-05 10:00"),  # 34 days after resolution
        pd.Timestamp("2026-07-05 10:40"),
        pd.Timestamp("2026-07-05 12:00"),
    ]

    flagged = metrics.with_repeat_flag(tickets)

    assert not flagged.loc[flagged["ticket_id"] == "TK-2", "repeat_contact"].iloc[0]


def test_with_repeat_flag_keeps_chain_through_unresolved_ticket(tickets):
    """Regression: a chain C1->C2 with an unresolved intermediate row must still
    compare against C1's resolution, not NaN (policy §10: 'prior resolution')."""
    # C1: TK-1 resolved 01 Jun; C2: TK-2 created 03 Jun but never resolved; C3: TK-3 created 05 Jun
    tickets.loc[tickets["ticket_id"] == "TK-2", ["customer_id", "created_at", "first_response_at", "resolved_at", "status"]] = [
        "C1", pd.Timestamp("2026-06-03 10:00"), pd.Timestamp("2026-06-03 10:40"), pd.NaT, "open",
    ]
    tickets.loc[tickets["ticket_id"] == "TK-3", ["customer_id", "created_at", "first_response_at", "resolved_at"]] = [
        "C1", pd.Timestamp("2026-06-05 10:00"), pd.Timestamp("2026-06-05 10:20"), pd.Timestamp("2026-06-05 12:00"),
    ]
    # TK-3 is out of the 30-day test frame only if it were; it is 4 days after TK-1's resolution
    tickets = tickets[tickets["ticket_id"].isin(["TK-1", "TK-2", "TK-3"])]

    flagged = metrics.with_repeat_flag(tickets)

    # TK-2 re-contacted 2 days after TK-1's resolution: a repeat contact by §10
    # even though it is still open. TK-3 must chain through the unresolved TK-2
    # to TK-1's resolution (4 days) — under the old code its prior was NaN.
    assert flagged.loc[flagged["ticket_id"] == "TK-2", "repeat_contact"].iloc[0]
    assert flagged.loc[flagged["ticket_id"] == "TK-3", "repeat_contact"].iloc[0]


def test_with_repeat_flag_does_not_count_own_resolution(tickets):
    """Regression: a kept legacy row can carry resolved_at < created_at (UTC
    event-log artifact); the row must not repeat against itself."""
    tickets.loc[tickets["ticket_id"] == "TK-1", "resolved_at"] = pd.Timestamp("2026-06-01 06:00")  # before created_at

    flagged = metrics.with_repeat_flag(tickets)

    assert not flagged.loc[flagged["ticket_id"] == "TK-1", "repeat_contact"].iloc[0]


def test_agent_leaderboard_tier_from_roster_not_ticket_team(tickets, agents):
    """Regression: tier is a property of the agent (roster), not of the team a
    routed ticket was assigned to — one Tier-2 ticket must not re-tier an agent."""
    tickets.loc[tickets["ticket_id"] == "TK-1", "assigned_team"] = "Escalations & Warranty"  # routed to A1 (Tier 1)

    board = metrics.agent_leaderboard(tickets, agents)

    a1 = board[board["agent_id"] == "A1"].iloc[0]
    assert a1["tier"] == "Tier 1"
    assert a1["closes"] == 5  # all A1 tickets count in one row


def test_repeat_contact_summary_costs_channel_rate(tickets):
    tickets.loc[tickets["ticket_id"] == "TK-2", ["customer_id", "created_at", "first_response_at", "resolved_at"]] = [
        "C1",
        pd.Timestamp("2026-06-03 10:00"),
        pd.Timestamp("2026-06-03 10:40"),
        pd.Timestamp("2026-06-03 12:00"),
    ]  # repeat on chat

    summary = metrics.repeat_contact_summary(tickets)

    assert summary["repeat_contacts"] == 1
    assert summary["repeat_cost_inr"] == config.CONTACT_COST_INR["chat"]


# --- Transfers --------------------------------------------------------------

def test_transfer_cost_uses_helpdesk_rows_only(tickets):
    tickets["source_system"] = "helpdesk"
    legacy = tickets[tickets["ticket_id"] == "TK-4"].copy()
    legacy["source_system"] = "legacy_fd"
    legacy["transfers"] = 99
    tickets = pd.concat([tickets, legacy], ignore_index=True)

    result = metrics.transfer_cost(tickets)

    assert result["transfers"] == 3.0  # 1 + 2 from helpdesk rows; legacy 99 excluded
    assert result["transfer_cost_inr"] == 3 * config.TRANSFER_COST_INR


# --- Leaderboard ------------------------------------------------------------

def test_agent_leaderboard_separates_tier2_from_volume_ranking(attended_tickets, agents):
    board = metrics.agent_leaderboard(attended_tickets, agents)

    assert set(board["tier"]) == {"Tier 1", "Tier 2"}
    tier1 = board[board["tier"] == "Tier 1"]
    assert tier1["agent_id"].tolist() == ["A1", "A2"]  # sorted by closes per active week
    assert tier1["closes_per_active_week"].iloc[0] >= tier1["closes_per_active_week"].iloc[-1]


def test_agent_leaderboard_normalizes_by_weeks_active(attended_tickets, agents):
    # A2 joined 3 weeks into the period: same closes in fewer weeks must rank higher per week
    agents.loc[agents["agent_id"] == "A2", "from_date"] = pd.Timestamp("2026-06-15")
    attended_tickets = attended_tickets[attended_tickets["agent_id"] != "A3"]

    board = metrics.agent_leaderboard(attended_tickets, agents)

    per_week = board.set_index("agent_id")["closes_per_active_week"]
    assert per_week["A2"] > per_week["A1"]


def test_weeks_active_partial_roster_counts_started_weeks(agents):
    weeks = metrics.weeks_active(agents, "A1", pd.Timestamp("2026-06-21"))

    assert weeks >= 1  # roster from 2024-01-01 to period end


# --- Weekly complaints ------------------------------------------------------

def test_weekly_complaints_pivots_category_by_week(tickets):
    weekly = metrics.weekly_complaints(tickets)

    assert weekly.sum().sum() == len(tickets)
    assert (weekly.columns == ["Connectivity"]).all()


def test_week_over_week_movers_returns_rising_and_falling(tickets):
    weekly = metrics.weekly_complaints(tickets)

    movers = metrics.week_over_week_movers(weekly)

    assert {"category", "prev", "curr", "delta"} == set(movers.columns)


@pytest.fixture
def attended_tickets(tickets):
    """Attendance set where A1 is Tier 1 with 5 closes and A3 is Tier 2 with 1."""
    tickets.loc[tickets["ticket_id"] == "TK-8", "assigned_team"] = "Escalations & Warranty"
    tickets.loc[tickets["ticket_id"] == "TK-8", "agent_id"] = "A3"
    return tickets

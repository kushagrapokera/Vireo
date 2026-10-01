"""Metrics engine (P2): SLA breaches, repeat contacts, transfers, leaderboard.

Pure functions over cleaned frames — no I/O.
"""
import pandas as pd

from vireo import config


def with_response_minutes(tickets: pd.DataFrame) -> pd.DataFrame:
    delta = tickets["first_response_at"] - tickets["created_at"]
    return tickets.assign(response_min=delta.dt.total_seconds() / 60)


def with_sla_breach(tickets: pd.DataFrame) -> pd.DataFrame:
    """§3: first response later than the channel target. Missing first response
    (no human reply yet) is not a measurable breach."""
    t = with_response_minutes(tickets)
    target = t["channel"].map(config.SLA_TARGET_MIN)
    return t.assign(sla_breach=t["response_min"].notna() & (t["response_min"] > target))


def sla_breach_summary(tickets: pd.DataFrame) -> pd.DataFrame:
    t = with_sla_breach(tickets)
    measured = t[t["response_min"].notna()]
    summary = measured.groupby("channel").agg(
        tickets=("ticket_id", "count"),
        breaches=("sla_breach", "sum"),
    )
    summary["breach_rate"] = summary["breaches"] / summary["tickets"]
    summary["breach_cost_inr"] = summary["breaches"] * config.SLA_BREACH_CREDIT_INR
    return summary


def with_repeat_flag(tickets: pd.DataFrame) -> pd.DataFrame:
    """§10: same customer, same issue (category proxy), a new ticket within 30
    days of the latest prior resolution. ffill-then-shift keeps the chain intact
    when an intermediate row has no resolution timestamp."""
    t = tickets.sort_values(["customer_id", "category", "created_at"]).copy()
    last_resolution = t.groupby(["customer_id", "category"])["resolved_at"].ffill()
    prior_resolution = last_resolution.groupby([t["customer_id"], t["category"]]).shift()
    gap = t["created_at"] - prior_resolution
    within = (gap.dt.days >= 0) & (gap.dt.days <= config.REPEAT_WINDOW_DAYS)
    return t.assign(repeat_contact=within.fillna(False))


def repeat_contact_summary(tickets: pd.DataFrame) -> dict:
    t = with_repeat_flag(tickets)
    repeats = int(t["repeat_contact"].sum())
    cost = t.loc[t["repeat_contact"], "channel"].map(config.CONTACT_COST_INR).sum()
    by_category = (
        t[t["repeat_contact"]]
        .groupby("category")["ticket_id"]
        .count()
        .sort_values(ascending=False)
    )
    return {
        "repeat_contacts": repeats,
        "repeat_rate": repeats / len(t) if len(t) else 0.0,
        "repeat_cost_inr": float(cost),
        "top_categories": by_category.head(5),
    }


def transfer_cost(tickets: pd.DataFrame) -> dict:
    """§9: transfers exists only in the current helpdesk — legacy rows excluded."""
    helpdesk = tickets[tickets["source_system"] != config.LEGACY_SOURCE]
    total_transfers = float(helpdesk["transfers"].fillna(0).sum())
    return {
        "transfers": total_transfers,
        "transfer_cost_inr": total_transfers * config.TRANSFER_COST_INR,
        "scope_note": "helpdesk rows only; field absent in legacy_fd",
    }


def weeks_active(agents: pd.DataFrame, agent_id: str, period_end: pd.Timestamp) -> int:
    roster = agents[agents["agent_id"] == agent_id]
    weeks = 0.0
    for _, row in roster.iterrows():
        start = row["from_date"] if pd.notna(row["from_date"]) else period_end
        end = row["to_date"] if pd.notna(row["to_date"]) else period_end
        end = min(end, period_end)
        if end < start:
            continue
        weeks += max((end - start).days, 0) / 7
    return max(round(weeks), 1)


def agent_leaderboard(attended: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
    """Tickets closed per agent, normalized by weeks active. Tier comes from
    the roster, not the ticket's assigned team — an agent's certification (§6)
    is a property of the agent. Tier 2 rows are kept out of the Tier 1 ranking:
    their cases take days by design and must not be volume-ranked."""
    roster = agents.drop_duplicates("agent_id")
    tier_by_agent = roster.set_index("agent_id")["tier"].map({1: "Tier 1", 2: "Tier 2"})
    period_end = attended["created_at"].max()
    counts = attended.groupby("agent_id").agg(closes=("ticket_id", "count")).reset_index()
    counts["tier"] = counts["agent_id"].map(tier_by_agent)
    counts["weeks_active"] = counts["agent_id"].map(lambda a: weeks_active(agents, a, period_end))
    counts["closes_per_active_week"] = counts["closes"] / counts["weeks_active"]
    counts = counts.merge(roster[["agent_id", "name", "team", "site"]], on="agent_id", how="left")
    return counts.sort_values("closes_per_active_week", ascending=False)


def weekly_complaints(attended: pd.DataFrame) -> pd.DataFrame:
    """Category counts per ISO week — the core of the weekly digest."""
    weeks = attended["created_at"].dt.to_period("W")
    return (
        attended.assign(week=weeks)
        .pivot_table(index="week", columns="category", values="ticket_id", aggfunc="count", fill_value=0)
    )


def week_over_week_movers(weekly: pd.DataFrame, top: int = 3) -> pd.DataFrame:
    if len(weekly) < 2:
        return pd.DataFrame(columns=["category", "prev", "curr", "delta"])
    prev, curr = weekly.iloc[-2], weekly.iloc[-1]
    delta = (curr - prev).sort_values()
    movers = pd.DataFrame(
        {"prev": prev[delta.index], "curr": curr[delta.index], "delta": delta}
    )
    return pd.concat([movers.head(top), movers.tail(top)])

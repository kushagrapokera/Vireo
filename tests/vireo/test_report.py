"""P4 reports: headline number math, digest content, leaderboard caveats."""
import pandas as pd

from vireo import clean, report


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
    return pd.DataFrame({"sku": ["VA-EB-PL1"], "retail_price_inr": [2499]})


def test_headline_number_uses_policy_repeat_definition(tickets):
    tickets.loc[tickets["ticket_id"] == "TK-2", ["customer_id", "created_at", "first_response_at", "resolved_at"]] = [
        "C1",
        pd.Timestamp("2026-06-03 10:00"),
        pd.Timestamp("2026-06-03 10:40"),
        pd.Timestamp("2026-06-03 12:00"),
    ]

    headline = report.headline_number(tickets, {})

    assert headline["repeat_contacts"] == 1
    assert headline["current_rate"] == 1 / len(tickets)
    assert headline["repeat_cost_inr"] == 210.0  # chat channel cost
    assert headline["avg_repeat_cost_inr"] == 210.0
    assert headline["quarterly_saving_inr"] > 0


def test_headline_number_handles_zero_repeats(tickets):
    headline = report.headline_number(tickets, {})

    assert headline["repeat_contacts"] == 0
    assert headline["quarterly_saving_inr"] == 0


def test_write_digest_contains_headline_and_weekly_table(tickets, tmp_path, monkeypatch):
    monkeypatch.setattr(report.classify, "_CACHE_PATH", tmp_path / "cache" / "classifications.json")
    result = clean.run(tickets, _orders(), _products())
    classifications = {tid: {"category": "Connectivity", "source": "heuristic"} for tid in result["attended"]["ticket_id"]}
    out = tmp_path / "weekly_digest.md"

    report.write_digest(result["attended"], classifications, result, out)

    text = out.read_text()
    assert "repeat contacts" in text
    assert "per quarter" in text
    assert "| Connectivity |" in text
    assert "heuristic only" in text


def test_write_digest_classifies_missing_ids_from_intake_category(tickets, tmp_path, monkeypatch):
    monkeypatch.setattr(report.classify, "_CACHE_PATH", tmp_path / "cache" / "classifications.json")
    result = clean.run(tickets, _orders(), _products())
    classifications = {}  # classifier produced nothing: intake category must fill in
    out = tmp_path / "weekly_digest.md"

    report.write_digest(result["attended"], classifications, result, out)

    assert "| Connectivity |" in out.read_text()


def test_write_leaderboard_embeds_caveat_rows(attended_tickets, agents, tmp_path):
    from vireo import metrics

    out = tmp_path / "agent_leaderboard.csv"

    report.write_leaderboard(metrics.agent_leaderboard(attended_tickets, agents), out)

    text = out.read_text()
    assert "caveat" in text
    assert "not comparable with Tier 1 volume" in text
    assert "volume is not quality" in text

"""P5 validation: sampling, human-label agreement, edge cases, VALIDATION.md."""
import pandas as pd

from vireo import validate


def test_sample_for_labeling_is_stratified_and_bounded(tickets):
    tickets["category"] = [f"Cat{i % 4}" for i in range(len(tickets))]

    sample = validate.sample_for_labeling(tickets, n_per_category=2)

    assert len(sample) == 8  # 4 categories x 2
    assert set(sample.columns) == {"ticket_id", "category", "message"}
    assert sample["category"].value_counts().eq(2).all()


def test_heuristic_agreement_counts_matches_and_misses():
    sample = pd.DataFrame(
        {
            "ticket_id": ["TK-1", "TK-2"],
            "category": ["Connectivity", "Returns & Refunds"],
            "message": ["bluetooth pairing fails", "want my money back"],
        }
    )

    agreement = validate.heuristic_agreement(
        sample, {"TK-1": "Connectivity", "TK-2": "Returns & Refunds"}
    )

    assert agreement["n"] == 2
    assert agreement["accuracy"] == 1.0
    assert agreement["errors"] == []


def test_heuristic_agreement_records_error_kind():
    sample = pd.DataFrame(
        {
            "ticket_id": ["TK-1"],
            "category": ["Other"],
            "message": ["kuch karo urgent"],
        }
    )

    agreement = validate.heuristic_agreement(sample, {"TK-1": "Delivery & Shipping"})

    assert agreement["accuracy"] == 0.0
    assert agreement["errors"][0]["predicted"] == "Other"
    assert agreement["errors"][0]["human"] == "Delivery & Shipping"


def test_heuristic_agreement_ignores_unknown_ticket_ids():
    sample = pd.DataFrame({"ticket_id": ["TK-1"], "category": ["Other"], "message": ["x"]})

    agreement = validate.heuristic_agreement(sample, {"TK-999": "Other"})

    assert agreement["n"] == 0


def test_week_bucket_edge_cases_survive_missing_timestamps(tickets):
    checks = validate.week_bucket_edge_cases(tickets)

    assert checks["missing_timestamps_handled"] is True


def test_write_validation_md_renders_checks_and_errors(tickets, tmp_path):
    sample = pd.DataFrame({"ticket_id": ["TK-1"], "category": ["Other"], "message": ["kuch karo"]})
    agreement = validate.heuristic_agreement(sample, {"TK-1": "Delivery & Shipping"})
    checks = {
        "sla": {"agree": True, "vectorized_breaches": 1},
        "repeats": {"agree": True, "shift_based": 0},
        "board": {"closes_sum_matches_attended": True, "no_tier2_in_tier1_ranking": True},
        "attended": {"row_balance": True, "unique_ticket_ids": True},
        "week_edges": {"missing_timestamps_handled": True},
    }
    out = tmp_path / "VALIDATION.md"

    validate.write_validation_md(sample, agreement, checks, out)

    text = out.read_text()
    assert "Accuracy: 0%" in text
    assert "delivery/wrong-item language not matched: 1" in text
    assert "| SLA breaches: vectorized vs per-row recomputation agree | yes (1) |" in text
    assert "upper bound" in text  # honest limitation section present

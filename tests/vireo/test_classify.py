"""P3 classifier: heuristic rules, cache, LLM batching, total-coverage fallback."""
import json
from unittest.mock import patch

import pytest

from vireo import classify


# --- Heuristic baseline -----------------------------------------------------

@pytest.mark.parametrize(
    "message,expected",
    [
        ("refund not received yet", "Returns & Refunds"),
        ("refund was promised 15 days ago and nothing", "Returns & Refunds"),
        ("payment was deducted but no order was created", "Billing & Payments"),
        ("battery draining even when not in use", "Charging & Battery"),
        ("bluetooth pairing fails every time", "Connectivity"),
        ("app not opening after update", "App & Firmware"),
        ("only one side plays sound", "Audio Quality"),
        ("OTP not coming on my number", "Account & Login"),
        ("what is the status of my warranty claim", "Warranty & Repair"),
        ("before I buy - will this talk to a 2019 Samsung", "Product Enquiry"),
        ("order status stuck on shipped since 05/11", "Delivery & Shipping"),
        ("hi wrong product delivered the pulse 2 earbuds", "Delivery & Shipping"),
        ("i haven't received my order. what do i do now?", "Delivery & Shipping"),
        ("kuch karo urgent", "Other"),  # pure Hinglish, no English keyword
        ("", "Other"),  # empty message must not crash
    ],
)
def test_heuristic_classify_realistic_messages(message, expected):
    assert classify.heuristic_classify(message) == expected


def test_heuristic_classify_matches_across_case():
    assert classify.heuristic_classify("NOT DELIVERED YET") == "Delivery & Shipping"


def test_heuristic_rule_priority_refund_over_billing():
    # "refund" (Returns) beats "payment" (Billing) when both appear
    assert classify.heuristic_classify("payment done but want refund") == "Returns & Refunds"


# --- Cache ------------------------------------------------------------------

def test_load_cache_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(classify, "_CACHE_PATH", tmp_path / "cache" / "classifications.json")

    assert classify.load_cache() == {}


def test_save_and_load_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(classify, "_CACHE_PATH", tmp_path / "cache" / "classifications.json")

    classify.save_cache({"TK-1": {"category": "Other", "source": "llm"}})
    assert classify.load_cache() == {"TK-1": {"category": "Other", "source": "llm"}}


def test_classify_messages_uses_cache_before_llm(tmp_path, monkeypatch):
    monkeypatch.setattr(classify, "_CACHE_PATH", tmp_path / "cache" / "classifications.json")
    classify.save_cache({"TK-1": {"category": "Audio Quality", "source": "llm"}})
    monkeypatch.setenv("VIREO_LLM_API_KEY", "test-key")

    def fail_if_called(messages):
        raise AssertionError("LLM should not be called when everything is cached")

    with patch.object(classify, "_call_llm", side_effect=fail_if_called):
        results = classify.classify_messages({"TK-1": "only one side plays sound"})

    assert results["TK-1"] == {"category": "Audio Quality", "source": "cache"}


# --- LLM layer (mocked; no network, no cost) --------------------------------

def test_classify_messages_llm_success_path(tmp_path, monkeypatch):
    monkeypatch.setattr(classify, "_CACHE_PATH", tmp_path / "cache" / "classifications.json")
    monkeypatch.setenv("VIREO_LLM_API_KEY", "test-key")

    def fake_llm(messages):
        return [{"id": i + 1, "category": "Connectivity"} for i in range(len(messages))]

    with patch.object(classify, "_call_llm", side_effect=fake_llm):
        results = classify.classify_messages({"TK-1": "pairing fails", "TK-2": "drops constantly"})

    assert results["TK-1"] == {"category": "Connectivity", "source": "llm"}
    assert results["TK-2"] == {"category": "Connectivity", "source": "llm"}


def test_classify_messages_llm_result_is_cached(tmp_path, monkeypatch):
    cache_path = tmp_path / "cache" / "classifications.json"
    monkeypatch.setattr(classify, "_CACHE_PATH", cache_path)
    monkeypatch.setenv("VIREO_LLM_API_KEY", "test-key")

    def fake_llm(messages):
        return [{"id": 1, "category": "Charging & Battery"}]

    with patch.object(classify, "_call_llm", side_effect=fake_llm):
        classify.classify_messages({"TK-9": "battery drains"})

    assert json.loads(cache_path.read_text())["TK-9"]["category"] == "Charging & Battery"


def test_classify_messages_falls_back_when_llm_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(classify, "_CACHE_PATH", tmp_path / "cache" / "classifications.json")
    monkeypatch.setenv("VIREO_LLM_API_KEY", "test-key")

    def broken_llm(messages):
        raise RuntimeError("api down")

    with patch.object(classify, "_call_llm", side_effect=broken_llm):
        results = classify.classify_messages({"TK-1": "pairing fails"})

    assert results["TK-1"] == {"category": "Connectivity", "source": "heuristic"}


def test_classify_messages_rejects_llm_category_outside_taxonomy(tmp_path, monkeypatch):
    monkeypatch.setattr(classify, "_CACHE_PATH", tmp_path / "cache" / "classifications.json")
    monkeypatch.setenv("VIREO_LLM_API_KEY", "test-key")

    def lying_llm(messages):
        return [{"id": 1, "category": "Made Up Category"}]

    with patch.object(classify, "_call_llm", side_effect=lying_llm):
        results = classify.classify_messages({"TK-1": "pairing fails"})

    assert results["TK-1"] == {"category": "Connectivity", "source": "heuristic"}


def test_classify_messages_without_key_runs_heuristic_only(tmp_path, monkeypatch):
    monkeypatch.setattr(classify, "_CACHE_PATH", tmp_path / "cache" / "classifications.json")
    monkeypatch.delenv("VIREO_LLM_API_KEY", raising=False)

    def fail_if_called(messages):
        raise AssertionError("LLM must not be called without a key")

    with patch.object(classify, "_call_llm", side_effect=fail_if_called):
        results = classify.classify_messages({"TK-1": "refund pending"}, use_llm=False)

    assert results["TK-1"]["source"] == "heuristic"

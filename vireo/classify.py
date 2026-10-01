"""Classify customer messages into the digest's complaint categories (P3).

Two classifiers, same category set:
- heuristic: deterministic keyword rules, zero cost, always available
- llm: optional batched LLM calls, cached per ticket, cost-logged

The LLM never gates the run: no API key means the tool completes on heuristics
and the digest footer says which mode produced the output.
"""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from vireo import config

# The digest taxonomy: the intake bot's categories plus Other; frozen so
# classifier output, digest columns and repeat-contact grouping stay comparable.
CATEGORIES = [
    "Delivery & Shipping",
    "Billing & Payments",
    "Returns & Refunds",
    "Connectivity",
    "Charging & Battery",
    "App & Firmware",
    "Audio Quality",
    "Warranty & Repair",
    "Account & Login",
    "Product Enquiry",
    "Other",
]

_CACHE_PATH = config.PROJECT_ROOT / "cache" / "classifications.json"
_COST_LOG_PATH = config.PROJECT_ROOT / "run_costs.jsonl"
_MODEL = "gemini-2.0-flash"

# Emotional boilerplate stripped before matching: venting tails that appear in
# angry templates regardless of the actual fault ("I want my money back" on a
# mic complaint). Without this, Returns & Refunds swallows half the corpus.
VENT_TAILS = [
    "i want a replacement or refund, nothing else",
    "i want a replacement or refund",
    "i want my money back",
    "i want a replacement",
    "i want a refund",
    "process a refund to my original payment method",
    "i request you to process a refund",
    "fix this or i am posting on twitter",
    "not acceptable at this price",
    "honestly regretting this purchase",
    "i am losing patience",
    "escalate this to someone",
    "posting on twitter",
]

# Template messages follow "Product: X Order: Y ... Issue: <the actual fault>
# Tried: ... Expected: <boilerplate>". The Expected field is form filler, not
# signal — a human reads the Issue field first, so the classifier does too.
ISSUE_FIELD_RE = re.compile(r"issue:\s*(.+?)(?=\s*tried:|\s*expected:|$)", re.IGNORECASE | re.DOTALL)

# Free-text messages are scanned fragment by fragment: the first fragment that
# matches any rule decides the label, mirroring how a human reads the first
# issue mentioned. Later venting or tangents cannot override it.
FRAGMENT_SPLIT_RE = re.compile(r"[.!;\n]|\s(?:tried|expected):", re.IGNORECASE)


def _first_issue_fragment(text: str) -> str | None:
    for fragment in FRAGMENT_SPLIT_RE.split(text):
        hit = _match_rules(f" {fragment.strip()} ")
        if hit:
            return hit
    return None

# (category, keywords). Matched fragment-by-fragment (first mention wins, like
# a human reader); the list is the heuristic's entire knowledge, so every entry
# earns its place.
HEURISTIC_RULES = [
    ("Returns & Refunds", ["refund", "money back", "money for the return", "money has", "return pickup", "reverse pickup", "pickup scheduled", "nobody came for the pickup", "picked up the item", "packed the box", "return was accepted", "where is the money"]),
    ("Billing & Payments", ["payment", "deducted", "invoice", "invooice", "gst", "bank says", "statement", "promo code", "discount", "coupon", "charged twice", "no order id", "no order was created", "no orders", "paid on", "offer vanished", "clicked pay"]),
    ("Charging & Battery", ["battery", "charging", "charge it", "won't charge", "wont charge", "drain", "dies by", "charge twice a day", "battery level", "expensive brick", "no lights", "pressing the button"]),
    ("Connectivity", ["pairing", "cannot pair", "pair ", "bluetooth", "connects", "disconnect", "connection drops", "not discoverable", "doesn't see it", "losing my phone", "goes silent for a second", "stutters", "cutting out"]),
    ("App & Firmware", ["app not", "app closes", "app crashes", "crashing", "vireo app", "firmware", "update failed", "loading screen", "after update", "update prompt", "update is stuck", "update stuck", "progress bar", "spinning circle", "white screen", "the app"]),
    ("Audio Quality", ["one side", "one direction", "one ear", "no sound", "no audio", "buzzing", "frying sound", "crackling", "static", "distorted", "completely silent", "low volume", "microphone", "mic not", "mic is", "useless for meetings"]),
    ("Account & Login", ["otp", "sent me a code", "code never arrives", "login", "log in", "locked out", "password"]),
    ("Warranty & Repair", ["warranty", "repair", "service centre", "service center", "rma", "claim", "sent the unit", "pin came off", "unresponsive", "not responding", "tearing", "snapped", "strap pin"]),
    ("Product Enquiry", ["before i buy", "compatible", "comptaible", "work with iphone", "work with my", "does pulse2 work", "will this", "will the watch", "app run", "can i connect two"]),
    ("Delivery & Shipping", ["not delivered", "not been delivered", "delivery", "shipped", "shipping address", "delivery address", "tracking", "courier", "wrong product", "wrong item", "wrong colour", "wrong color", "ordered black", "got white", "got something else", "not what i paid for", "stuck on", "haven't received", "havent received", "parcel", "kicked here", "dent", "don't ship it", "cancel"]),
]


def _match_rules(text: str) -> str | None:
    for category, keywords in HEURISTIC_RULES:
        if any(keyword in text for keyword in keywords):
            return category
    return None


def heuristic_classify(message: str) -> str:
    text = str(message).lower()
    for tail in sorted(VENT_TAILS, key=len, reverse=True):
        text = text.replace(tail, " ")
    text = f" {text} "

    issue = ISSUE_FIELD_RE.search(text)
    if issue:
        hit = _match_rules(f" {issue.group(1)} ")
        if hit:
            return hit
    return _first_issue_fragment(text) or "Other"


def load_cache() -> dict:
    if _CACHE_PATH.exists():
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(cache, indent=1), encoding="utf-8")


def _log_cost(model: str, prompt_tokens: int, completion_tokens: int, cost_inr: float) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_inr": round(cost_inr, 6),
    }
    with _COST_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def _build_prompt(messages: list[str]) -> str:
    numbered = "\n".join(f"{i + 1}. {message[:280]}" for i, message in enumerate(messages))
    return (
        "Classify each customer complaint into exactly one category from this list:\n"
        f"{json.dumps(CATEGORIES)}\n\n"
        "Messages contain typos and Hinglish; judge by the underlying issue.\n"
        'Reply with only a JSON array of objects: [{"id": <number>, "category": "<name>"}]\n\n'
        f"{numbered}"
    )


def _call_llm(messages: list[str]) -> list[dict]:
    """One batched call. Raises on any failure; callers decide the fallback."""
    import google.generativeai as genai

    genai.configure(api_key=os.environ["VIREO_LLM_API_KEY"])
    model = genai.GenerativeModel(_MODEL)
    response = model.generate_content(_build_prompt(messages))
    text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
    _log_cost(
        model=_MODEL,
        prompt_tokens=response.usage_metadata.prompt_token_count,
        completion_tokens=response.usage_metadata.candidates_token_count,
        cost_inr=(response.usage_metadata.prompt_token_count * 0.000075 + response.usage_metadata.candidates_token_count * 0.0003) * 83.0,
    )
    return json.loads(text)


def classify_messages(messages: dict[str, str], use_llm: bool | None = None) -> dict[str, dict]:
    """Classify {ticket_id: message} -> {ticket_id: {category, source}}.

    Cache hits return first; LLM handles the rest in batches; anything the LLM
    misses or that fails falls back to the heuristic so output is always total.
    """
    if use_llm is None:
        use_llm = bool(os.environ.get("VIREO_LLM_API_KEY"))
    results: dict[str, dict] = {}
    cache = load_cache()

    for ticket_id, message in messages.items():
        if ticket_id in cache:
            results[ticket_id] = {**cache[ticket_id], "source": "cache"}
        else:
            results[ticket_id] = {"category": heuristic_classify(message), "source": "heuristic"}

    if not use_llm:
        return results

    pending = [tid for tid, r in results.items() if r["source"] == "heuristic"]
    batch_size = 60
    for start in range(0, len(pending), batch_size):
        batch_ids = pending[start : start + batch_size]
        try:
            reply = _call_llm([messages[tid] for tid in batch_ids])
        except Exception:
            continue  # heuristic result already in place
        for item in reply:
            tid = batch_ids[item["id"] - 1]
            if item["category"] in CATEGORIES:
                results[tid] = {"category": item["category"], "source": "llm"}
                cache[tid] = {"category": item["category"], "source": "llm"}
    save_cache(cache)
    return results

"""Load the Vireo CSV exports with correct dtypes (P0)."""
import pandas as pd

from vireo import config

TICKET_TIMESTAMP_COLS = ["created_at", "first_response_at", "resolved_at"]


def _find(name: str):
    matches = sorted(config.PROJECT_ROOT.glob(config.DATA_FILES[name]))
    if len(matches) != 1:
        raise FileNotFoundError(f"expected exactly one {name} file, found {len(matches)}: {matches}")
    return matches[0]


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(_find(name), low_memory=False)


def load_tickets() -> pd.DataFrame:
    tickets = _read("tickets")
    for col in TICKET_TIMESTAMP_COLS:
        tickets[col] = pd.to_datetime(tickets[col], errors="coerce")
    return tickets


def load_agents() -> pd.DataFrame:
    agents = _read("agents")
    for col in ("from_date", "to_date"):
        agents[col] = pd.to_datetime(agents[col], errors="coerce")
    return agents


def load_orders() -> pd.DataFrame:
    orders = _read("orders")
    orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
    return orders


def load_customers() -> pd.DataFrame:
    return _read("customers")


def load_products() -> pd.DataFrame:
    return _read("products")

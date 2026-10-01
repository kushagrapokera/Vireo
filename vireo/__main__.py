"""Run the full pipeline: load → clean → classify → metrics → reports.

Usage: python -m vireo [--no-llm]
"""
import argparse
from pathlib import Path

from vireo import clean, classify, config, load, metrics, report

OUTPUT_DIR = config.PROJECT_ROOT / "outputs"


def main() -> None:
    parser = argparse.ArgumentParser(description="Vireo support-ticket digest")
    parser.add_argument("--no-llm", action="store_true", help="force heuristic classification")
    args = parser.parse_args()

    tickets = load.load_tickets()
    agents = load.load_agents()
    orders = load.load_orders()
    products = load.load_products()

    result = clean.run(tickets, orders, products)
    report.write_report(result, OUTPUT_DIR / "data_quality_report.md")
    print(f"[1/4] cleaned: {result['stats']['unique_tickets']:,} unique tickets "
          f"({result['stats']['duplicate_rows_dropped']} duplicates dropped)")

    attended = result["attended"]
    messages = attended.dropna(subset=["customer_message"]).set_index("ticket_id")["customer_message"].to_dict()
    classifications = classify.classify_messages(messages, use_llm=not args.no_llm)
    print(f"[2/4] classified {len(classifications):,} messages "
          f"(llm: {sum(1 for c in classifications.values() if c['source'] == 'llm')}, "
          f"cache: {sum(1 for c in classifications.values() if c['source'] == 'cache')}, "
          f"heuristic: {sum(1 for c in classifications.values() if c['source'] == 'heuristic')})")

    board = metrics.agent_leaderboard(attended, agents)
    report.write_leaderboard(board, OUTPUT_DIR / "agent_leaderboard.csv")
    report.write_digest(attended, classifications, result, OUTPUT_DIR / "weekly_digest.md")
    print(f"[3/4] leaderboard: {board['agent_id'].nunique()} agents "
          f"(tier 1: {board.loc[board['tier'] == 'Tier 1', 'agent_id'].nunique()}, "
          f"tier 2: {board.loc[board['tier'] == 'Tier 2', 'agent_id'].nunique()})")

    headline = report.headline_number(attended, result["stats"])
    print(f"[4/4] headline: repeat contacts {headline['current_rate']:.1%} → target {headline['target_rate']:.0%}, "
          f"≈ ₹{headline['quarterly_saving_inr']:,.0f}/quarter")
    print(f"\nOutputs in {OUTPUT_DIR}/: weekly_digest.md, agent_leaderboard.csv, data_quality_report.md")


if __name__ == "__main__":
    main()

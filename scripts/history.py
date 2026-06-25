import os
import json
from datetime import datetime, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
HISTORY_DIR = os.path.join(DATA_DIR, "history")


def save_daily_snapshot(snapshot, focus_buys, cap_data, progress):
    """Save today's data as a snapshot file for tomorrow's comparison."""
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(HISTORY_DIR, f"{today}.json")

    snapshot_data = {
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "fx_rate": snapshot["fx_rate"],
        "total_portfolio_cad": snapshot["total_portfolio_cad"],
        "total_gain_cad": snapshot["total_gain_cad"],
        "total_gain_pct": snapshot["total_gain_pct"],
        "cash_cad": snapshot["cash_cad"],
        "positions": {},
        "zone_statuses": {},
        "cap_statuses": {},
        "breaches": [b["ticker"] for b in cap_data["breaches"]],
        "theme_exposure_pct": progress["theme_exposure_pct"],
        "core_pct": next(
            (b["current_pct"] for b in progress["buckets"] if b["key"] == "xeqt_core"),
            0,
        ),
    }

    for p in snapshot["positions"]:
        if "error" in p:
            continue
        snapshot_data["positions"][p["ticker"]] = {
            "price": p["live_price"],
            "value_cad": p["value_cad"],
            "weight_pct": p.get("weight_pct", 0),
            "gain_pct": p["gain_pct"],
            "currency": p["currency"],
        }

    for fb in focus_buys:
        if "error" not in fb:
            snapshot_data["zone_statuses"][fb["ticker"]] = fb["zone_status"]

    for c in cap_data["positions"]:
        snapshot_data["cap_statuses"][c["ticker"]] = c["status"]

    with open(filepath, "w") as f:
        json.dump(snapshot_data, f, indent=2)

    return filepath


def load_previous_snapshot():
    """Load the most recent snapshot before today."""
    today = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(HISTORY_DIR):
        return None

    files = sorted(
        [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json") and f[:10] != today],
        reverse=True,
    )

    if not files:
        return None

    filepath = os.path.join(HISTORY_DIR, files[0])
    with open(filepath, "r") as f:
        return json.load(f)


def calc_what_changed(current_snapshot, current_focus_buys, current_cap_data, prev):
    """Compare today vs the previous snapshot and return a list of changes."""
    changes = []

    if not prev:
        changes.append("First run — no previous snapshot to compare against.")
        return changes

    prev_date = prev.get("date", "unknown")

    portfolio_change = round(
        current_snapshot["total_portfolio_cad"] - prev["total_portfolio_cad"], 2
    )
    portfolio_pct = round(
        (portfolio_change / prev["total_portfolio_cad"]) * 100, 2
    ) if prev["total_portfolio_cad"] else 0
    sign = "+" if portfolio_change >= 0 else ""
    changes.append(
        f"Portfolio: ${current_snapshot['total_portfolio_cad']:,.2f} "
        f"({sign}${portfolio_change:,.2f} / {sign}{portfolio_pct:.1f}% since {prev_date})"
    )

    if current_snapshot["fx_rate"] != prev.get("fx_rate"):
        fx_change = round(current_snapshot["fx_rate"] - prev.get("fx_rate", 0), 4)
        sign = "+" if fx_change >= 0 else ""
        changes.append(
            f"USD/CAD: {current_snapshot['fx_rate']} ({sign}{fx_change})"
        )

    big_movers = []
    for p in current_snapshot["positions"]:
        if "error" in p:
            continue
        ticker = p["ticker"]
        prev_pos = prev.get("positions", {}).get(ticker)
        if not prev_pos:
            continue

        price_change_pct = round(
            ((p["live_price"] - prev_pos["price"]) / prev_pos["price"]) * 100, 2
        ) if prev_pos["price"] else 0

        if abs(price_change_pct) >= 2.0:
            sign = "+" if price_change_pct >= 0 else ""
            big_movers.append(
                f"{ticker} {sign}{price_change_pct:.1f}% "
                f"(${prev_pos['price']:.2f} -> ${p['live_price']:.2f})"
            )

    if big_movers:
        changes.append("Big movers (2%+): " + " | ".join(big_movers))

    for fb in current_focus_buys:
        if "error" in fb:
            continue
        ticker = fb["ticker"]
        prev_zone = prev.get("zone_statuses", {}).get(ticker)
        if prev_zone and prev_zone != fb["zone_status"]:
            changes.append(
                f"Zone change: {ticker} {prev_zone} -> {fb['zone_status']}"
            )

    prev_breaches = set(prev.get("breaches", []))
    current_breaches = set(b["ticker"] for b in current_cap_data["breaches"])
    new_breaches = current_breaches - prev_breaches
    resolved = prev_breaches - current_breaches
    if new_breaches:
        changes.append(f"New cap breaches: {', '.join(new_breaches)}")
    if resolved:
        changes.append(f"Cap breaches resolved: {', '.join(resolved)}")

    prev_core = prev.get("core_pct", 0)
    curr_core = next(
        (b["current_pct"] for b in []),
        0,
    )
    for p_item in current_snapshot["positions"]:
        if p_item.get("ticker") == "XEQT.TO" and "error" not in p_item:
            curr_core = p_item.get("weight_pct", 0)
    core_change = round(curr_core - prev_core, 1)
    if abs(core_change) >= 0.5:
        sign = "+" if core_change >= 0 else ""
        changes.append(f"XEQT core weight: {curr_core:.1f}% ({sign}{core_change}pp)")

    return changes


def print_what_changed(changes):
    """Print the what-changed summary."""
    print()
    print("=" * 80)
    print("  WHAT CHANGED SINCE YESTERDAY")
    print("=" * 80)
    for c in changes:
        print(f"  {c}")
    print("=" * 80)


if __name__ == "__main__":
    from fetch_prices import fetch_prices, fetch_fx_rate, get_all_tickers
    from portfolio import build_snapshot
    from targets import calc_target_progress
    from caps import check_caps
    from verdict import evaluate_focus_buys

    print("Fetching prices...")
    tickers = get_all_tickers()
    fx_rate = fetch_fx_rate()
    prices = fetch_prices(tickers)

    snapshot = build_snapshot(prices, fx_rate)
    progress = calc_target_progress(snapshot)
    cap_data = check_caps(snapshot)
    focus_buys = evaluate_focus_buys(prices, snapshot, cap_data)

    prev = load_previous_snapshot()
    changes = calc_what_changed(snapshot, focus_buys, cap_data, prev)
    print_what_changed(changes)

    filepath = save_daily_snapshot(snapshot, focus_buys, cap_data, progress)
    print(f"\n  Snapshot saved: {filepath}")

import os
import json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")


def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), "r") as f:
        return json.load(f)


def check_caps(snapshot):
    """Check every held position against its hard cap.

    Returns a list of dicts with cap status for each position, plus a list
    of breaches and warnings.
    """
    plan = load_json("plan.json")
    caps_config = plan["position_caps"]
    default_cap = caps_config["default_max_pct"]
    overrides = caps_config["overrides"]

    total_cad = snapshot["total_portfolio_cad"]
    results = []
    breaches = []
    warnings = []

    for p in snapshot["positions"]:
        if "error" in p:
            continue

        ticker = p["ticker"]
        value_cad = p["value_cad"]
        weight_pct = p.get("weight_pct", 0)

        cap_pct = overrides.get(ticker, default_cap)

        cap_value_cad = round((cap_pct / 100) * total_cad, 2)
        room_cad = round(cap_value_cad - value_cad, 2)
        room_pct = round(cap_pct - weight_pct, 1)

        breached = weight_pct > cap_pct
        near_cap = room_pct <= 2.0 and not breached

        if ticker in ("XEQT.TO", "VFV.TO"):
            status = "NO CAP"
            breached = False
            near_cap = False
            room_cad = None
            room_pct = None
        elif breached:
            status = "BREACH"
            breaches.append({
                "ticker": ticker,
                "weight_pct": weight_pct,
                "cap_pct": cap_pct,
                "over_by_pct": round(weight_pct - cap_pct, 1),
                "over_by_cad": round(value_cad - cap_value_cad, 2),
            })
        elif near_cap:
            status = "NEAR CAP"
        else:
            status = "OK"

        results.append({
            "ticker": ticker,
            "value_cad": value_cad,
            "weight_pct": weight_pct,
            "cap_pct": cap_pct,
            "cap_value_cad": cap_value_cad,
            "room_cad": room_cad,
            "room_pct": room_pct,
            "status": status,
        })

    high_beta_tickers = set()
    for bz in plan.get("buy_zones", []):
        if bz.get("score") and bz["score"] < 70:
            high_beta_tickers.add(bz["ticker"])

    high_beta_cad = sum(
        p["value_cad"] for p in snapshot["positions"]
        if "error" not in p and p["ticker"] in high_beta_tickers
    )
    high_beta_pct = round((high_beta_cad / total_cad) * 100, 1) if total_cad else 0
    if high_beta_pct > caps_config["high_beta_crypto_max_pct"]:
        warnings.append(
            f"High-beta exposure at {high_beta_pct}% — above {caps_config['high_beta_crypto_max_pct']}% threshold."
        )

    tiny_buy_threshold_cad = 5.0

    for r in results:
        if r["room_cad"] is not None and 0 < r["room_cad"] < tiny_buy_threshold_cad:
            warnings.append(
                f"{r['ticker']}: only ${r['room_cad']:.2f} CAD room to cap — too small for a meaningful buy."
            )

    return {
        "positions": sorted(results, key=lambda x: x["weight_pct"], reverse=True),
        "breaches": breaches,
        "warnings": warnings,
        "total_cad": total_cad,
    }


def print_cap_status(cap_data):
    """Print cap status in a readable format."""
    print()
    print("=" * 80)
    print("  CAP STATUS")
    print(f"  Portfolio total: ${cap_data['total_cad']:,.2f} CAD")
    print("=" * 80)

    print(f"\n  {'Ticker':<10} {'Wt%':>7} {'Cap%':>6} {'Status':>10} "
          f"{'$ Value':>10} {'$ Cap':>10} {'$ Room':>10}")
    print("-" * 80)

    for r in cap_data["positions"]:
        if r["status"] == "NO CAP":
            print(
                f"  {r['ticker']:<10} {r['weight_pct']:>6.1f}% {'—':>6} "
                f"{'—':>10} "
                f"${r['value_cad']:>9.2f} {'—':>10} {'—':>10}"
            )
        elif r["status"] == "BREACH":
            print(
                f"  {r['ticker']:<10} {r['weight_pct']:>6.1f}% {r['cap_pct']:>5.0f}% "
                f"{'*** BREACH':>10} "
                f"${r['value_cad']:>9.2f} "
                f"${r['cap_value_cad']:>9.2f} "
                f"${r['room_cad']:>9.2f}"
            )
        elif r["status"] == "NEAR CAP":
            print(
                f"  {r['ticker']:<10} {r['weight_pct']:>6.1f}% {r['cap_pct']:>5.0f}% "
                f"{'~NEAR CAP':>10} "
                f"${r['value_cad']:>9.2f} "
                f"${r['cap_value_cad']:>9.2f} "
                f"${r['room_cad']:>9.2f}"
            )
        else:
            print(
                f"  {r['ticker']:<10} {r['weight_pct']:>6.1f}% {r['cap_pct']:>5.0f}% "
                f"{'OK':>10} "
                f"${r['value_cad']:>9.2f} "
                f"${r['cap_value_cad']:>9.2f} "
                f"${r['room_cad']:>9.2f}"
            )

    if cap_data["breaches"]:
        print()
        print("  *** CAP BREACHES ***")
        for b in cap_data["breaches"]:
            print(
                f"  {b['ticker']}: {b['weight_pct']:.1f}% vs {b['cap_pct']}% cap — "
                f"over by {b['over_by_pct']}pp (${b['over_by_cad']:.2f} CAD). "
                f"DO NOT ADD. Shrinks by dilution only."
            )

    if cap_data["warnings"]:
        print()
        for w in cap_data["warnings"]:
            print(f"  *** {w}")

    print("=" * 80)


if __name__ == "__main__":
    from fetch_prices import fetch_prices, fetch_fx_rate, get_all_tickers
    from portfolio import build_snapshot

    print("Fetching prices...")
    tickers = get_all_tickers()
    fx_rate = fetch_fx_rate()
    prices = fetch_prices(tickers)

    snapshot = build_snapshot(prices, fx_rate)
    cap_data = check_caps(snapshot)
    print_cap_status(cap_data)

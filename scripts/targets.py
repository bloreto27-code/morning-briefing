import os
import json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")


def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), "r") as f:
        return json.load(f)


CONVICTION_TICKERS = {"CEG", "ETN", "GEV", "OSS", "PWR", "SOFI", "VFV.TO"}
TIER2_TICKERS = {"BWXT", "MSFT", "PLTR"}
CORE_TICKERS = {"XEQT.TO"}


def calc_target_progress(snapshot):
    """Compare current allocation vs target allocation per bucket.

    Takes the snapshot dict from portfolio.build_snapshot().
    Returns a list of bucket dicts with current vs target numbers.
    """
    plan = load_json("plan.json")
    target_alloc = plan["target_allocation"]
    total_cad = snapshot["total_portfolio_cad"]
    target_total = plan["target_portfolio_cad"]

    core_cad = 0.0
    tier2_cad = 0.0
    conviction_cad = 0.0

    for p in snapshot["positions"]:
        if "error" in p:
            continue
        ticker = p["ticker"]
        val = p["value_cad"]

        if ticker in CORE_TICKERS:
            core_cad += val
        elif ticker in TIER2_TICKERS:
            tier2_cad += val
        elif ticker in CONVICTION_TICKERS:
            conviction_cad += val

    cash_cad = snapshot["cash_cad"]

    buckets = [
        {
            "key": "xeqt_core",
            "label": target_alloc["xeqt_core"]["label"],
            "current_cad": round(core_cad, 2),
            "current_pct": round((core_cad / total_cad) * 100, 1) if total_cad else 0,
            "target_pct": target_alloc["xeqt_core"]["target_pct"],
            "target_cad_at_5k": target_alloc["xeqt_core"]["target_cad"],
            "gap_cad": round(target_alloc["xeqt_core"]["target_cad"] - core_cad, 2),
            "notes": target_alloc["xeqt_core"]["notes"],
        },
        {
            "key": "tier2",
            "label": target_alloc["tier2"]["label"],
            "current_cad": round(tier2_cad, 2),
            "current_pct": round((tier2_cad / total_cad) * 100, 1) if total_cad else 0,
            "target_pct": target_alloc["tier2"]["target_pct"],
            "target_cad_at_5k": target_alloc["tier2"]["target_cad"],
            "gap_cad": round(target_alloc["tier2"]["target_cad"] - tier2_cad, 2),
            "notes": target_alloc["tier2"]["notes"],
        },
        {
            "key": "conviction",
            "label": target_alloc["conviction"]["label"],
            "current_cad": round(conviction_cad, 2),
            "current_pct": round((conviction_cad / total_cad) * 100, 1) if total_cad else 0,
            "target_pct": target_alloc["conviction"]["target_pct"],
            "target_cad_at_5k": target_alloc["conviction"]["target_cad"],
            "gap_cad": round(target_alloc["conviction"]["target_cad"] - conviction_cad, 2),
            "notes": target_alloc["conviction"]["notes"],
        },
        {
            "key": "cash",
            "label": target_alloc["cash"]["label"],
            "current_cad": round(cash_cad, 2),
            "current_pct": round((cash_cad / total_cad) * 100, 1) if total_cad else 0,
            "target_pct": target_alloc["cash"]["target_pct"],
            "target_cad_at_5k": target_alloc["cash"]["target_cad"],
            "gap_cad": round(target_alloc["cash"]["target_cad"] - cash_cad, 2),
            "notes": target_alloc["cash"]["notes"],
        },
    ]

    theme_exposure_cad = conviction_cad + tier2_cad
    theme_pct = round((theme_exposure_cad / total_cad) * 100, 1) if total_cad else 0

    diversified_pct = round((core_cad / total_cad) * 100, 1) if total_cad else 0

    warnings = []
    if diversified_pct < target_alloc["xeqt_core"]["target_pct"]:
        diff = round(target_alloc["xeqt_core"]["target_pct"] - diversified_pct, 1)
        warnings.append(
            f"UNDER-DIVERSIFIED: XEQT core is {diversified_pct}% vs {target_alloc['xeqt_core']['target_pct']}% target "
            f"({diff}pp below). Prioritize funding core."
        )
    if theme_pct > 50:
        warnings.append(
            f"THEME CONCENTRATION: Single-theme (AI/power/nuclear) exposure at {theme_pct}% — above 50% threshold."
        )

    return {
        "buckets": buckets,
        "theme_exposure_pct": theme_pct,
        "diversified_pct": diversified_pct,
        "total_cad": total_cad,
        "target_total_cad": target_total,
        "gap_to_target_cad": round(target_total - total_cad, 2),
        "warnings": warnings,
    }


def print_target_progress(progress):
    """Print the target progress in a readable format."""
    print()
    print("=" * 80)
    print("  PROGRESS TO $5,000 TARGET")
    print(f"  Portfolio: ${progress['total_cad']:,.2f} CAD  |  "
          f"Gap to $5K: ${progress['gap_to_target_cad']:,.2f}")
    print("=" * 80)

    print(f"\n  {'Bucket':<30} {'Now':>8} {'Target':>8} {'Diff':>8} "
          f"{'$ Now':>10} {'$ Gap':>10}")
    print("-" * 80)

    for b in progress["buckets"]:
        diff_pct = round(b["current_pct"] - b["target_pct"], 1)
        sign = "+" if diff_pct >= 0 else ""
        arrow = ">>>" if diff_pct < -10 else ">>" if diff_pct < -5 else "" if diff_pct >= 0 else ">"

        print(
            f"  {b['label']:<30} {b['current_pct']:>7.1f}% {b['target_pct']:>7.0f}% "
            f"{sign}{diff_pct:>7.1f}% "
            f"${b['current_cad']:>9.2f} "
            f"${b['gap_cad']:>9.2f} {arrow}"
        )

    print("-" * 80)
    print(f"  Theme exposure (AI/power/nuclear): {progress['theme_exposure_pct']}%")
    print(f"  Diversified (XEQT core):           {progress['diversified_pct']}%")

    if progress["warnings"]:
        print()
        for w in progress["warnings"]:
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
    progress = calc_target_progress(snapshot)
    print_target_progress(progress)

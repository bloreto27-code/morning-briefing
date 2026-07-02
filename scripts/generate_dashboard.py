import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/Toronto")
def now_et(): return datetime.now(ET)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
DASHBOARD_DIR = os.path.join(REPO_ROOT, "docs")


def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), "r") as f:
        return json.load(f)


def generate_dashboard_data(
    snapshot, progress, cap_data, focus_buys, verdict_lines,
    news_items, thesis_flags, changes, prices, tfsa_data
):
    """Bundle all briefing data into a single JSON for the dashboard."""
    plan = load_json("plan.json")

    positions_list = []
    for p in snapshot["positions"]:
        if "error" in p:
            continue
        positions_list.append({
            "ticker": p["ticker"],
            "shares": p["shares"],
            "avg_cost": p["avg_cost"],
            "price": p["live_price"],
            "currency": p["currency"],
            "value_cad": p["value_cad"],
            "cost_cad": p["cost_cad"],
            "gain_cad": p["gain_cad"],
            "gain_pct": p["gain_pct"],
            "weight_pct": p.get("weight_pct", 0),
            "day_change": p["day_change"],
            "day_pct": p["day_pct"],
            "account": p["account"],
            "status": p["status"],
        })

    focus_list = []
    for fb in focus_buys:
        if "error" in fb:
            continue
        focus_list.append({
            "rank": fb["rank"],
            "ticker": fb["ticker"],
            "price": fb["live_price"],
            "currency": fb["currency"],
            "day_pct": fb["day_pct"],
            "zone_status": fb["zone_status"],
            "zone_reason": fb["zone_reason"],
            "score": fb["score"],
            "cap_pct": fb["cap_pct"],
            "room_cad": fb["room_cad"],
            "buyable": fb["buyable"],
            "buyable_note": fb.get("buyable_note", ""),
        })

    cap_list = []
    for c in cap_data["positions"]:
        cap_list.append({
            "ticker": c["ticker"],
            "weight_pct": c["weight_pct"],
            "cap_pct": c["cap_pct"],
            "room_cad": c["room_cad"],
            "status": c["status"],
            "value_cad": c["value_cad"],
        })

    price_board = []
    for ticker in sorted(prices.keys()):
        data = prices[ticker]
        if "error" in data:
            continue
        price_board.append({
            "ticker": ticker,
            "price": data["price"],
            "change": data["change"],
            "pct_change": data["pct_change"],
            "currency": data["currency"],
        })

    ticker_details = {}
    buy_zones = {bz["ticker"]: bz for bz in plan.get("buy_zones", [])}
    watchlist = load_json("watchlist.json")
    tier2_map = {t["ticker"]: t for t in watchlist["tier2"]["tickers"]}

    all_detail_tickers = set()
    all_detail_tickers.update(watchlist["held"])
    all_detail_tickers.update(tier2_map.keys())
    all_detail_tickers.update(watchlist["tier3"]["tickers"])
    all_detail_tickers.update(watchlist["tier4"]["tickers"])
    for etf in watchlist["etfs"]["tickers"]:
        all_detail_tickers.add(etf["ticker"])

    for ticker in all_detail_tickers:
        bz = buy_zones.get(ticker, {})
        t2 = tier2_map.get(ticker, {})

        cap_info = next((c for c in cap_list if c["ticker"] == ticker), None)
        fb_info = next((f for f in focus_list if f["ticker"] == ticker), None)
        pos_info = next((p for p in positions_list if p["ticker"] == ticker), None)
        price_info = next((pb for pb in price_board if pb["ticker"] == ticker), None)

        def fmt_zone(val):
            if val is None:
                return None
            if isinstance(val, list):
                return f"${val[0]}--${val[1]}"
            if isinstance(val, str):
                return val
            return f"${val}"

        ticker_news = [n for n in news_items if n.get("ticker") == ticker]
        ticker_thesis_flags = [tf for tf in thesis_flags if tf.get("ticker") == ticker]

        detail = {
            "ticker": ticker,
            "role": bz.get("role") or t2.get("role", ""),
            "score": bz.get("score") or t2.get("score"),
            "ref_price": bz.get("ref_price"),
            "starter": fmt_zone(bz.get("starter")),
            "preferred": fmt_zone(bz.get("preferred")),
            "aggressive": fmt_zone(bz.get("aggressive")),
            "no_chase": fmt_zone(bz.get("no_chase")),
            "thesis_break": bz.get("thesis_break", ""),
            "monitoring_flags": bz.get("monitoring_flags", []),
            "cap_pct": (cap_info or {}).get("cap_pct") or bz.get("cap_pct") or t2.get("cap_pct"),
            "weight_pct": (cap_info or {}).get("weight_pct"),
            "room_cad": (cap_info or {}).get("room_cad"),
            "cap_status": (cap_info or {}).get("status"),
            "zone_status": (fb_info or {}).get("zone_status"),
            "zone_reason": (fb_info or {}).get("zone_reason"),
            "price": (price_info or {}).get("price"),
            "currency": (price_info or {}).get("currency"),
            "day_change": (price_info or {}).get("change"),
            "day_pct": (price_info or {}).get("pct_change"),
            "held": pos_info is not None,
            "shares": (pos_info or {}).get("shares"),
            "avg_cost": (pos_info or {}).get("avg_cost"),
            "cost_cad": (pos_info or {}).get("cost_cad"),
            "account": (pos_info or {}).get("account", ""),
            "value_cad": (pos_info or {}).get("value_cad"),
            "gain_cad": (pos_info or {}).get("gain_cad"),
            "gain_pct": (pos_info or {}).get("gain_pct"),
            "status": (pos_info or {}).get("status", ""),
            "news": ticker_news[:10],
            "thesis_flags": ticker_thesis_flags,
        }
        ticker_details[ticker] = detail

    weekly_deposit = (
        (tfsa_data["deposit_cadence"]["biweekly_range"][0] / 2)
        + tfsa_data["deposit_cadence"]["weekly_extra"]
    )
    gap_to_5k = tfsa_data["milestones"]["next_target_cad"] - tfsa_data["milestones"]["current_total_cad"]
    weeks_to_5k = int(gap_to_5k / weekly_deposit) if weekly_deposit > 0 else 0

    dashboard = {
        "generated_at": now_et().strftime("%Y-%m-%d %I:%M %p ET"),
        "date": now_et().strftime("%Y-%m-%d"),
        "verdict": verdict_lines,
        "portfolio": {
            "total_cad": snapshot["total_portfolio_cad"],
            "total_cost_cad": snapshot["total_cost_cad"],
            "total_gain_cad": snapshot["total_gain_cad"],
            "total_gain_pct": snapshot["total_gain_pct"],
            "cash_cad": snapshot["cash_cad"],
            "fx_rate": snapshot["fx_rate"],
            "positions": positions_list,
            "accounts": snapshot["accounts"],
        },
        "progress": {
            "buckets": progress["buckets"],
            "theme_exposure_pct": progress["theme_exposure_pct"],
            "diversified_pct": progress["diversified_pct"],
            "total_cad": progress["total_cad"],
            "target_total_cad": progress["target_total_cad"],
            "gap_to_target_cad": progress["gap_to_target_cad"],
            "warnings": progress["warnings"],
        },
        "caps": {
            "positions": cap_list,
            "breaches": cap_data["breaches"],
            "warnings": cap_data["warnings"],
        },
        "focus_buys": focus_list,
        "news": news_items[:25],
        "thesis_flags": thesis_flags,
        "what_changed": changes,
        "price_board": price_board,
        "ticker_details": ticker_details,
        "tfsa": {
            "annual_limit": tfsa_data["tfsa_annual_limit"],
            "contributed": tfsa_data["contributions_this_year_cad"],
            "remaining_room": tfsa_data["remaining_room_cad"],
            "current_total": tfsa_data["milestones"]["current_total_cad"],
            "target": tfsa_data["milestones"]["next_target_cad"],
            "gap_to_target": round(gap_to_5k, 2),
            "est_weekly_deposit": round(weekly_deposit, 2),
            "est_weeks_to_target": weeks_to_5k,
        },
    }

    output_path = os.path.join(DASHBOARD_DIR, "data.json")
    with open(output_path, "w") as f:
        json.dump(dashboard, f, indent=2)

    return output_path


if __name__ == "__main__":
    from fetch_prices import fetch_prices, fetch_fx_rate, get_all_tickers
    from portfolio import build_snapshot
    from targets import calc_target_progress
    from caps import check_caps
    from verdict import evaluate_focus_buys, generate_verdict
    from news import fetch_news, check_thesis_breaks
    from history import load_previous_snapshot, calc_what_changed, save_daily_snapshot

    print("Generating dashboard data...")
    tickers = get_all_tickers()
    fx_rate = fetch_fx_rate()
    prices = fetch_prices(tickers)

    snapshot = build_snapshot(prices, fx_rate)
    progress = calc_target_progress(snapshot)
    cap_data = check_caps(snapshot)
    focus_buys = evaluate_focus_buys(prices, snapshot, cap_data)
    verdict_lines = generate_verdict(focus_buys, progress, cap_data, snapshot)

    watchlist = load_json("watchlist.json")
    held = watchlist["held"]
    tier2 = [t["ticker"] for t in watchlist["tier2"]["tickers"]]
    news_items = fetch_news(held + tier2)
    plan = load_json("plan.json")
    thesis_flags = check_thesis_breaks(news_items, plan["buy_zones"])

    prev = load_previous_snapshot()
    changes = calc_what_changed(snapshot, focus_buys, cap_data, prev)
    save_daily_snapshot(snapshot, focus_buys, cap_data, progress)

    tfsa_data = load_json("contributions.json")

    path = generate_dashboard_data(
        snapshot, progress, cap_data, focus_buys, verdict_lines,
        news_items, thesis_flags, changes, prices, tfsa_data
    )
    print(f"  Dashboard data written to: {path}")

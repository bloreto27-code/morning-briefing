import os
import json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")


def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), "r") as f:
        return json.load(f)


def get_zone_status(ticker, live_price, buy_zone):
    """Determine where the live price sits relative to the buy zones.

    Returns a status string and a short reason.
    """
    starter = buy_zone.get("starter")

    if starter == "hold, no add":
        return "HOLD", "Hold position — no new money during build phase"

    if starter == "hold only, no new money":
        return "HOLD", "Legacy hold — no new money"

    if starter == "buy every deposit":
        return "BUY", "Core ETF — buy every deposit"

    no_chase = buy_zone.get("no_chase")
    if no_chase and live_price > no_chase:
        return "NO-CHASE", f"Above no-chase zone (>${no_chase})"

    aggressive = buy_zone.get("aggressive")
    preferred = buy_zone.get("preferred")

    if aggressive and live_price <= aggressive:
        return "BUY", f"Aggressive zone (below ${aggressive})"

    if isinstance(preferred, list) and len(preferred) == 2:
        if preferred[0] <= live_price <= preferred[1]:
            return "BUY", f"Preferred zone (${preferred[0]}–${preferred[1]})"
    elif isinstance(preferred, (int, float)):
        if live_price <= preferred:
            return "BUY", f"Below preferred review price (${preferred})"

    if isinstance(starter, list) and len(starter) == 2:
        if starter[0] <= live_price <= starter[1]:
            return "BUY", f"Starter zone (${starter[0]}–${starter[1]})"
        elif live_price < starter[0]:
            return "BUY", f"Below starter zone (under ${starter[0]})"
        else:
            return "WATCH", f"Above starter zone (>${starter[1]}), below no-chase"
    elif isinstance(starter, (int, float)):
        if live_price <= starter:
            return "BUY", f"At or below starter (${starter})"

    return "WAIT", "Not in a buy zone"


def evaluate_focus_buys(prices, snapshot, cap_data):
    """Evaluate each focus-buy name: zone status, cap room, buyability.

    Returns a list of focus buy evaluations in priority order.
    """
    plan = load_json("plan.json")
    focus_list = plan["focus_buys_priority"]
    buy_zones = {bz["ticker"]: bz for bz in plan["buy_zones"]}

    cap_lookup = {r["ticker"]: r for r in cap_data["positions"]}

    total_cad = snapshot["total_portfolio_cad"]
    fx_rate = snapshot["fx_rate"]

    results = []

    for focus in focus_list:
        ticker = focus["ticker"]
        rank = focus["rank"]
        base_reason = focus["reason"]

        price_data = prices.get(ticker)
        if not price_data or "error" in price_data:
            results.append({
                "rank": rank,
                "ticker": ticker,
                "error": f"No price data for {ticker}",
            })
            continue

        live_price = price_data["price"]
        day_change = price_data["change"]
        day_pct = price_data["pct_change"]
        currency = price_data["currency"]

        bz = buy_zones.get(ticker, {})
        zone_status, zone_reason = get_zone_status(ticker, live_price, bz)

        score = bz.get("score")

        cap_info = cap_lookup.get(ticker)
        if cap_info and cap_info["status"] != "NO CAP":
            cap_pct = cap_info["cap_pct"]
            room_cad = cap_info["room_cad"]
            cap_status = cap_info["status"]
        elif ticker in ("XEQT.TO", "VFV.TO"):
            cap_pct = None
            room_cad = None
            cap_status = "NO CAP"
        else:
            cap_pct = bz.get("cap_pct", 15)
            cap_value = (cap_pct / 100) * total_cad
            owned_cad = 0
            for p in snapshot["positions"]:
                if p.get("ticker") == ticker and "error" not in p:
                    owned_cad = p["value_cad"]
            room_cad = round(cap_value - owned_cad, 2)
            cap_status = "OK"

        buyable = True
        buyable_note = ""

        if zone_status in ("HOLD", "NO-CHASE", "WAIT", "WATCH"):
            buyable = False
            buyable_note = zone_reason

        if cap_status == "BREACH":
            buyable = False
            buyable_note = "Cap breached — do not add"
        elif room_cad is not None and 0 < room_cad < 5:
            buyable = False
            buyable_note = f"Only ${room_cad:.2f} CAD room — too small"

        price_cad = live_price if currency == "CAD" else round(live_price * fx_rate, 2)

        results.append({
            "rank": rank,
            "ticker": ticker,
            "live_price": live_price,
            "currency": currency,
            "price_cad": price_cad,
            "day_change": day_change,
            "day_pct": day_pct,
            "zone_status": zone_status,
            "zone_reason": zone_reason,
            "score": score,
            "cap_pct": cap_pct,
            "room_cad": room_cad,
            "cap_status": cap_status,
            "buyable": buyable,
            "buyable_note": buyable_note,
            "base_reason": base_reason,
        })

    return results


def generate_verdict(focus_buys, progress, cap_data, snapshot):
    """Generate the Today's Verdict — 4-6 blunt sentences.

    Leads with the single best next buy to move toward $5K target.
    """
    plan = load_json("plan.json")
    lines = []

    best_buy = None
    for fb in focus_buys:
        if fb.get("buyable"):
            best_buy = fb
            break

    core_bucket = next((b for b in progress["buckets"] if b["key"] == "xeqt_core"), None)
    core_below_target = core_bucket and core_bucket["current_pct"] < core_bucket["target_pct"]

    if best_buy:
        ticker = best_buy["ticker"]
        price = best_buy["live_price"]
        ccy = best_buy["currency"]
        zone = best_buy["zone_reason"]

        if ticker == "XEQT.TO":
            lines.append(
                f"Buy XEQT.TO at ${price:.2f} {ccy}. "
                f"Core is {core_bucket['current_pct']}% vs 40% target — "
                f"${core_bucket['gap_cad']:,.0f} to go. Fund first, every deposit."
            )
        else:
            lines.append(
                f"Buy {ticker} at ${price:.2f} {ccy}. {zone}. "
                f"Score {best_buy['score']}/100."
            )
            if core_below_target:
                lines.append(
                    f"But fund XEQT.TO first — core is only {core_bucket['current_pct']}% "
                    f"(target 40%)."
                )
    else:
        lines.append(
            "No buys today. No focus name is in a buy zone with cap room."
        )
        if core_below_target:
            lines.append(
                f"XEQT.TO is always a buy — core at {core_bucket['current_pct']}% "
                f"vs 40% target. Fund on next deposit."
            )

    if cap_data["breaches"]:
        breach_names = [b["ticker"] for b in cap_data["breaches"]]
        lines.append(
            f"Cap breach{'es' if len(breach_names) > 1 else ''}: "
            f"{', '.join(breach_names)}. Do not add — shrink by dilution."
        )

    if progress["theme_exposure_pct"] > 50:
        lines.append(
            f"Theme concentration at {progress['theme_exposure_pct']}%. "
            f"Building XEQT core is the fix."
        )

    lines.append(
        f"Portfolio: ${snapshot['total_portfolio_cad']:,.2f} CAD. "
        f"Gap to $5K: ${progress['gap_to_target_cad']:,.2f}."
    )

    skipped = []
    for fb in focus_buys:
        if fb.get("error"):
            continue
        if not fb.get("buyable") and fb["ticker"] != "XEQT.TO":
            reason = fb.get("buyable_note") or fb.get("zone_reason", "")
            if fb["zone_status"] == "NO-CHASE":
                skipped.append(f"{fb['ticker']} above no-chase")
            elif fb["zone_status"] == "WATCH":
                skipped.append(f"{fb['ticker']} above zone")

    if skipped:
        lines.append(f"Skip: {'; '.join(skipped)}.")

    return lines


def print_verdict_and_focus(verdict_lines, focus_buys):
    """Print the verdict and focus buys table."""
    print()
    print("=" * 80)
    print("  TODAY'S VERDICT")
    print("=" * 80)
    for line in verdict_lines:
        print(f"  {line}")
    print("=" * 80)

    print()
    print("=" * 80)
    print("  FOCUS BUYS (priority order)")
    print("=" * 80)
    print(f"  {'#':>2} {'Ticker':<10} {'Price':>9} {'Day':>8} "
          f"{'Zone':>10} {'Score':>6} {'Cap':>5} {'Room$':>8} {'Action'}")
    print("-" * 80)

    for fb in focus_buys:
        if fb.get("error"):
            print(f"  {fb['rank']:>2} {fb['ticker']:<10} {'ERROR':<9}")
            continue

        ccy_sym = "C" if fb["currency"] == "CAD" else "U"
        sign = "+" if fb["day_change"] >= 0 else ""
        score_str = str(fb["score"]) if fb["score"] else "—"
        cap_str = f"{fb['cap_pct']}%" if fb["cap_pct"] else "—"

        if fb["room_cad"] is not None:
            room_str = f"${fb['room_cad']:,.0f}"
        else:
            room_str = "—"

        if fb["buyable"]:
            action = f">>> {fb['zone_reason']}"
        elif fb["zone_status"] == "HOLD":
            action = "HOLD — no new money"
        elif fb["cap_status"] == "BREACH":
            action = "BREACH — do not add"
        else:
            action = fb.get("buyable_note") or fb["zone_reason"]

        print(
            f"  {fb['rank']:>2} {fb['ticker']:<10} "
            f"{fb['live_price']:>8.2f}{ccy_sym} "
            f"{sign}{fb['day_pct']:>6.1f}% "
            f"{fb['zone_status']:>10} "
            f"{score_str:>6} "
            f"{cap_str:>5} "
            f"{room_str:>8}  "
            f"{action}"
        )

    print("=" * 80)


if __name__ == "__main__":
    from fetch_prices import fetch_prices, fetch_fx_rate, get_all_tickers
    from portfolio import build_snapshot
    from targets import calc_target_progress
    from caps import check_caps

    print("Fetching prices...")
    tickers = get_all_tickers()
    fx_rate = fetch_fx_rate()
    prices = fetch_prices(tickers)

    snapshot = build_snapshot(prices, fx_rate)
    progress = calc_target_progress(snapshot)
    cap_data = check_caps(snapshot)

    focus_buys = evaluate_focus_buys(prices, snapshot, cap_data)
    verdict_lines = generate_verdict(focus_buys, progress, cap_data, snapshot)
    print_verdict_and_focus(verdict_lines, focus_buys)

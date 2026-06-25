import os
import json
from datetime import datetime, timedelta, timezone

import yfinance as yf

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")


def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), "r") as f:
        return json.load(f)


def fetch_news(tickers, hours=168):
    """Fetch recent news for a list of tickers using yfinance.

    Returns a list of news items tagged with the ticker they came from,
    filtered to the last `hours` hours (default 7 days), deduplicated by title.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    all_news = []
    seen_titles = set()

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            items = t.news or []
            for item in items:
                content = item.get("content", item)

                title = content.get("title", "")
                if not title or title in seen_titles:
                    continue

                pub_str = content.get("pubDate") or content.get("displayTime", "")
                pub_dt = None
                if pub_str:
                    try:
                        pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                        if pub_dt < cutoff:
                            continue
                    except ValueError:
                        pass
                else:
                    pub_ts = item.get("providerPublishTime", 0)
                    if pub_ts:
                        pub_dt = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
                        if pub_dt < cutoff:
                            continue

                provider = content.get("provider", {})
                publisher = provider.get("displayName", "") if isinstance(provider, dict) else str(provider)

                click_url = content.get("clickThroughUrl", {})
                link = click_url.get("url", "") if isinstance(click_url, dict) else ""
                if not link:
                    canon = content.get("canonicalUrl", {})
                    link = canon.get("url", "") if isinstance(canon, dict) else ""

                seen_titles.add(title)
                all_news.append({
                    "ticker": ticker,
                    "title": title,
                    "publisher": publisher,
                    "link": link,
                    "published": pub_dt.strftime("%Y-%m-%d %H:%M") if pub_dt else "unknown",
                    "type": content.get("contentType", ""),
                })
        except Exception:
            continue

    all_news.sort(key=lambda x: x["published"], reverse=True)
    return all_news


def check_thesis_breaks(news_items, plan_buy_zones):
    """Scan news titles for keywords that match thesis-break triggers.

    Returns a list of flagged items with the matching trigger.
    """
    flags = []

    trigger_keywords = {}
    for bz in plan_buy_zones:
        ticker = bz["ticker"]
        trigger_text = bz.get("thesis_break", "")
        if not trigger_text:
            continue

        keywords = []
        for phrase in trigger_text.lower().replace(",", ";").split(";"):
            phrase = phrase.strip()
            if len(phrase) > 3:
                keywords.append(phrase)
        trigger_keywords[ticker] = {
            "keywords": keywords,
            "full_trigger": trigger_text,
        }

    monitoring_flags = {}
    for bz in plan_buy_zones:
        ticker = bz["ticker"]
        for flag in bz.get("monitoring_flags", []):
            monitoring_flags.setdefault(ticker, []).append(flag.lower())

    for item in news_items:
        ticker = item["ticker"]
        title_lower = item["title"].lower()

        if ticker in trigger_keywords:
            for kw in trigger_keywords[ticker]["keywords"]:
                if kw in title_lower:
                    flags.append({
                        "ticker": ticker,
                        "title": item["title"],
                        "matched_keyword": kw,
                        "thesis_break_trigger": trigger_keywords[ticker]["full_trigger"],
                        "published": item["published"],
                    })
                    break

        if ticker in monitoring_flags:
            for mf in monitoring_flags[ticker]:
                if any(word in title_lower for word in mf.split()[:3]):
                    flags.append({
                        "ticker": ticker,
                        "title": item["title"],
                        "matched_keyword": f"monitoring: {mf[:50]}",
                        "thesis_break_trigger": "Active monitoring flag",
                        "published": item["published"],
                    })
                    break

    return flags


def print_news(news_items, thesis_flags):
    """Print news and thesis-break flags."""
    print()
    print("=" * 80)
    print("  NEWS & CATALYST FLAGS (last 48h)")
    print("=" * 80)

    if not news_items:
        print("  No recent news found.")
    else:
        for item in news_items[:20]:
            title = item['title'][:65].encode('ascii', 'replace').decode('ascii')
            publisher = item['publisher'].encode('ascii', 'replace').decode('ascii')
            print(f"  [{item['ticker']:<8}] {title}")
            print(f"           {publisher} -- {item['published']}")

    if thesis_flags:
        print()
        print("-" * 80)
        print("  *** THESIS-BREAK WATCH ***")
        for tf in thesis_flags:
            title = tf['title'][:60].encode('ascii', 'replace').decode('ascii')
            print(f"  {tf['ticker']}: \"{title}\"")
            print(f"    Matched: {tf['matched_keyword']}")
            print(f"    Trigger: {tf['thesis_break_trigger']}")

    print("=" * 80)


if __name__ == "__main__":
    plan = load_json("plan.json")
    watchlist = load_json("watchlist.json")

    held = watchlist["held"]
    tier2 = [t["ticker"] for t in watchlist["tier2"]["tickers"]]
    priority_tickers = held + tier2

    print(f"Fetching news for {len(priority_tickers)} priority tickers...")
    news_items = fetch_news(priority_tickers)
    print(f"  Found {len(news_items)} articles\n")

    thesis_flags = check_thesis_breaks(news_items, plan["buy_zones"])
    print_news(news_items, thesis_flags)

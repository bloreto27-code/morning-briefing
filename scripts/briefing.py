import json
import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/Toronto")
def now_et(): return datetime.now(ET)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_prices import fetch_prices, fetch_fx_rate, get_all_tickers
from portfolio import build_snapshot
from targets import calc_target_progress
from caps import check_caps
from verdict import evaluate_focus_buys, generate_verdict
from news import fetch_news, check_thesis_breaks
from history import load_previous_snapshot, calc_what_changed, save_daily_snapshot
from generate_dashboard import generate_dashboard_data, load_json


def colorize_tickers(text, tickers):
    """Wrap ticker symbols in gold bold HTML spans for email rendering."""
    for ticker in sorted(tickers, key=len, reverse=True):
        pattern = r'\b' + re.escape(ticker) + r'\b'
        span = f'<span style="color:#F5A623;font-weight:bold;">{ticker}</span>'
        text = re.sub(pattern, span, text)
    return text


def build_email_html(
    verdict_lines, progress, snapshot, cap_data, focus_buys,
    news_items, thesis_flags, changes, prices, tfsa_data
):
    """Generate a self-contained HTML email of the morning briefing."""
    date_str = now_et().strftime("%A, %B %d, %Y")
    fx = snapshot["fx_rate"]

    # Build ticker list for gold colorization in plain-text sections
    all_tickers = list({
        pos["ticker"] for pos in snapshot.get("positions", []) if "error" not in pos
    } | {
        fb["ticker"] for fb in focus_buys if "error" not in fb
    })

    s = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
                max-width:700px;margin:0 auto;background:#0d1117;color:#e6edf3;padding:20px;
                border-radius:8px;">

    <h1 style="color:#58a6ff;font-size:1.3rem;margin-bottom:2px;">Morning Briefing</h1>
    <div style="color:#8b949e;font-size:0.8rem;margin-bottom:16px;">{date_str} &nbsp;|&nbsp; USD/CAD: {fx}</div>
    """

    # Verdict
    s += '<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">'
    s += '<div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">TODAY\'S VERDICT</div>'
    for line in verdict_lines:
        s += f'<div style="margin-bottom:5px;font-size:0.88rem;color:#e0e0e0;">{colorize_tickers(line, all_tickers)}</div>'
    s += '</div>'

    # Stats
    p = snapshot
    gain_color = "#3fb950" if p["total_gain_cad"] >= 0 else "#f85149"
    sgn = "+" if p["total_gain_cad"] >= 0 else ""
    s += f"""
    <table style="width:100%;border-collapse:collapse;margin-bottom:14px;font-size:0.85rem;">
    <tr>
      <td style="text-align:center;padding:10px;background:#161b22;border:1px solid #30363d;border-radius:6px;">
        <div style="font-size:1.3rem;font-weight:700;">${p["total_portfolio_cad"]:,.2f}</div>
        <div style="color:#8b949e;font-size:0.7rem;text-transform:uppercase;">Portfolio CAD</div></td>
      <td style="text-align:center;padding:10px;background:#161b22;border:1px solid #30363d;border-radius:6px;">
        <div style="font-size:1.3rem;font-weight:700;color:{gain_color};">{sgn}${abs(p["total_gain_cad"]):,.2f}</div>
        <div style="color:#8b949e;font-size:0.7rem;text-transform:uppercase;">Gain ({sgn}{p["total_gain_pct"]:.1f}%)</div></td>
      <td style="text-align:center;padding:10px;background:#161b22;border:1px solid #30363d;border-radius:6px;">
        <div style="font-size:1.3rem;font-weight:700;">${progress["gap_to_target_cad"]:,.2f}</div>
        <div style="color:#8b949e;font-size:0.7rem;text-transform:uppercase;">Gap to $5K</div></td>
    </tr></table>
    """

    # Progress
    s += '<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">'
    s += '<div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">PROGRESS TO TARGET</div>'
    for b in progress["buckets"]:
        pct = min(b["current_pct"], 100)
        bar_color = "#f85149" if b["current_pct"] < b["target_pct"] - 10 else "#d29922" if b["current_pct"] < b["target_pct"] else "#3fb950"
        s += f"""
        <div style="margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:2px;">
            <span>{b["label"]}</span><span>{b["current_pct"]:.1f}% / {b["target_pct"]}%</span></div>
          <div style="background:#30363d;border-radius:4px;height:16px;position:relative;">
            <div style="background:{bar_color};height:100%;border-radius:4px;width:{pct}%;"></div>
          </div>
          <div style="font-size:0.72rem;color:#8b949e;">Now: ${b["current_cad"]:,.2f} &nbsp;|&nbsp; Gap: ${b["gap_cad"]:,.2f}</div>
        </div>"""
    if progress["warnings"]:
        for w in progress["warnings"]:
            s += f'<div style="color:#d29922;font-size:0.8rem;margin-top:4px;">&#9888; {colorize_tickers(w, all_tickers)}</div>'
    s += '</div>'

    # What Changed
    s += '<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">'
    s += '<div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">WHAT CHANGED</div>'
    for c in changes:
        s += f'<div style="font-size:0.82rem;margin-bottom:4px;color:#e0e0e0;">{colorize_tickers(c, all_tickers)}</div>'
    s += '</div>'

    # Portfolio
    s += '<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">'
    s += '<div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">PORTFOLIO</div>'
    s += '<table style="width:100%;border-collapse:collapse;font-size:0.78rem;">'
    s += '<tr style="color:#8b949e;"><th style="text-align:left;padding:4px;">Ticker</th><th style="text-align:right;padding:4px;">Price</th><th style="text-align:right;padding:4px;">Day</th><th style="text-align:right;padding:4px;">CAD Val</th><th style="text-align:right;padding:4px;">Gain</th><th style="text-align:right;padding:4px;">Wt%</th></tr>'
    for pos in sorted(snapshot["positions"], key=lambda x: x.get("value_cad", 0), reverse=True):
        if "error" in pos:
            continue
        ccy = "C" if pos["currency"] == "CAD" else "U"
        gc = "#3fb950" if pos["gain_cad"] >= 0 else "#f85149"
        dc = "#3fb950" if pos["day_pct"] >= 0 else "#f85149"
        dsgn = "+" if pos["day_pct"] >= 0 else ""
        gsgn = "+" if pos["gain_pct"] >= 0 else ""
        s += f'<tr style="border-bottom:1px solid #30363d;"><td style="padding:4px;font-weight:700;color:#F5A623;">{pos["ticker"]}</td><td style="text-align:right;padding:4px;">{pos["live_price"]:.2f}{ccy}</td><td style="text-align:right;padding:4px;color:{dc};">{dsgn}{pos["day_pct"]:.1f}%</td><td style="text-align:right;padding:4px;">${pos["value_cad"]:,.2f}</td><td style="text-align:right;padding:4px;color:{gc};">{gsgn}{pos["gain_pct"]:.1f}%</td><td style="text-align:right;padding:4px;">{pos.get("weight_pct",0):.1f}%</td></tr>'
    s += '</table></div>'

    # Cap Status
    s += '<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">'
    s += '<div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">CAP STATUS</div>'
    if cap_data["breaches"]:
        for b in cap_data["breaches"]:
            s += f'<div style="color:#f85149;font-size:0.82rem;margin-bottom:4px;">&#128308; <strong style="color:#F5A623;">{b["ticker"]}</strong>: {b["weight_pct"]:.1f}% vs {b["cap_pct"]}% cap &mdash; over by {b["over_by_pct"]}pp. Do not add.</div>'
    s += '<table style="width:100%;border-collapse:collapse;font-size:0.78rem;">'
    s += '<tr style="color:#8b949e;"><th style="text-align:left;padding:4px;">Ticker</th><th style="text-align:right;padding:4px;">Wt%</th><th style="text-align:right;padding:4px;">Cap%</th><th style="text-align:right;padding:4px;">Room</th><th style="text-align:left;padding:4px;">Status</th></tr>'
    for c in cap_data["positions"]:
        status_color = "#f85149" if c["status"] == "BREACH" else "#d29922" if c["status"] == "NEAR CAP" else "#8b949e"
        room_str = f'${c["room_cad"]:,.2f}' if c["room_cad"] is not None else "--"
        cap_str = f'{c["cap_pct"]}%' if c["cap_pct"] else "--"
        s += f'<tr style="border-bottom:1px solid #30363d;"><td style="padding:4px;font-weight:700;color:#F5A623;">{c["ticker"]}</td><td style="text-align:right;padding:4px;">{c["weight_pct"]:.1f}%</td><td style="text-align:right;padding:4px;">{cap_str}</td><td style="text-align:right;padding:4px;">{room_str}</td><td style="padding:4px;color:{status_color};">{c["status"]}</td></tr>'
    s += '</table></div>'

    # Focus Buys
    s += '<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">'
    s += '<div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">FOCUS BUYS</div>'
    s += '<table style="width:100%;border-collapse:collapse;font-size:0.78rem;">'
    s += '<tr style="color:#8b949e;"><th style="text-align:left;padding:4px;">#</th><th style="text-align:left;padding:4px;">Ticker</th><th style="text-align:right;padding:4px;">Price</th><th style="text-align:right;padding:4px;">Day</th><th style="text-align:left;padding:4px;">Zone</th><th style="text-align:right;padding:4px;">Score</th></tr>'
    for fb in focus_buys:
        if "error" in fb:
            continue
        ccy = "C" if fb["currency"] == "CAD" else "U"
        dc = "#3fb950" if fb["day_pct"] >= 0 else "#f85149"
        dsgn = "+" if fb["day_pct"] >= 0 else ""
        zone_color = "#3fb950" if fb["zone_status"] == "BUY" else "#d29922" if fb["zone_status"] == "WATCH" else "#8b949e"
        score_str = str(fb["score"]) if fb["score"] else "--"
        s += f'<tr style="border-bottom:1px solid #30363d;"><td style="padding:4px;">{fb["rank"]}</td><td style="padding:4px;font-weight:700;color:#F5A623;">{fb["ticker"]}</td><td style="text-align:right;padding:4px;">{fb["live_price"]:.2f}{ccy}</td><td style="text-align:right;padding:4px;color:{dc};">{dsgn}{fb["day_pct"]:.1f}%</td><td style="padding:4px;color:{zone_color};">{fb["zone_status"]}</td><td style="text-align:right;padding:4px;">{score_str}</td></tr>'
    s += '</table></div>'

    # Thesis flags
    if thesis_flags:
        s += '<div style="background:#161b22;border:1px solid #f85149;border-radius:8px;padding:14px;margin-bottom:14px;">'
        s += '<div style="color:#f85149;font-weight:600;margin-bottom:8px;font-size:0.9rem;">THESIS-BREAK WATCH</div>'
        for tf in thesis_flags:
            title = tf["title"][:80]
            s += f'<div style="font-size:0.82rem;margin-bottom:6px;"><strong style="color:#F5A623;">{tf["ticker"]}:</strong> &ldquo;{title}&rdquo;<br><span style="color:#8b949e;">Matched: {tf["matched_keyword"]}</span></div>'
        s += '</div>'

    # News
    s += '<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">'
    s += '<div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">NEWS &amp; CATALYSTS</div>'
    for n in news_items[:15]:
        title = n["title"][:80]
        link = n.get("link", "")
        title_html = f'<a href="{link}" style="color:#e6edf3;text-decoration:none;border-bottom:1px dotted #8b949e;">{title}</a>' if link else title
        s += f'<div style="font-size:0.75rem;padding:3px 0;border-bottom:1px solid #30363d;"><span style="color:#F5A623;font-weight:700;">{n["ticker"]}</span> {title_html} <span style="color:#8b949e;font-size:0.68rem;">&mdash; {n["published"]}</span></div>'
    s += '</div>'

    # TFSA
    tfsa = load_json("contributions.json")
    weekly = (tfsa["deposit_cadence"]["biweekly_range"][0] / 2) + tfsa["deposit_cadence"]["weekly_extra"]
    gap_5k = tfsa["milestones"]["next_target_cad"] - tfsa["milestones"]["current_total_cad"]
    weeks = int(gap_5k / weekly) if weekly > 0 else 0
    s += f"""
    <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">
    <div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">TFSA ROOM</div>
    <div style="font-size:0.82rem;">Contributed: ${tfsa["contributions_this_year_cad"]:,.2f} &nbsp;|&nbsp; Remaining: ${tfsa["remaining_room_cad"]:,.2f} &nbsp;|&nbsp; Limit: ${tfsa["tfsa_annual_limit"]:,}</div>
    <div style="font-size:0.82rem;">Est. ~{weeks} weeks to $5K at current cadence.</div>
    </div>"""

    s += '<div style="text-align:center;color:#8b949e;font-size:0.7rem;margin-top:10px;">Generated by Morning Briefing System &bull; Prices may lag. Broker app is final word.</div>'
    s += '</div>'
    return s


SENDGRID_TO = "bloreto27@adrian.edu"
SENDGRID_FROM = "bloreto27@adrian.edu"


def send_email(html_body, subject=None):
    """Send the briefing email via SendGrid."""
    api_key = os.environ.get("SENDGRID_API_KEY")
    to_email = SENDGRID_TO
    from_email = SENDGRID_FROM

    if not api_key:
        print("  SENDGRID_API_KEY not set — skipping email.")
        return False

    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    if not subject:
        subject = f"Morning Briefing — {now_et().strftime('%B %d, %Y')}"

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=html_body,
    )

    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(f"  Email sent! Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"  Email failed: {e}")
        return False


def build_sms_body(verdict_lines, snapshot, focus_buys, cap_data, thesis_flags):
    """Build a condensed text message version of the briefing."""
    date_str = now_et().strftime("%b %d")
    lines = [f"BRIEFING {date_str}"]

    for v in verdict_lines:
        lines.append(v)

    lines.append("")
    lines.append("FOCUS BUYS:")
    for fb in focus_buys:
        if "error" in fb:
            continue
        ccy = "C" if fb["currency"] == "CAD" else "U"
        sgn = "+" if fb["day_pct"] >= 0 else ""
        lines.append(
            f" {fb['rank']}. {fb['ticker']} ${fb['live_price']:.2f}{ccy} "
            f"({sgn}{fb['day_pct']:.1f}%) {fb['zone_status']}"
        )

    if thesis_flags:
        lines.append("")
        lines.append("THESIS ALERT:")
        for tf in thesis_flags:
            lines.append(f" {tf['ticker']}: {tf['title'][:60]}")

    lines.append("")
    lines.append("Prices may lag. Broker app is final word.")

    return "\n".join(lines)


def build_midday_sms_body(snapshot, focus_buys, thesis_flags):
    """Condensed midday text: portfolio value + any focus buy in zone."""
    date_str = now_et().strftime("%b %d")
    p = snapshot
    sgn = "+" if p["total_gain_cad"] >= 0 else ""
    lines = [
        f"MIDDAY {date_str}",
        f"Portfolio: ${p['total_portfolio_cad']:,.2f} CAD ({sgn}{p['total_gain_pct']:.1f}%)",
    ]

    buys_in_zone = [fb for fb in focus_buys if fb.get("zone_status") == "BUY" and "error" not in fb]
    if buys_in_zone:
        lines.append("")
        lines.append("IN BUY ZONE NOW:")
        for fb in buys_in_zone[:3]:
            ccy = "C" if fb["currency"] == "CAD" else "U"
            lines.append(f" {fb['ticker']} ${fb['live_price']:.2f}{ccy}")
    else:
        lines.append("No focus buys in zone right now.")

    if thesis_flags:
        lines.append("")
        lines.append("THESIS ALERT:")
        for tf in thesis_flags[:2]:
            lines.append(f" {tf['ticker']}: {tf['title'][:60]}")

    return "\n".join(lines)


def build_close_sms_body(snapshot, focus_buys, thesis_flags):
    """Condensed market-close text: day change + tomorrow's game plan."""
    date_str = now_et().strftime("%b %d")
    p = snapshot
    fx = p["fx_rate"]
    positions = [pos for pos in p["positions"] if "error" not in pos]
    day_change_cad = sum(
        pos.get("day_change", 0) * pos.get("shares", 0) * (1 if pos["currency"] == "CAD" else fx)
        for pos in positions
    )
    day_sgn = "+" if day_change_cad >= 0 else ""
    sgn = "+" if p["total_gain_cad"] >= 0 else ""
    lines = [
        f"CLOSE {date_str}",
        f"Portfolio: ${p['total_portfolio_cad']:,.2f} CAD",
        f"Today: {day_sgn}${abs(day_change_cad):,.2f}  |  Total: {sgn}{p['total_gain_pct']:.1f}%",
    ]

    in_zone = [fb for fb in focus_buys if fb.get("zone_status") == "BUY" and "error" not in fb]
    near_zone = [fb for fb in focus_buys if fb.get("zone_status") in ("WATCH", "WAIT") and "error" not in fb]
    lines.append("")
    if in_zone:
        fb0 = in_zone[0]
        lines.append(f"Plan: {fb0['ticker']} closed in buy zone at ${fb0['live_price']:.2f}.")
    elif near_zone:
        fb0 = near_zone[0]
        lines.append(f"Plan: {fb0['ticker']} approaching zone, alert at {fb0.get('starter', '—')}.")
    else:
        lines.append("Plan: No focus buys in zone. Fund XEQT.TO next deposit.")

    if thesis_flags:
        lines.append("")
        lines.append("THESIS FLAGS TODAY:")
        for tf in thesis_flags[:2]:
            lines.append(f" {tf['ticker']}: {tf['title'][:60]}")

    return "\n".join(lines)


def send_sms(body):
    """Send the briefing SMS via Twilio."""
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_FROM_NUMBER")
    to_number = os.environ.get("TWILIO_TO_NUMBER")

    if not account_sid or not auth_token:
        print("  TWILIO credentials not set — skipping SMS.")
        return False
    if not from_number or not to_number:
        print("  TWILIO phone numbers not set — skipping SMS.")
        return False

    from twilio.rest import Client

    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number,
        )
        print(f"  SMS sent! SID: {message.sid}")
        return True
    except Exception as e:
        print(f"  SMS failed: {e}")
        return False


def get_briefing_type():
    """Detect morning / midday / close from current Toronto hour, or BRIEFING_TYPE env var."""
    t = os.environ.get("BRIEFING_TYPE", "").lower().strip()
    if t in ("morning", "midday", "close"):
        return t
    h = now_et().hour
    if h <= 10:
        return "morning"
    elif h <= 14:
        return "midday"
    else:
        return "close"


def build_midday_email_html(snapshot, focus_buys, thesis_flags):
    date_str = now_et().strftime("%A, %B %d, %Y")
    time_str = now_et().strftime("%I:%M %p ET")
    fx = snapshot["fx_rate"]
    p = snapshot
    gain_color = "#3fb950" if p["total_gain_cad"] >= 0 else "#f85149"
    sgn = "+" if p["total_gain_cad"] >= 0 else ""

    positions = [pos for pos in p["positions"] if "error" not in pos]
    by_day = sorted(positions, key=lambda x: x.get("day_pct", 0), reverse=True)
    buys_in_zone = [fb for fb in focus_buys if fb.get("zone_status") == "BUY" and "error" not in fb]

    s = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
max-width:700px;margin:0 auto;background:#0d1117;color:#e6edf3;padding:20px;border-radius:8px;">
<h1 style="color:#d29922;font-size:1.3rem;margin-bottom:2px;">Midday Update &#9201;</h1>
<div style="color:#8b949e;font-size:0.8rem;margin-bottom:16px;">{date_str} &nbsp;|&nbsp; {time_str} &nbsp;|&nbsp; USD/CAD: {fx}</div>"""

    s += f"""<table style="width:100%;border-collapse:collapse;margin-bottom:14px;font-size:0.85rem;"><tr>
<td style="text-align:center;padding:10px;background:#161b22;border:1px solid #30363d;border-radius:6px;">
  <div style="font-size:1.3rem;font-weight:700;">${p["total_portfolio_cad"]:,.2f}</div>
  <div style="color:#8b949e;font-size:0.7rem;text-transform:uppercase;">Portfolio CAD</div></td>
<td style="text-align:center;padding:10px;background:#161b22;border:1px solid #30363d;border-radius:6px;">
  <div style="font-size:1.3rem;font-weight:700;color:{gain_color};">{sgn}${abs(p["total_gain_cad"]):,.2f}</div>
  <div style="color:#8b949e;font-size:0.7rem;text-transform:uppercase;">Unrealized P&L ({sgn}{p["total_gain_pct"]:.1f}%)</div></td>
</tr></table>"""

    # Positions sorted by day move
    s += """<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">
<div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">YOUR HOLDINGS RIGHT NOW</div>
<table style="width:100%;border-collapse:collapse;font-size:0.78rem;">
<tr style="color:#8b949e;"><th style="text-align:left;padding:4px;">Ticker</th>
<th style="text-align:right;padding:4px;">Price</th><th style="text-align:right;padding:4px;">Day %</th>
<th style="text-align:right;padding:4px;">Value CAD</th></tr>"""
    for pos in by_day:
        ccy = "C" if pos["currency"] == "CAD" else "U"
        dc = "#3fb950" if pos["day_pct"] >= 0 else "#f85149"
        dsgn = "+" if pos["day_pct"] >= 0 else ""
        s += f'<tr style="border-bottom:1px solid #30363d;"><td style="padding:4px;font-weight:700;color:#F5A623;">{pos["ticker"]}</td><td style="text-align:right;padding:4px;">{pos["live_price"]:.2f}{ccy}</td><td style="text-align:right;padding:4px;color:{dc};">{dsgn}{pos["day_pct"]:.1f}%</td><td style="text-align:right;padding:4px;">${pos["value_cad"]:,.2f}</td></tr>'
    s += "</table></div>"

    # Focus buys
    border = "#3fb950" if buys_in_zone else "#30363d"
    hdr_color = "#3fb950" if buys_in_zone else "#58a6ff"
    hdr_txt = "&#9989; FOCUS BUY IN ZONE NOW" if buys_in_zone else "FOCUS BUYS — MIDDAY PRICES"
    s += f'<div style="background:#161b22;border:1px solid {border};border-radius:8px;padding:14px;margin-bottom:14px;">'
    s += f'<div style="color:{hdr_color};font-weight:600;margin-bottom:8px;font-size:0.9rem;">{hdr_txt}</div>'
    for fb in focus_buys[:4]:
        if "error" in fb:
            continue
        ccy = "C" if fb["currency"] == "CAD" else "U"
        zone_color = "#3fb950" if fb["zone_status"] == "BUY" else "#d29922" if fb["zone_status"] in ("WATCH","WAIT") else "#8b949e"
        dsgn = "+" if fb["day_pct"] >= 0 else ""
        s += f'<div style="font-size:0.83rem;margin-bottom:5px;"><strong style="color:#F5A623;">{fb["ticker"]}</strong> &nbsp; ${fb["live_price"]:.2f}{ccy} &nbsp; <span style="color:{zone_color};">{fb["zone_status"]}</span> &nbsp; <span style="color:#8b949e;">Score {fb["score"] or "—"} &nbsp; {dsgn}{fb["day_pct"]:.1f}% today</span></div>'
    s += "</div>"

    if thesis_flags:
        s += '<div style="background:#161b22;border:1px solid #f85149;border-radius:8px;padding:14px;margin-bottom:14px;">'
        s += '<div style="color:#f85149;font-weight:600;margin-bottom:8px;font-size:0.9rem;">&#9888; THESIS WATCH</div>'
        for tf in thesis_flags[:3]:
            s += f'<div style="font-size:0.82rem;margin-bottom:4px;"><strong style="color:#F5A623;">{tf["ticker"]}</strong>: {tf["title"][:80]}</div>'
        s += "</div>"

    s += '<div style="text-align:center;color:#8b949e;font-size:0.7rem;margin-top:10px;">Market Close update at 4:00 PM ET &bull; Dashboard: bloreto27-code.github.io/morning-briefing</div></div>'
    return s


def build_close_email_html(snapshot, focus_buys, thesis_flags, news_items):
    date_str = now_et().strftime("%A, %B %d, %Y")
    fx = snapshot["fx_rate"]
    p = snapshot
    gain_color = "#3fb950" if p["total_gain_cad"] >= 0 else "#f85149"
    sgn = "+" if p["total_gain_cad"] >= 0 else ""

    positions = [pos for pos in p["positions"] if "error" not in pos]
    by_day = sorted(positions, key=lambda x: x.get("day_pct", 0), reverse=True)
    gainers = [x for x in by_day if x.get("day_pct", 0) > 0]
    losers = [x for x in reversed(by_day) if x.get("day_pct", 0) < 0]

    day_change_cad = sum(
        pos.get("day_change", 0) * pos.get("shares", 0) * (1 if pos["currency"] == "CAD" else fx)
        for pos in positions
    )
    day_color = "#3fb950" if day_change_cad >= 0 else "#f85149"
    day_sgn = "+" if day_change_cad >= 0 else ""

    s = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
max-width:700px;margin:0 auto;background:#0d1117;color:#e6edf3;padding:20px;border-radius:8px;">
<h1 style="color:#58a6ff;font-size:1.3rem;margin-bottom:2px;">Market Close &#128200;</h1>
<div style="color:#8b949e;font-size:0.8rem;margin-bottom:16px;">{date_str} &nbsp;|&nbsp; Markets closed 4:00 PM ET &nbsp;|&nbsp; USD/CAD: {fx}</div>"""

    s += f"""<table style="width:100%;border-collapse:collapse;margin-bottom:14px;font-size:0.85rem;"><tr>
<td style="text-align:center;padding:10px;background:#161b22;border:1px solid #30363d;border-radius:6px;">
  <div style="font-size:1.3rem;font-weight:700;">${p["total_portfolio_cad"]:,.2f}</div>
  <div style="color:#8b949e;font-size:0.7rem;text-transform:uppercase;">Closing Value CAD</div></td>
<td style="text-align:center;padding:10px;background:#161b22;border:1px solid #30363d;border-radius:6px;">
  <div style="font-size:1.3rem;font-weight:700;color:{day_color};">{day_sgn}${abs(day_change_cad):,.2f}</div>
  <div style="color:#8b949e;font-size:0.7rem;text-transform:uppercase;">Today's Change CAD</div></td>
<td style="text-align:center;padding:10px;background:#161b22;border:1px solid #30363d;border-radius:6px;">
  <div style="font-size:1.3rem;font-weight:700;color:{gain_color};">{sgn}${abs(p["total_gain_cad"]):,.2f} ({sgn}{p["total_gain_pct"]:.1f}%)</div>
  <div style="color:#8b949e;font-size:0.7rem;text-transform:uppercase;">Total Unrealized P&L</div></td>
</tr></table>"""

    # Closing prices
    s += """<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">
<div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">CLOSING PRICES</div>
<table style="width:100%;border-collapse:collapse;font-size:0.78rem;">
<tr style="color:#8b949e;"><th style="text-align:left;padding:4px;">Ticker</th>
<th style="text-align:right;padding:4px;">Close</th><th style="text-align:right;padding:4px;">Day</th>
<th style="text-align:right;padding:4px;">Value CAD</th><th style="text-align:right;padding:4px;">Total Gain</th></tr>"""
    for pos in sorted(positions, key=lambda x: x.get("value_cad", 0), reverse=True):
        ccy = "C" if pos["currency"] == "CAD" else "U"
        dc = "#3fb950" if pos["day_pct"] >= 0 else "#f85149"
        gc = "#3fb950" if pos["gain_cad"] >= 0 else "#f85149"
        dsgn = "+" if pos["day_pct"] >= 0 else ""
        gsgn = "+" if pos["gain_pct"] >= 0 else ""
        s += f'<tr style="border-bottom:1px solid #30363d;"><td style="padding:4px;font-weight:700;color:#F5A623;">{pos["ticker"]}</td><td style="text-align:right;padding:4px;">{pos["live_price"]:.2f}{ccy}</td><td style="text-align:right;padding:4px;color:{dc};">{dsgn}{pos["day_pct"]:.1f}%</td><td style="text-align:right;padding:4px;">${pos["value_cad"]:,.2f}</td><td style="text-align:right;padding:4px;color:{gc};">{gsgn}{pos["gain_pct"]:.1f}%</td></tr>'
    s += "</table></div>"

    # Day movers
    if gainers or losers:
        s += '<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">'
        s += '<div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">DAY MOVERS IN YOUR HOLDINGS</div>'
        if gainers:
            s += '<div style="color:#3fb950;font-size:0.75rem;font-weight:700;margin-bottom:4px;text-transform:uppercase;">Gainers</div>'
            for pos in gainers:
                s += f'<div style="font-size:0.82rem;margin-bottom:3px;"><strong style="color:#F5A623;">{pos["ticker"]}</strong> <span style="color:#3fb950;">+{pos["day_pct"]:.1f}%</span> &nbsp; ${pos["live_price"]:.2f}</div>'
        if losers:
            s += '<div style="color:#f85149;font-size:0.75rem;font-weight:700;margin:8px 0 4px;text-transform:uppercase;">Losers</div>'
            for pos in losers:
                s += f'<div style="font-size:0.82rem;margin-bottom:3px;"><strong style="color:#F5A623;">{pos["ticker"]}</strong> <span style="color:#f85149;">{pos["day_pct"]:.1f}%</span> &nbsp; ${pos["live_price"]:.2f}</div>'
        s += "</div>"

    # Focus buys at close
    s += """<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">
<div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">FOCUS BUYS AT CLOSE</div>
<table style="width:100%;border-collapse:collapse;font-size:0.78rem;">
<tr style="color:#8b949e;"><th style="text-align:left;padding:4px;">#</th><th style="text-align:left;padding:4px;">Ticker</th>
<th style="text-align:right;padding:4px;">Close</th><th style="text-align:right;padding:4px;">Day</th>
<th style="text-align:left;padding:4px;">Zone</th><th style="text-align:right;padding:4px;">Score</th></tr>"""
    for fb in focus_buys:
        if "error" in fb:
            continue
        ccy = "C" if fb["currency"] == "CAD" else "U"
        dc = "#3fb950" if fb["day_pct"] >= 0 else "#f85149"
        dsgn = "+" if fb["day_pct"] >= 0 else ""
        zc = "#3fb950" if fb["zone_status"] == "BUY" else "#d29922" if fb["zone_status"] in ("WATCH","WAIT") else "#8b949e"
        s += f'<tr style="border-bottom:1px solid #30363d;"><td style="padding:4px;">{fb["rank"]}</td><td style="padding:4px;font-weight:700;color:#F5A623;">{fb["ticker"]}</td><td style="text-align:right;padding:4px;">{fb["live_price"]:.2f}{ccy}</td><td style="text-align:right;padding:4px;color:{dc};">{dsgn}{fb["day_pct"]:.1f}%</td><td style="padding:4px;color:{zc};">{fb["zone_status"]}</td><td style="text-align:right;padding:4px;">{fb["score"] or "—"}</td></tr>'
    s += "</table></div>"

    if thesis_flags:
        s += '<div style="background:#161b22;border:1px solid #f85149;border-radius:8px;padding:14px;margin-bottom:14px;">'
        s += '<div style="color:#f85149;font-weight:600;margin-bottom:8px;font-size:0.9rem;">&#9888; THESIS FLAGS TODAY</div>'
        for tf in thesis_flags:
            s += f'<div style="font-size:0.82rem;margin-bottom:6px;"><strong style="color:#F5A623;">{tf["ticker"]}</strong>: &ldquo;{tf["title"][:80]}&rdquo;<br><span style="color:#8b949e;">Matched: {tf["matched_keyword"]}</span></div>'
        s += "</div>"

    # Tomorrow's game plan
    in_zone = [fb for fb in focus_buys if fb.get("zone_status") == "BUY" and "error" not in fb]
    near_zone = [fb for fb in focus_buys if fb.get("zone_status") in ("WATCH","WAIT") and "error" not in fb]
    s += """<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">
<div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">TOMORROW'S GAME PLAN</div>"""
    if in_zone:
        fb0 = in_zone[0]
        s += f'<div style="font-size:0.85rem;margin-bottom:6px;color:#3fb950;">&#9989; <strong>{fb0["ticker"]}</strong> closed in buy zone at ${fb0["live_price"]:.2f}. Next deposit: XEQT.TO first, then {fb0["ticker"]}.</div>'
    elif near_zone:
        fb0 = near_zone[0]
        s += f'<div style="font-size:0.85rem;margin-bottom:6px;color:#d29922;">&#9201; <strong>{fb0["ticker"]}</strong> is approaching buy zone. Set a price alert at {fb0.get("starter","—")}.</div>'
    else:
        s += '<div style="font-size:0.85rem;margin-bottom:6px;color:#8b949e;">No focus buys in zone. Fund XEQT.TO on next deposit and hold cash otherwise.</div>'
    s += '<div style="font-size:0.8rem;color:#8b949e;margin-top:4px;">Full morning briefing tomorrow at 7:30 AM ET.</div></div>'

    # Top news
    if news_items:
        s += """<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:14px;">
<div style="color:#58a6ff;font-weight:600;margin-bottom:8px;font-size:0.9rem;">TODAY'S KEY NEWS</div>"""
        for n in news_items[:8]:
            link = n.get("link", "")
            title = n["title"][:80]
            title_html = f'<a href="{link}" style="color:#e6edf3;text-decoration:none;border-bottom:1px dotted #8b949e;">{title}</a>' if link else title
            s += f'<div style="font-size:0.75rem;padding:3px 0;border-bottom:1px solid #30363d;"><span style="color:#F5A623;font-weight:700;">{n["ticker"]}</span> {title_html} <span style="color:#8b949e;font-size:0.68rem;">&mdash; {n["published"]}</span></div>'
        s += "</div>"

    s += '<div style="text-align:center;color:#8b949e;font-size:0.7rem;margin-top:10px;">Generated by Morning Briefing System &bull; Prices may lag. Broker app is final word.</div></div>'
    return s


def run_briefing():
    """Run the full briefing pipeline — morning, midday, or market close."""
    briefing_type = get_briefing_type()
    ts = now_et().strftime("%Y-%m-%d %I:%M %p ET")
    labels = {"morning": "MORNING BRIEFING", "midday": "MIDDAY UPDATE", "close": "MARKET CLOSE"}
    print(f"\n{'='*60}")
    print(f"  {labels.get(briefing_type, 'BRIEFING')} — {ts}")
    print(f"{'='*60}\n")

    print("1. Fetching prices...")
    tickers = get_all_tickers()
    fx_rate = fetch_fx_rate()
    prices = fetch_prices(tickers)
    success = sum(1 for v in prices.values() if "error" not in v)
    print(f"   {success}/{len(tickers)} tickers fetched. USD/CAD = {fx_rate}")

    print("2. Building portfolio snapshot...")
    snapshot = build_snapshot(prices, fx_rate)
    print(f"   Portfolio: ${snapshot['total_portfolio_cad']:,.2f} CAD")

    print("3. Calculating target progress...")
    progress = calc_target_progress(snapshot)

    print("4. Checking caps...")
    cap_data = check_caps(snapshot)
    if cap_data["breaches"]:
        print(f"   Breaches: {', '.join(b['ticker'] for b in cap_data['breaches'])}")

    print("5. Evaluating focus buys & generating verdict...")
    focus_buys = evaluate_focus_buys(prices, snapshot, cap_data)
    verdict_lines = generate_verdict(focus_buys, progress, cap_data, snapshot)

    print("6. Fetching news...")
    watchlist = load_json("watchlist.json")
    held = watchlist["held"]
    tier2 = [t["ticker"] for t in watchlist["tier2"]["tickers"]]
    news_items = fetch_news(held + tier2)
    plan = load_json("plan.json")
    thesis_flags = check_thesis_breaks(news_items, plan["buy_zones"])
    print(f"   {len(news_items)} articles, {len(thesis_flags)} thesis flags")

    print("7. Comparing to yesterday...")
    prev = load_previous_snapshot()
    changes = calc_what_changed(snapshot, focus_buys, cap_data, prev)
    save_daily_snapshot(snapshot, focus_buys, cap_data, progress)

    print("8. Generating dashboard data...")
    tfsa_data = load_json("contributions.json")
    generate_dashboard_data(
        snapshot, progress, cap_data, focus_buys, verdict_lines,
        news_items, thesis_flags, changes, prices, tfsa_data,
        briefing_type=briefing_type
    )

    print(f"9. Building {briefing_type} email...")
    date_str = now_et().strftime("%B %d, %Y")
    if briefing_type == "morning":
        email_html = build_email_html(
            verdict_lines, progress, snapshot, cap_data, focus_buys,
            news_items, thesis_flags, changes, prices, tfsa_data
        )
        subject = f"Morning Briefing — {date_str}"
    elif briefing_type == "midday":
        email_html = build_midday_email_html(snapshot, focus_buys, thesis_flags)
        subject = f"Midday Update — {date_str} | ${snapshot['total_portfolio_cad']:,.0f} CAD"
    else:
        email_html = build_close_email_html(snapshot, focus_buys, thesis_flags, news_items)
        subject = f"Market Close — {date_str} | ${snapshot['total_portfolio_cad']:,.0f} CAD"

    print("10. Sending email...")
    send_email(email_html, subject)

    print("11. Building & sending SMS...")
    if briefing_type == "morning":
        sms_body = build_sms_body(verdict_lines, snapshot, focus_buys, cap_data, thesis_flags)
    elif briefing_type == "midday":
        sms_body = build_midday_sms_body(snapshot, focus_buys, thesis_flags)
    else:
        sms_body = build_close_sms_body(snapshot, focus_buys, thesis_flags)
    send_sms(sms_body)

    print(f"\n{'='*60}")
    print("  VERDICT:")
    for line in verdict_lines:
        print(f"  {line}")
    print(f"{'='*60}\n")

    return {
        "briefing_type": briefing_type,
        "snapshot": snapshot,
        "progress": progress,
        "cap_data": cap_data,
        "focus_buys": focus_buys,
        "verdict": verdict_lines,
        "news": news_items,
        "thesis_flags": thesis_flags,
        "changes": changes,
        "email_html": email_html,
        "sms_body": sms_body,
    }


if __name__ == "__main__":
    run_briefing()

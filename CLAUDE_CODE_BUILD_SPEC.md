# Portfolio Morning Briefing System — Complete Build Spec (v4)

**Hand this entire file to Claude Code. Say: "Read the whole spec first, then propose a plan and the recommended free APIs before writing any code. Build step by step and explain each piece in plain English. I am not a developer."**

---

## What I'm building

A personal, automated portfolio morning-briefing system that runs in the cloud via GitHub Actions. It must:

1. Store my holdings and plan data permanently in the repo as files
2. Pull live stock prices and recent news every morning automatically
3. Convert USD holdings to CAD using a live FX rate so all weighting and cap math is accurate
4. Check every holding against buy zones, position caps, and the scorecard
5. Track what changed since yesterday (real deltas, not cold snapshots)
6. Let me log a buy/sell with a single command and update holdings permanently
7. Deliver a morning briefing to **email, text message, and a web dashboard**
8. Run on a schedule (7:30 AM ET weekdays) with my computer off
9. Show progress toward my target allocation (current state vs target state)

I have a GitHub account. I'm on Windows. Build this as a GitHub repository with GitHub Actions scheduling.

---

## MY GOAL (important — shapes the whole strategy)

Long-term growth and a large, growing tax-free savings account. NOT a hard-deadline house purchase. This means a **wealth-building horizon longer than 5 years**, steady contributions (at least the $7,000/year TFSA limit, assume $7K/year through August 2027, likely more once working full-time), and dollar-cost averaging through dips. I can tolerate volatility because I'm not forced to sell on a fixed date — but I still need real diversification so one bad theme cannot erase years of progress.

---

## CRITICAL CONTEXT — read before building

- **I hold fractional shares.** Positions like 0.0057 shares are normal. Handle fractional shares everywhere. I can buy fractional shares, so "too small to buy" is rarely a hard blocker — but warn me when a cap allows only a tiny/awkward buy.
- **My accounts are CAD but most stocks are USD.** Convert with a LIVE USD→CAD rate (snapshot implied ~1.41605; do not hardcode).
- **Owned vs watchlist are different.** I own 8 positions. I do NOT own any Tier 2 (BWXT, MSFT, PLTR) yet. Never show a watchlist name as owned.
- **My current holdings are long-term conviction buys at good prices — NOT mistakes.** CEG, ETN, GEV, OSS, PWR, SOFI were each bought deliberately. "Hold, no add" means I'm not putting NEW money into them while I build the diversified core and Tier 2 — it does NOT mean sell or trim. They shrink as a % only through dilution, never selling.
- **Diversification is a priority, not an afterthought.** My stock picks are concentrated in one correlated theme (AI, power, grid, nuclear, electrification). The XEQT core is my diversification engine and must be LEANED ON — see target allocation.
- **Account is growing fast.** ~$1,298 CAD today → targeting ~$5,000 CAD as the next milestone via $750–$1,000 bi-weekly + ~$100/week. Plan for the $5,000 target state.

---

## THE DIVERSIFICATION STRATEGY (read carefully)

My individual stock picks lean heavily into one correlated theme. Rather than clutter a small account with many tiny sector positions (healthcare, financials, staples bought individually), **the ETF core does the diversifying.** XEQT.TO holds ~10,000 stocks across US, Canada, international developed, and emerging markets — every sector and geography I'm otherwise missing, in one ticker that auto-rebalances.

**ETF setup (final):**
- **XEQT.TO** = my single growing diversified core. All new ETF money goes here. Target ~40%.
- **VFV.TO** = legacy hold (S&P 500, overlaps with my tech/AI concentration). Hold what I own, add NO new money. Shrinks by dilution.
- **No second ETF until ~$15K+.** Two all-in-one ETFs is redundant. Past $15K I may add a deliberate sector satellite (e.g. CHPS.TO semiconductors, or a healthcare ETF) — future decision, not now.

This keeps real single-theme exposure to ~45% with ~40% genuinely diversified, instead of ~60% concentration.

---

## TWO STATES TO TRACK

### Current state (June 24, 2026)
~$1,298 CAD. Held: CEG, ETN, GEV, OSS, PWR, SOFI, VFV.TO, XEQT.TO. No Tier 2 owned. XEQT core only ~$128.

### Target state (~$5,000 CAD next milestone) — advisor-recommended allocation
| Bucket | Target % | ~CAD at $5K | Notes |
|--------|----------|-------------|-------|
| XEQT.TO core | 40% | ~$2,000 | Diversification engine. Covers every sector/geography my stocks miss. Fund FIRST every deposit until target. |
| Tier 2 (BWXT, MSFT, PLTR) | 22% | ~$1,100 | Active build priority. BWXT ~9%, MSFT ~8%, PLTR ~5% (hard cap). |
| Current conviction holdings | 28% | ~$1,400 | CEG, ETN, GEV, OSS, PWR, SOFI — held, not added to. Shrink by dilution. No single name >15%. |
| Cash | 10% | ~$500 | Dry powder for red days / limit orders. |

This puts single-theme (AI/power/nuclear) exposure at ~45% with ~40% truly diversified. Growth-tilted but not a one-theme bet. Dashboard must show current % vs target % per bucket and the gap to close.

**Past $15K:** revisit adding a deliberate sector-diversifier satellite (healthcare or payments name, or CHPS.TO). Not before.

---

## DEPLOYMENT SEQUENCE (now → $5,000)

Every new deposit follows this order:

1. **XEQT.TO first** — ~40% of each deposit to the core until it reaches ~$2,000. This is the diversification engine; it gets funded first, always.
2. **Then Tier 2, price-permitting** — BWXT first (best fit), then MSFT, then PLTR (only when 5% cap allows a real buy). Skip any Tier 2 name above its no-chase zone; route to next eligible name or hold cash.
3. **No new money into current conviction holdings** during the build. SOFI only after Tier 2 priority met.

The verdict should always answer: "Given today's prices and my deposit cadence, what's the single best next buy to move toward the $5,000 target allocation?"

---

## Architecture

- **Language:** Python 3
- **Repo files:**
  - `data/holdings.json` — real positions (exact, below)
  - `data/watchlist.json` — full watchlist by tier (below)
  - `data/plan.json` — buy zones, caps, scorecard, thesis, target allocation (below)
  - `data/contributions.json` — TFSA contribution + deposit cadence tracking
  - `data/history/` — daily snapshots for "what changed"
  - `scripts/briefing.py` — morning engine
  - `scripts/log_trade.py` — logs buys/sells, updates holdings
  - `dashboard/` — static web dashboard (GitHub Pages)
  - `.github/workflows/morning.yml` — scheduler
- **Data sources:** free stock price API good for fractional shares + Canadian tickers (XEQT.TO, VFV.TO). Recommend Financial Modeling Prep / Finnhub / Alpha Vantage and walk me through the key. Live USD/CAD FX. News from provider or free news API.
- **Secrets:** all keys/creds in GitHub repository secrets. Never hardcoded.

---

## MY EXACT HOLDINGS (snapshot June 24, 2026, ~12:25 PM ET)

### Combined
Questrade TFSA **$969.09 CAD** · Wealthsimple TFSA **$329.03 CAD** · Combined **$1,298.12 CAD** (~$916.72 USD)

### Questrade TFSA — held (USD stocks)
| Ticker | Shares | Avg Cost USD | Last Price USD | Value USD | Account | Currency |
|--------|--------|--------------|----------------|-----------|---------|----------|
| CEG | 1.3491 | 248.28 | 270.77 | 365.29 | Questrade | USD |
| ETN | 0.1714 | 379.05 | 407.21 | 69.79 | Questrade | USD |
| GEV | 0.0057 | 866.30 | 1044.00 | 5.95 | Questrade | USD |
| OSS | 6 | 15.78 | 17.35 | 104.10 | Questrade | USD |
| PWR | 0.0772 | 647.03 | 705.00 | 54.42 | Questrade | USD |
| SOFI | 4.8391 | 17.22 | 17.35 | 83.95 | Questrade | USD |

Questrade cash: $1.22 CAD.

### Wealthsimple TFSA — held (CAD ETFs)
| Ticker | Shares | Avg Price CAD | Last Price CAD | Value CAD | Account | Currency |
|--------|--------|---------------|----------------|-----------|---------|----------|
| VFV.TO | 1.0801 | 183.98 | 186.00 | 200.90 | Wealthsimple | CAD |
| XEQT.TO | 2.8494 | 45.42 | 44.94 | 128.05 | Wealthsimple | CAD |

Wealthsimple cash: $0.08 CAD.

**These 8 positions are my complete current holdings. All long-term conviction buys.**

---

## FULL WATCHLIST — track prices for all, separate from holdings

### Held (8)
CEG, ETN, GEV, OSS, PWR, SOFI (Questrade) · VFV.TO, XEQT.TO (Wealthsimple)

### Tier 2 — ACTIVE BUY PRIORITY (not owned yet)
| Ticker | Role | Cap % | Score | Target weight |
|--------|------|-------|-------|---------------|
| BWXT | Best Tier 2 fit, nuclear/defense | 15 | 86 | ~9% |
| MSFT | Quality tech compounder | 15 | 86 | ~8% |
| PLTR | Capped AI satellite | 5 | 74 | ~5% |

### Tier 3 — months 2–3 (watch only)
NVDA, WMB, CRWD, KMI, HWM, FIX, ISRG, NBIS

### Tier 4 — speculative watch
RKLB, LUNR, ASTS, CRCL, PL, BAM

### ETF layer
XEQT.TO (core, held — grow to ~40%), VFV.TO (held, hold-only no new money), XIU.TO (not needed; redundant with XEQT), CHPS.TO (thematic semiconductor satellite — future, past $15K)

---

## PLAN DATA

### Position caps (HARD RULES)
- No single satellite position exceeds **15%** of total portfolio (unconditional below $15K — no escape clause)
- **PLTR capped at 5%** — no exceptions
- Cash target: 5–10%
- Flag if crypto + high-beta stocks exceed 50% of total net assets

### Buy zones, scorecard, thesis-break triggers
| Ticker | Role | Ref Price | Starter | Preferred | Aggressive | No-Chase | Cap% | Score | Thesis Break Trigger |
|--------|------|-----------|---------|-----------|------------|----------|------|-------|---------------------|
| XEQT.TO | Core ETF (held) | live | buy every deposit | — | — | — | — | 92 | Risk tolerance / time horizon changes |
| VFV.TO | U.S. ETF (held) | live | hold only, no new money | — | — | — | — | — | Hold; overlaps tech concentration |
| BWXT | Tier 2 priority | 209.89 | 205–210 | 180–195 | ≤175 | >220 | 15 | 86 | Backlog weakens, guidance cut, contract risk rises, valuation overheats |
| MSFT | Tier 2 priority | 373.94 | 365–375 | 335–355 | ≤325 | >400 | 15 | 86 | Azure slows sharply, AI capex hurts margins with no payoff |
| PLTR | Tier 2 capped | 116.70 | 105–115 | 90–100 | ≤85 | >120 | 5 | 74 | Growth slows, valuation breaks, govt demand weakens, position exceeds 5% |
| SOFI | Held conviction | 17.29 | 16.50–17.50 | 14.50–16 | ≤14 | — | 10 | 76 | Credit quality worsens, growth slows, funding costs rise |
| CEG | Held conviction | 270.26 | hold, no add | review <230 | review <203 | — | 15 | 83 | Power thesis weakens, nuclear regulation worsens, guidance deteriorates |
| ETN | Held conviction | 405.28 | hold, no add | review <344 | review <304 | — | 15 | 78 | Backlog weakens, margins compress, data center demand slows |
| GEV | Held conviction | 1034.98 | hold, no add | review <880 | review <776 | — | 15 | 80 | AI power buildout slows, guidance weakens, execution problems |
| PWR | Held conviction | 702.29 | hold, no add | review <597 | review <527 | — | 15 | 76 | Backlog weakens, utility spending slows, margins deteriorate |
| OSS | Held conviction | 17.02 | hold, no add | review <14.50 | review <12.75 | — | 7 | 65 | Growth stalls, dilution rises, thesis becomes unclear |

**PLTR note:** ref price/zones stale — PLTR recently hit a 52-week low (~$116.70) on European government contract losses (Switzerland legal loss; France replacing with ChapsVision). Refresh ref prices; keep PLTR European contract risk as an active monitoring flag.

**Framing:** "hold, no add" on conviction holdings is a deployment-priority choice (build diversified core + Tier 2 first), NOT a negative judgment. Long-term holds bought at good prices.

### Focus buys (top of briefing, priority order)
1. XEQT.TO (core / diversification engine — fund first every deposit until ~$2,000 / 40%)
2. BWXT (first Tier 2 buy, price-permitting)
3. MSFT (second Tier 2)
4. PLTR (capped satellite, only when 5% cap allows a real buy)
5. SOFI (only after Tier 2 priority met)

### Deposit allocation rules (build phase, diversification-weighted)
| Deposit | Allocation |
|---------|-----------|
| $100 | $100 XEQT.TO (build core) |
| $250 | $120 XEQT.TO, $130 BWXT (or MSFT if BWXT above no-chase) |
| $500 | $220 XEQT.TO, $150 BWXT, $130 MSFT |
| $1,000 | $400 XEQT.TO, $250 BWXT, $200 MSFT, $100 PLTR (if 5% cap allows), $50 cash |

Rule: XEQT funded first toward ~40% / ~$2,000. Tier 2 next, price-permitting. Skip any Tier 2 name above its no-chase zone; route to next eligible name or cash. No new money into current conviction holdings during build. No new money into VFV.

### Scorecard weights
Economic need 15%, Bottleneck exposure 20%, Business quality 20%, Valuation discipline 15%, Portfolio fit 15%, Risk control 10%, Source confidence 5%.
90+ strong buy; 80–89 approved; 70–79 watchlist/starter; <70 do not buy.

### Attractive-price test for adding to a name (ALL four must pass)
1. Materially cheaper (down 15–25% from recent high or below pre-written buy zone)
2. Thesis intact
3. Sizing safe (under 15% cap; PLTR under 5%)
4. Core (XEQT) still funded first

### Execution rules
Limit orders only; never buy at open (wait 9:45–10:15 AM ET); cancel unfilled day orders by 3:30 PM; never chase up; one stock at a time, staggered; rebalance via new deposits, not selling.

### TFSA contribution tracking
- Min $7,000/year committed (assume $7K/year through August 2027, likely more once full-time)
- Adding $750–$1,000 bi-weekly + ~$100/week
- Track contributions used vs limit; show remaining room and projected date to hit $5,000 at current cadence

---

## Morning briefing output (in order)

1. **Today's verdict** — 4–6 blunt sentences. Lead with the single best next buy to move toward the $5,000 target. If nothing actionable, say "No buys today" and why.
2. **Progress to target** — current % vs target % per bucket (core 40 / Tier 2 22 / conviction 28 / cash 10), and the gap to close. Highlight whether I'm under-diversified (core below target).
3. **What changed since yesterday** — price moves, new news, zone/cap status changes.
4. **Portfolio snapshot** — total CAD + USD, per-account split, cash, unrealized gain per position and overall.
5. **Cap status** — each held position's % of total, room to cap in CAD, breaches flagged red (check CEG specifically).
6. **Focus buys** — 5 priority names: live price, day change, zone status (BUY/WATCH/WAIT/HOLD), cap room CAD, score, buyable-at-my-size check, one-line reason tied to today's news.
7. **News & catalyst flags** — material 48h news, tagged by ticker + impact.
8. **Full price board** — all watchlist tickers (all tiers), price, day change, zone status.
9. **Thesis-break watch** — break criteria per held name, flagged if news matches.
10. **TFSA room** — contributions used vs limit, remaining room, projected date to $5,000.

---

## Verdict tone
Blunt, direct, no hedging, no hype. Lead with the action. Treat current holdings as conviction holds, never mistakes. Prioritize building the diversified XEQT core and Tier 2. If the core is below its 40% target, say so and prioritize it — diversification first. Flag any Tier 2 name in a buy zone with cap room. If a name is above no-chase or a cap is breached, say don't buy. Broker app is final word; prices may lag minutes.

---

## Build sequence (confirm each step before moving on)

1. Create repo; commit holdings.json, watchlist.json, plan.json (with target allocation), contributions.json — exact data above.
2. briefing.py: pull live prices for all watchlist tickers + live USD/CAD; print. Test locally.
3. Add CAD/USD conversion, portfolio snapshot, per-position weighting.
4. Add target-progress calc (current % vs target % per bucket; flag if core under-weight).
5. Add cap math (fractional shares + too-small-to-buy warning); flag breaches.
6. Add buy-zone logic, scorecard, deployment-sequence verdict generator.
7. Add news fetching + "what changed since yesterday" snapshot comparison.
8. log_trade.py: record buys/sells, update holdings + contributions.
9. Dashboard on GitHub Pages.
10. Email delivery; test.
11. Twilio text delivery; test.
12. GitHub Actions weekday 7:30 AM ET.
13. Full end-to-end test.

**Before writing code: propose the plan, recommend the free APIs, and list every account/key I need to create. Then build step by step.**

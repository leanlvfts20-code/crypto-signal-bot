import os
import json
import time
import schedule
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import anthropic

# ── Config ─────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SENDGRID_API_KEY  = os.environ["SENDGRID_API_KEY"]
FROM_EMAIL        = os.environ["FROM_EMAIL"]
TO_EMAIL          = os.environ["TO_EMAIL"]
MORNING_TIME      = os.environ.get("MORNING_TIME", "07:00")
EVENING_TIME      = os.environ.get("EVENING_TIME", "15:00")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Search system ───────────────────────────────────────────────────────────────
SEARCH_SYSTEM = "You are a financial market researcher. Search the web and return concise, factual summaries of what you find. Focus on the most recent and relevant data only."

# ── Analysis system ─────────────────────────────────────────────────────────────
def get_analysis_system(edition: str) -> str:
    timeframes = "scalp (minutes-hours) and swing (1-3 days)" if edition == "morning" else "scalp (minutes-hours) and evening session (same day)"
    return f"""You are an expert trader covering crypto and stocks. Given market research, output ONLY raw JSON (no markdown, no backticks, no explanation).

Return this exact structure:
{{
  "edition": "{edition}",
  "marketCondition": "brief 1-2 sentence overall market mood",
  "fearGreedIndex": {{
    "value": 65,
    "label": "Greed",
    "interpretation": "one sentence on what this means for trading today"
  }},
  "asiaMarkets": {{
    "summary": "brief summary of Asia session performance",
    "notable": ["Nikkei up 1.2% on BOJ news", "Hang Seng flat"]
  }},
  "cryptoPicks": [
    {{
      "rank": 1,
      "symbol": "BTC",
      "name": "Bitcoin",
      "currentPrice": "$65,000",
      "riskLevel": "Medium",
      "scalp": {{
        "entryPrice": "$64,800 - $65,000",
        "targetPrice": "$65,800",
        "stopLoss": "$64,200",
        "upside": "+1.2%",
        "strategy": "Buy the dip at support, quick scalp to resistance"
      }},
      "swing": {{
        "entryPrice": "$64,500 - $65,000",
        "targetPrice": "$68,000",
        "stopLoss": "$63,000",
        "upside": "+4.6%",
        "strategy": "Accumulate on pullbacks, hold 1-3 days for breakout"
      }},
      "catalyst": "reason this coin is moving",
      "sentiment": "bullish",
      "confidence": 82
    }},
    {{
      "rank": 2,
      "symbol": "ETH",
      "name": "Ethereum",
      "currentPrice": "$3,200",
      "riskLevel": "Medium",
      "scalp": {{"entryPrice": "$3,180","targetPrice": "$3,260","stopLoss": "$3,120","upside": "+2.5%","strategy": "scalp strategy"}},
      "swing": {{"entryPrice": "$3,150","targetPrice": "$3,450","stopLoss": "$3,050","upside": "+9.5%","strategy": "swing strategy"}},
      "catalyst": "catalyst",
      "sentiment": "bullish",
      "confidence": 75
    }},
    {{
      "rank": 3,
      "symbol": "SOL",
      "name": "Solana",
      "currentPrice": "$150",
      "riskLevel": "Medium",
      "scalp": {{"entryPrice": "$149","targetPrice": "$155","stopLoss": "$146","upside": "+4%","strategy": "scalp strategy"}},
      "swing": {{"entryPrice": "$148","targetPrice": "$165","stopLoss": "$142","upside": "+11%","strategy": "swing strategy"}},
      "catalyst": "catalyst",
      "sentiment": "bullish",
      "confidence": 70
    }}
  ],
  "memeCoinPicks": [
    {{
      "rank": 1,
      "symbol": "DOGE",
      "name": "Dogecoin",
      "currentPrice": "$0.12",
      "riskLevel": "High",
      "entryPrice": "$0.118 - $0.122",
      "targetPrice": "$0.135",
      "stopLoss": "$0.110",
      "upside": "+12%",
      "catalyst": "trending on Twitter, Elon mention",
      "strategy": "Small position only, tight stop, take profits quickly",
      "confidence": 60
    }}
  ],
  "stockPicks": [
    {{
      "rank": 1,
      "ticker": "NVDA",
      "name": "NVIDIA",
      "currentPrice": "$875",
      "riskLevel": "Medium",
      "eventType": "earnings|IPO|news|technical",
      "eventDetail": "Earnings beat by 15%, raised guidance",
      "scalp": {{
        "entryPrice": "$870 - $878",
        "targetPrice": "$895",
        "stopLoss": "$858",
        "upside": "+2.3%",
        "strategy": "Buy pre-market dip, scalp gap fill to resistance"
      }},
      "swing": {{
        "entryPrice": "$865 - $875",
        "targetPrice": "$920",
        "stopLoss": "$845",
        "upside": "+5.7%",
        "strategy": "Post-earnings momentum play, hold 2-3 days"
      }},
      "sentiment": "bullish",
      "confidence": 78
    }},
    {{
      "rank": 2,
      "ticker": "TSLA",
      "name": "Tesla",
      "currentPrice": "$185",
      "riskLevel": "Medium",
      "eventType": "news",
      "eventDetail": "event detail",
      "scalp": {{"entryPrice": "$183","targetPrice": "$190","stopLoss": "$179","upside": "+3.8%","strategy": "scalp strategy"}},
      "swing": {{"entryPrice": "$182","targetPrice": "$200","stopLoss": "$175","upside": "+9.9%","strategy": "swing strategy"}},
      "sentiment": "bullish",
      "confidence": 72
    }},
    {{
      "rank": 3,
      "ticker": "SPY",
      "name": "S&P 500 ETF",
      "currentPrice": "$520",
      "riskLevel": "Low",
      "eventType": "technical",
      "eventDetail": "event detail",
      "scalp": {{"entryPrice": "$518","targetPrice": "$524","stopLoss": "$515","upside": "+1.2%","strategy": "scalp strategy"}},
      "swing": {{"entryPrice": "$517","targetPrice": "$530","stopLoss": "$512","upside": "+2.5%","strategy": "swing strategy"}},
      "sentiment": "neutral",
      "confidence": 68
    }}
  ],
  "iposAndEarnings": [
    {{
      "type": "Earnings|IPO|Split|Merger",
      "ticker": "AAPL",
      "name": "Apple",
      "detail": "Reports after close today, expected EPS $1.50",
      "impact": "High",
      "tradeIdea": "Buy calls before close if market bullish, sell into earnings pop"
    }}
  ],
  "watchlist": {{"crypto": ["PEPE","ARB","INJ"], "stocks": ["AMD","META","MSFT"]}},
  "disclaimer": "Not financial advice. Always do your own research."
}}

Rules:
- ONLY include crypto picks with riskLevel Low or Medium (exclude High risk from cryptoPicks)
- memeCoinPicks can be High risk but clearly labeled
- Fill ALL fields with real current data from the research
- Output ONLY the JSON, nothing else"""


def run_search(prompt: str, max_tokens: int = 2048) -> str:
    messages = [{"role": "user", "content": prompt}]
    for _ in range(8):
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=max_tokens,
            system=SEARCH_SYSTEM,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            return "".join(b.text for b in response.content if hasattr(b, "text"))

        if response.stop_reason == "tool_use":
            tool_results = [
                {"type": "tool_result", "tool_use_id": b.id, "content": "OK"}
                for b in response.content if b.type == "tool_use"
            ]
            messages.append({"role": "user", "content": tool_results})
            continue

        text = "".join(b.text for b in response.content if hasattr(b, "text"))
        if text: return text
        raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")

    raise RuntimeError("Search loop exceeded max rounds.")


def get_analysis(edition: str) -> dict:
    today = datetime.now().strftime("%A, %B %d, %Y")
    now = datetime.now().strftime("%I:%M %p")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Searching markets ({edition} edition)...")

    research = run_search(
        f"Today is {today}, time is {now}. Search for ALL of the following and summarize concisely:\n"
        "1. Current Fear & Greed Index value and label\n"
        "2. BTC and ETH current prices and 24h trend\n"
        "3. Top 3 gaining/moving cryptocurrencies today with reasons\n"
        "4. Trending meme coins on social media right now\n"
        "5. Asia market session summary (Nikkei, Hang Seng, Shanghai)\n"
        "6. Top 3 most important US stock news today (earnings, IPOs, major moves)\n"
        "7. Any upcoming earnings calls today or tomorrow\n"
        "8. Major stock movers pre/post market today\n"
        "Be specific with numbers and prices."
    )

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating {edition} signal picks...")

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        system=get_analysis_system(edition),
        messages=[{
            "role": "user",
            "content": f"Market research for {today} ({edition} edition):\n\n{research[:4000]}\n\nOutput the JSON now."
        }],
    )

    raw = "".join(b.text for b in response.content if hasattr(b, "text")).strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1:
        raise ValueError(f"No JSON found: {raw[:300]}")
    return json.loads(raw[start:end])


# ── HTML helpers ────────────────────────────────────────────────────────────────
def sc(s): return {"bullish": "#00e5a0", "bearish": "#ff4d6d"}.get((s or "").lower(), "#f0c040")
def se(s): return {"bullish": "🟢", "bearish": "🔴"}.get((s or "").lower(), "🟡")
def rc(r): return {"low": "#00e5a0", "high": "#ff4d6d"}.get((r or "").lower(), "#f0c040")
def ic(i): return {"high": "#ff4d6d", "low": "#00e5a0"}.get((i or "").lower(), "#f0c040")

def timeframe_block(label: str, data: dict, color: str) -> str:
    return f"""
    <div style="background:#0a1020;border-radius:4px;padding:10px;margin-bottom:8px;">
      <div style="font-size:9px;letter-spacing:2px;color:{color};margin-bottom:6px;">{label}</div>
      <table style="width:100%;border-collapse:separate;border-spacing:3px 0;">
        <tr>
          <td style="background:#080c14;padding:6px 8px;border-radius:3px;text-align:center;">
            <div style="font-size:8px;color:#4a6080;margin-bottom:2px;">ENTRY</div>
            <div style="font-size:11px;font-weight:700;color:#00e5a0;">{data.get('entryPrice','—')}</div>
          </td>
          <td style="background:#080c14;padding:6px 8px;border-radius:3px;text-align:center;">
            <div style="font-size:8px;color:#4a6080;margin-bottom:2px;">TARGET</div>
            <div style="font-size:11px;font-weight:700;color:#00aaff;">{data.get('targetPrice','—')}</div>
          </td>
          <td style="background:#080c14;padding:6px 8px;border-radius:3px;text-align:center;">
            <div style="font-size:8px;color:#4a6080;margin-bottom:2px;">STOP</div>
            <div style="font-size:11px;font-weight:700;color:#ff4d6d;">{data.get('stopLoss','—')}</div>
          </td>
          <td style="background:#080c14;padding:6px 8px;border-radius:3px;text-align:center;">
            <div style="font-size:8px;color:#4a6080;margin-bottom:2px;">UPSIDE</div>
            <div style="font-size:11px;font-weight:700;color:#f0c040;">{data.get('upside','—')}</div>
          </td>
        </tr>
      </table>
      <div style="font-size:11px;color:#a0b8d0;margin-top:6px;font-style:italic;">{data.get('strategy','—')}</div>
    </div>"""

def crypto_card(p: dict, i: int) -> str:
    badge_bg = ["#00e5a0","#00aaff","#8855ff"][min(i,2)]
    badge_fg = "#080c14" if i == 0 else "#e0eaff"
    border = "#00e5a0" if i == 0 else "#1e2d45"
    return f"""
    <div style="background:#0d1625;border:1px solid {border};border-radius:8px;padding:18px;margin-bottom:12px;position:relative;">
      {"<div style='position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,#00e5a0,#00aaff,transparent);border-radius:8px 8px 0 0;'></div>" if i==0 else ""}
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="background:{badge_bg};color:{badge_fg};border-radius:50%;width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;font-size:10px;font-weight:900;">#{p.get('rank')}</span>
          <div>
            <div style="font-size:19px;font-weight:900;color:#e0eaff;">{p.get('symbol')}</div>
            <div style="font-size:10px;color:#4a6080;">{p.get('name')}</div>
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:16px;font-weight:700;color:#e0eaff;">{p.get('currentPrice')}</div>
          <div style="font-size:10px;color:{sc(p.get('sentiment'))};">{se(p.get('sentiment'))} {(p.get('sentiment') or '').upper()}</div>
          <div style="font-size:10px;color:{rc(p.get('riskLevel'))};">RISK: {p.get('riskLevel')}</div>
        </div>
      </div>
      <div style="background:#0a1020;border-radius:4px;padding:8px 10px;margin-bottom:10px;font-size:11px;color:#a0b8d0;">
        <span style="color:#4a6080;font-size:9px;">CATALYST </span>{p.get('catalyst','—')}
      </div>
      {timeframe_block('⚡ SCALP TRADE', p.get('scalp', {}), '#f0c040')}
      {timeframe_block('📈 SWING TRADE', p.get('swing', {}), '#00aaff')}
      <div style="font-size:10px;color:#4a6080;">CONFIDENCE: <strong style="color:#e0eaff;">{p.get('confidence')}%</strong></div>
    </div>"""

def meme_card(p: dict) -> str:
    return f"""
    <div style="background:#0d1625;border:1px solid #ff4d6d44;border-radius:8px;padding:16px;margin-bottom:10px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div>
          <span style="font-size:17px;font-weight:900;color:#e0eaff;">{p.get('symbol')}</span>
          <span style="font-size:10px;color:#4a6080;margin-left:8px;">{p.get('name')}</span>
          <span style="background:#ff4d6d22;color:#ff4d6d;border-radius:3px;padding:2px 6px;font-size:9px;margin-left:8px;">HIGH RISK</span>
        </div>
        <div style="font-size:14px;font-weight:700;color:#e0eaff;">{p.get('currentPrice')}</div>
      </div>
      <table style="width:100%;border-collapse:separate;border-spacing:3px 0;margin-bottom:8px;">
        <tr>
          <td style="background:#0a1020;padding:6px;border-radius:3px;text-align:center;">
            <div style="font-size:8px;color:#4a6080;">ENTRY</div>
            <div style="font-size:11px;font-weight:700;color:#00e5a0;">{p.get('entryPrice','—')}</div>
          </td>
          <td style="background:#0a1020;padding:6px;border-radius:3px;text-align:center;">
            <div style="font-size:8px;color:#4a6080;">TARGET</div>
            <div style="font-size:11px;font-weight:700;color:#00aaff;">{p.get('targetPrice','—')}</div>
          </td>
          <td style="background:#0a1020;padding:6px;border-radius:3px;text-align:center;">
            <div style="font-size:8px;color:#4a6080;">STOP</div>
            <div style="font-size:11px;font-weight:700;color:#ff4d6d;">{p.get('stopLoss','—')}</div>
          </td>
          <td style="background:#0a1020;padding:6px;border-radius:3px;text-align:center;">
            <div style="font-size:8px;color:#4a6080;">UPSIDE</div>
            <div style="font-size:11px;font-weight:700;color:#f0c040;">{p.get('upside','—')}</div>
          </td>
        </tr>
      </table>
      <div style="font-size:11px;color:#a0b8d0;margin-bottom:6px;"><span style="color:#4a6080;font-size:9px;">CATALYST </span>{p.get('catalyst','—')}</div>
      <div style="font-size:11px;color:#f0c040;font-style:italic;">{p.get('strategy','—')}</div>
      <div style="font-size:10px;color:#4a6080;margin-top:6px;">CONFIDENCE: <strong style="color:#e0eaff;">{p.get('confidence')}%</strong></div>
    </div>"""

def stock_card(p: dict, i: int) -> str:
    border = "#00e5a0" if i == 0 else "#1e2d45"
    event_colors = {"earnings": "#f0c040", "ipo": "#00e5a0", "split": "#00aaff", "merger": "#8855ff", "news": "#a0b8d0"}
    ev_color = event_colors.get((p.get('eventType') or '').lower(), "#a0b8d0")
    return f"""
    <div style="background:#0d1625;border:1px solid {border};border-radius:8px;padding:18px;margin-bottom:12px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div>
          <span style="font-size:19px;font-weight:900;color:#e0eaff;">{p.get('ticker')}</span>
          <span style="font-size:10px;color:#4a6080;margin-left:8px;">{p.get('name')}</span>
        </div>
        <div style="text-align:right;">
          <div style="font-size:15px;font-weight:700;color:#e0eaff;">{p.get('currentPrice')}</div>
          <div style="font-size:10px;color:{sc(p.get('sentiment'))};">{se(p.get('sentiment'))} {(p.get('sentiment') or '').upper()}</div>
        </div>
      </div>
      <div style="background:{ev_color}22;border:1px solid {ev_color}44;border-radius:4px;padding:8px 10px;margin-bottom:10px;">
        <span style="font-size:9px;letter-spacing:1px;color:{ev_color};">{(p.get('eventType') or '').upper()} </span>
        <span style="font-size:11px;color:#c0d8f0;">{p.get('eventDetail','—')}</span>
      </div>
      {timeframe_block('⚡ SCALP TRADE', p.get('scalp', {}), '#f0c040')}
      {timeframe_block('📈 SWING TRADE', p.get('swing', {}), '#00aaff')}
      <div style="font-size:10px;color:#4a6080;">RISK: <strong style="color:{rc(p.get('riskLevel'))};">{p.get('riskLevel')}</strong> &nbsp;|&nbsp; CONFIDENCE: <strong style="color:#e0eaff;">{p.get('confidence')}%</strong></div>
    </div>"""

def section_header(title: str, subtitle: str = "") -> str:
    return f"""
    <div style="margin:24px 0 12px;">
      <div style="font-size:10px;letter-spacing:3px;color:#4a6080;margin-bottom:2px;">{title}</div>
      {"<div style='font-size:11px;color:#2a3a50;'>" + subtitle + "</div>" if subtitle else ""}
    </div>"""


def build_html(data: dict, edition: str) -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")
    now = datetime.now().strftime("%I:%M %p")
    edition_label = "🌅 MORNING BRIEF" if edition == "morning" else "🌆 EVENING SESSION"
    edition_color = "#f0c040" if edition == "morning" else "#00aaff"

    # Fear & Greed
    fg = data.get("fearGreedIndex", {})
    fg_val = fg.get("value", 50)
    fg_label = fg.get("label", "Neutral")
    fg_color = "#00e5a0" if fg_val >= 60 else "#ff4d6d" if fg_val <= 40 else "#f0c040"
    fg_bar = f"""
    <div style="margin-top:10px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
        <span style="font-size:9px;color:#4a6080;">FEAR</span>
        <span style="font-size:12px;font-weight:900;color:{fg_color};">{fg_val} — {fg_label}</span>
        <span style="font-size:9px;color:#4a6080;">GREED</span>
      </div>
      <div style="height:6px;background:#1a2a40;border-radius:3px;">
        <div style="height:100%;width:{fg_val}%;background:linear-gradient(90deg,#ff4d6d,#f0c040,#00e5a0);border-radius:3px;"></div>
      </div>
      <div style="font-size:11px;color:#a0b8d0;margin-top:6px;">{fg.get('interpretation','')}</div>
    </div>"""

    # Asia markets
    asia = data.get("asiaMarkets", {})
    asia_items = "".join(f'<div style="font-size:11px;color:#a0b8d0;margin-bottom:3px;">• {n}</div>' for n in asia.get("notable", []))
    asia_block = f"""
    <div style="background:#0d1625;border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:16px;margin-bottom:16px;">
      <div style="font-size:10px;letter-spacing:3px;color:#4a6080;margin-bottom:8px;">🌏 ASIA MARKETS</div>
      <div style="font-size:12px;color:#c0d8f0;margin-bottom:8px;">{asia.get('summary','')}</div>
      {asia_items}
    </div>"""

    # IPOs & Earnings
    events = data.get("iposAndEarnings", [])
    events_html = ""
    for ev in events:
        imp_color = ic(ev.get('impact'))
        ev_type_colors = {"Earnings": "#f0c040", "IPO": "#00e5a0", "Split": "#00aaff", "Merger": "#8855ff"}
        tc = ev_type_colors.get(ev.get('type',''), '#a0b8d0')
        events_html += f"""
        <div style="background:#0d1625;border:1px solid rgba(255,255,255,0.06);border-radius:6px;padding:14px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <div>
              <span style="font-size:14px;font-weight:900;color:#e0eaff;">{ev.get('ticker')}</span>
              <span style="font-size:10px;color:#4a6080;margin-left:6px;">{ev.get('name')}</span>
              <span style="background:{tc}22;color:{tc};border-radius:3px;padding:2px 6px;font-size:9px;margin-left:6px;">{ev.get('type','').upper()}</span>
            </div>
            <span style="font-size:9px;color:{imp_color};">⬤ {(ev.get('impact') or '').upper()} IMPACT</span>
          </div>
          <div style="font-size:11px;color:#a0b8d0;margin-bottom:6px;">{ev.get('detail','')}</div>
          <div style="font-size:11px;color:#f0c040;font-style:italic;">💡 {ev.get('tradeIdea','')}</div>
        </div>"""

    # Watchlist
    wl = data.get("watchlist", {})
    wl_crypto = "".join(f'<span style="background:#1a2a40;border-radius:4px;padding:3px 9px;font-size:11px;font-weight:700;color:#00e5a0;margin-right:5px;">{c}</span>' for c in wl.get("crypto", []))
    wl_stocks = "".join(f'<span style="background:#1a2a40;border-radius:4px;padding:3px 9px;font-size:11px;font-weight:700;color:#00aaff;margin-right:5px;">{c}</span>' for c in wl.get("stocks", []))

    # Crypto picks
    crypto_html = "".join(crypto_card(p, i) for i, p in enumerate(data.get("cryptoPicks", [])))

    # Meme picks
    meme_html = "".join(meme_card(p) for p in data.get("memeCoinPicks", []))

    # Stock picks
    stock_html = "".join(stock_card(p, i) for i, p in enumerate(data.get("stockPicks", [])))

    btc_sent = data.get("btcSentiment") or "neutral"

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#080c14;font-family:'Courier New',monospace;">
<div style="max-width:680px;margin:0 auto;padding:24px 16px;">

  <!-- Header -->
  <div style="margin-bottom:20px;">
    <div style="font-size:10px;letter-spacing:4px;color:#00e5a0;margin-bottom:4px;">● SIGNAL ACTIVE</div>
    <h1 style="margin:0 0 4px;font-size:24px;font-weight:900;color:#e0eaff;">CRYPTO & MARKETS SIGNAL</h1>
    <div style="display:flex;gap:12px;align-items:center;">
      <span style="font-size:13px;font-weight:700;color:{edition_color};">{edition_label}</span>
      <span style="font-size:11px;color:#4a6080;">{today} · {now}</span>
    </div>
  </div>

  <!-- Market Overview -->
  <div style="background:#0d1625;border:1px solid rgba(0,230,160,0.2);border-radius:8px;padding:18px;margin-bottom:16px;">
    <div style="font-size:10px;letter-spacing:3px;color:#00e5a0;margin-bottom:8px;">MARKET OVERVIEW</div>
    <p style="margin:0 0 10px;line-height:1.7;font-size:13px;color:#c0d8f0;">{data.get('marketCondition','')}</p>
    <span style="font-size:11px;color:#4a6080;">BTC: </span>
    <span style="font-size:11px;font-weight:700;color:{sc(btc_sent)};">{se(btc_sent)} {btc_sent.upper()}</span>
    {fg_bar}
  </div>

  <!-- Asia Markets -->
  {asia_block}

  <!-- IPOs & Earnings -->
  {section_header("📋 IPOS · EARNINGS · KEY EVENTS", "High-impact events and trade ideas")}
  {events_html if events_html else '<div style="color:#2a3a50;font-size:12px;padding:10px;">No major events today.</div>'}

  <!-- Crypto Picks -->
  {section_header("₿ TOP CRYPTO PICKS", "Low &amp; Medium risk only · Scalp and Swing levels")}
  {crypto_html}

  <!-- Meme Coins -->
  {section_header("🚀 MEME COIN RADAR", "High risk — small position sizes only")}
  {meme_html if meme_html else '<div style="color:#2a3a50;font-size:12px;padding:10px;">No meme coin setups today.</div>'}

  <!-- Stocks -->
  {section_header("📊 TOP STOCK PICKS", "Scalp and Swing trade plans")}
  {stock_html}

  <!-- Watchlist -->
  <div style="background:#0d1625;border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:14px;margin-bottom:16px;">
    <div style="font-size:10px;letter-spacing:3px;color:#4a6080;margin-bottom:10px;">👀 WATCHLIST</div>
    <div style="margin-bottom:8px;"><span style="font-size:9px;color:#4a6080;margin-right:8px;">CRYPTO</span>{wl_crypto}</div>
    <div><span style="font-size:9px;color:#4a6080;margin-right:8px;">STOCKS</span>{wl_stocks}</div>
  </div>

  <!-- Footer -->
  <div style="font-size:10px;color:#2a3a50;line-height:1.6;">
    ⚠ {data.get('disclaimer','Not financial advice. Always do your own research.')}<br>
    Generated {now} · Crypto &amp; Markets Signal Engine
  </div>

</div>
</body></html>"""


def send_email(html: str, edition: str):
    emoji = "🌅" if edition == "morning" else "🌆"
    subject = f"{emoji} {'Morning Brief' if edition == 'morning' else 'Evening Session'} — {datetime.now().strftime('%b %d, %Y')}"
    message = Mail(from_email=FROM_EMAIL, to_emails=TO_EMAIL, subject=subject, html_content=html)
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {edition.capitalize()} email sent to {TO_EMAIL}")


def run_job(edition: str):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting {edition} signal job...")
    try:
        data = get_analysis(edition)
        html = build_html(data, edition)
        send_email(html, edition)
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error ({edition}): {e}")


if __name__ == "__main__":
    print(f"Signal Bot started. Morning: {MORNING_TIME} | Evening: {EVENING_TIME}")

    # Run morning edition on startup to verify everything works
    run_job("morning")

    schedule.every().day.at(MORNING_TIME).do(run_job, edition="morning")
    schedule.every().day.at(EVENING_TIME).do(run_job, edition="evening")

    while True:
        schedule.run_pending()
        time.sleep(60)

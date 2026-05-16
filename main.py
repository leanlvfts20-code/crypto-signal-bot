import os
import json
import time
import schedule
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import anthropic

# ── Config ─────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
SENDGRID_API_KEY   = os.environ["SENDGRID_API_KEY"]
FROM_EMAIL         = os.environ["FROM_EMAIL"]       # must be verified in SendGrid
TO_EMAIL           = os.environ["TO_EMAIL"]
SEND_TIME          = os.environ.get("SEND_TIME", "15:00")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Prompts ────────────────────────────────────────────────────────────────────
SEARCH_SYSTEM = "You are a crypto market researcher. Search the web and summarize: current BTC price and trend, top 3 gaining altcoins today, any major crypto news in last 12 hours, and trending coins on social media. Be concise."

ANALYSIS_SYSTEM = """You are a crypto trader. Given market research, output ONLY raw JSON (no markdown, no backticks):
{"marketSummary":"string","btcSentiment":"bullish|bearish|neutral","topPicks":[{"rank":1,"symbol":"str","name":"str","currentPrice":"str","entryPrice":"str","targetPrice":"str","stopLoss":"str","upside":"str","confidence":80,"timeframe":"str","catalyst":"str","sentiment":"bullish|bearish|neutral","riskLevel":"Low|Medium|High"},{"rank":2,"symbol":"str","name":"str","currentPrice":"str","entryPrice":"str","targetPrice":"str","stopLoss":"str","upside":"str","confidence":75,"timeframe":"str","catalyst":"str","sentiment":"bullish","riskLevel":"Medium"},{"rank":3,"symbol":"str","name":"str","currentPrice":"str","entryPrice":"str","targetPrice":"str","stopLoss":"str","upside":"str","confidence":70,"timeframe":"str","catalyst":"str","sentiment":"bullish","riskLevel":"High"}],"watchlist":["SYM1","SYM2","SYM3"],"disclaimer":"Not financial advice. Always do your own research."}
Fill all fields with real data. Output ONLY the JSON."""


def run_search(user_message: str) -> str:
    """Multi-turn agentic web search loop."""
    messages = [{"role": "user", "content": user_message}]

    for _ in range(8):
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
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


def get_analysis() -> dict:
    today = datetime.now().strftime("%A, %B %d, %Y")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Searching markets...")

    research = run_search(
        f"Today is {today}. Find: BTC current price and 24h direction, "
        "top gaining altcoins today, major crypto news last 12 hours, "
        "trending coins on crypto social media. Keep it brief."
    )

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Analyzing picks...")

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        system=ANALYSIS_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Research:\n{research[:3000]}\n\nOutput JSON now."
        }],
    )

    raw = "".join(b.text for b in response.content if hasattr(b, "text")).strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1: raise ValueError(f"No JSON found: {raw[:200]}")
    return json.loads(raw[start:end])


def sem(s): 
    return {"bullish": "🟢", "bearish": "🔴"}.get((s or "").lower(), "🟡")

def build_html(data: dict) -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")
    btc = data.get("btcSentiment", "neutral")
    picks_html = ""

    for p in data.get("topPicks", []):
        border = "#00e5a0" if p.get("rank") == 1 else "#1e2d45"
        badge_bg = ["#00e5a0", "#00aaff", "#8855ff"][p.get("rank", 1) - 1]
        badge_fg = "#080c14" if p.get("rank") == 1 else "#e0eaff"
        sent_color = {"bullish": "#00e5a0", "bearish": "#ff4d6d"}.get(p.get("sentiment", "").lower(), "#f0c040")
        risk_color = {"low": "#00e5a0", "high": "#ff4d6d"}.get(p.get("riskLevel", "").lower(), "#f0c040")

        picks_html += f"""
        <div style="background:#0d1625;border:1px solid {border};border-radius:8px;padding:20px;margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="background:{badge_bg};color:{badge_fg};border-radius:50%;width:26px;height:26px;
                display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:900;flex-shrink:0;">
                #{p.get('rank')}</span>
              <div>
                <div style="font-size:20px;font-weight:900;color:#e0eaff;">{p.get('symbol')}</div>
                <div style="font-size:11px;color:#4a6080;">{p.get('name')}</div>
              </div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:17px;font-weight:700;color:#e0eaff;">{p.get('currentPrice')}</div>
              <div style="font-size:11px;color:{sent_color};">{sem(p.get('sentiment'))} {(p.get('sentiment') or '').upper()}</div>
            </div>
          </div>
          <table style="width:100%;border-collapse:separate;border-spacing:4px 0;margin-bottom:12px;">
            <tr>
              <td style="background:#0a1020;padding:8px;border-radius:4px;text-align:center;">
                <div style="font-size:9px;color:#4a6080;margin-bottom:3px;">ENTRY</div>
                <div style="font-size:12px;font-weight:700;color:#00e5a0;">{p.get('entryPrice')}</div>
              </td>
              <td style="background:#0a1020;padding:8px;border-radius:4px;text-align:center;">
                <div style="font-size:9px;color:#4a6080;margin-bottom:3px;">TARGET</div>
                <div style="font-size:12px;font-weight:700;color:#00aaff;">{p.get('targetPrice')}</div>
              </td>
              <td style="background:#0a1020;padding:8px;border-radius:4px;text-align:center;">
                <div style="font-size:9px;color:#4a6080;margin-bottom:3px;">STOP</div>
                <div style="font-size:12px;font-weight:700;color:#ff4d6d;">{p.get('stopLoss')}</div>
              </td>
              <td style="background:#0a1020;padding:8px;border-radius:4px;text-align:center;">
                <div style="font-size:9px;color:#4a6080;margin-bottom:3px;">UPSIDE</div>
                <div style="font-size:12px;font-weight:700;color:#f0c040;">{p.get('upside')}</div>
              </td>
            </tr>
          </table>
          <div style="background:#0a1020;border-radius:4px;padding:10px;margin-bottom:10px;font-size:12px;color:#a0b8d0;">
            <span style="color:#4a6080;font-size:9px;letter-spacing:1px;">CATALYST </span>{p.get('catalyst')}
          </div>
          <div style="font-size:11px;color:#4a6080;">
            CONFIDENCE: <strong style="color:#e0eaff;">{p.get('confidence')}%</strong> &nbsp;|&nbsp;
            TIMEFRAME: <strong style="color:#a0b8d0;">{p.get('timeframe')}</strong> &nbsp;|&nbsp;
            RISK: <strong style="color:{risk_color};">{p.get('riskLevel')}</strong>
          </div>
        </div>"""

    watchlist = data.get("watchlist", [])
    wl_html = "".join(
        f'<span style="background:#1a2a40;border-radius:4px;padding:4px 10px;font-size:12px;font-weight:700;color:#a0b8d0;margin-right:6px;">{c}</span>'
        for c in watchlist
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#080c14;font-family:'Courier New',monospace;">
<div style="max-width:660px;margin:0 auto;padding:24px 16px;">

  <div style="margin-bottom:24px;">
    <div style="font-size:10px;letter-spacing:4px;color:#00e5a0;margin-bottom:6px;">● SIGNAL ACTIVE</div>
    <h1 style="margin:0 0 4px;font-size:26px;font-weight:900;color:#e0eaff;">CRYPTO SIGNAL ENGINE</h1>
    <div style="font-size:12px;color:#4a6080;">{today}</div>
  </div>

  <div style="background:#0d1625;border:1px solid rgba(0,230,160,0.2);border-radius:8px;padding:18px;margin-bottom:20px;">
    <div style="font-size:10px;letter-spacing:3px;color:#00e5a0;margin-bottom:8px;">MARKET OVERVIEW</div>
    <p style="margin:0 0 10px;line-height:1.7;font-size:13px;color:#c0d8f0;">{data.get('marketSummary')}</p>
    <span style="font-size:12px;color:#4a6080;">BTC: </span>
    <span style="font-size:12px;font-weight:700;color:{'#00e5a0' if btc=='bullish' else '#ff4d6d' if btc=='bearish' else '#f0c040'};">
      {sem(btc)} {btc.upper()}</span>
  </div>

  <div style="font-size:10px;letter-spacing:3px;color:#4a6080;margin-bottom:12px;">TOP 3 PICKS</div>
  {picks_html}

  {"" if not watchlist else f'<div style="background:#0d1625;border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:14px;margin-bottom:16px;"><span style="font-size:10px;letter-spacing:2px;color:#4a6080;margin-right:10px;">WATCHING:</span>{wl_html}</div>'}

  <div style="font-size:10px;color:#2a3a50;line-height:1.6;">
    ⚠ {data.get('disclaimer', 'Not financial advice.')}<br>
    Generated {datetime.now().strftime('%I:%M %p')} · Crypto Signal Engine
  </div>
</div>
</body></html>"""


def send_email(html: str):
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAIL,
        subject=f"🚀 Crypto Signal — {datetime.now().strftime('%b %d, %Y')}",
        html_content=html,
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Email sent to {TO_EMAIL}")


def job():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting daily crypto signal job...")
    try:
        data = get_analysis()
        html = build_html(data)
        send_email(html)
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {e}")


if __name__ == "__main__":
    print(f"Crypto Signal Bot started. Sending daily at {SEND_TIME}.")
    job()  # run once on startup to verify everything works
    schedule.every().day.at(SEND_TIME).do(job)
    while True:
        schedule.run_pending()
        time.sleep(60)

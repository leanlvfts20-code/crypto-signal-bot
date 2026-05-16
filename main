import os
import json
import time
import smtplib
import schedule
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import anthropic

# ── Config from environment variables ──────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GMAIL_ADDRESS     = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TO_EMAIL          = os.environ["TO_EMAIL"]
SEND_TIME         = os.environ.get("SEND_TIME", "15:00")  # default 3:00 PM

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SEARCH_SYSTEM = """You are a crypto market research assistant. Search the web thoroughly.
Search for: current Bitcoin price and 24h trend, top gaining and losing altcoins today,
trending cryptocurrencies on Twitter/X and Reddit, major crypto news from the past 24 hours,
and any upcoming token events or catalysts. Summarize everything you find in detail."""

ANALYSIS_SYSTEM = """You are an expert crypto trader. You will receive raw market research.
Output ONLY a valid JSON object — no markdown, no backticks, no explanation, just raw JSON.

Use exactly this structure (replace example values with real ones from the research):
{"marketSummary":"2-3 sentences about current conditions","btcSentiment":"bullish","topPicks":[{"rank":1,"symbol":"BTC","name":"Bitcoin","currentPrice":"$65,000","entryPrice":"$64,500 - $65,000","targetPrice":"$67,500","stopLoss":"$63,000","upside":"+4%","confidence":82,"timeframe":"Tonight / Tomorrow","catalyst":"reason for expected move","sentiment":"bullish","riskLevel":"Medium"},{"rank":2,"symbol":"ETH","name":"Ethereum","currentPrice":"$3,200","entryPrice":"$3,150 - $3,200","targetPrice":"$3,400","stopLoss":"$3,050","upside":"+6%","confidence":75,"timeframe":"Tonight / Tomorrow","catalyst":"reason","sentiment":"bullish","riskLevel":"Medium"},{"rank":3,"symbol":"SOL","name":"Solana","currentPrice":"$150","entryPrice":"$148 - $151","targetPrice":"$162","stopLoss":"$143","upside":"+8%","confidence":70,"timeframe":"Tonight / Tomorrow","catalyst":"reason","sentiment":"bullish","riskLevel":"High"}],"watchlist":["DOGE","PEPE","ARB"],"disclaimer":"Not financial advice. Always do your own research.","generatedAt":"ISO-timestamp"}

Output ONLY the JSON. Nothing else."""


def run_agentic_search(user_message: str) -> str:
    """Runs multi-turn agentic loop with web search until end_turn."""
    messages = [{"role": "user", "content": user_message}]

    for _ in range(10):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SEARCH_SYSTEM,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            return "".join(b.text for b in response.content if hasattr(b, "text"))

        if response.stop_reason == "tool_use":
            tool_results = [
                {
                    "type": "tool_result",
                    "tool_use_id": b.id,
                    "content": "Search executed successfully.",
                }
                for b in response.content
                if b.type == "tool_use"
            ]
            messages.append({"role": "user", "content": tool_results})
            continue

        # Fallback
        text = "".join(b.text for b in response.content if hasattr(b, "text"))
        if text:
            return text
        raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")

    raise RuntimeError("Search loop exceeded max rounds.")


def get_analysis() -> dict:
    """Step 1: search. Step 2: structured JSON analysis."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Running web search...")

    research = run_agentic_search(
        f"Today is {today}. Search for: current Bitcoin price and direction, "
        "top gaining/losing altcoins today, trending coins on crypto Twitter and Reddit, "
        "major crypto news last 24 hours, any token unlocks or exchange listings. "
        "Give me a thorough detailed summary."
    )

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating signal picks...")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=ANALYSIS_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Here is the latest crypto market research:\n\n{research}\n\nOutput the JSON analysis now."
        }],
    )

    raw = "".join(b.text for b in response.content if hasattr(b, "text")).strip()

    # Extract JSON from response
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in response: {raw[:300]}")

    return json.loads(raw[start:end])


def sentiment_emoji(s: str) -> str:
    s = (s or "").lower()
    if s == "bullish": return "🟢"
    if s == "bearish": return "🔴"
    return "🟡"


def risk_emoji(r: str) -> str:
    r = (r or "").lower()
    if r == "low": return "🟢 Low"
    if r == "high": return "🔴 High"
    return "🟡 Medium"


def build_email_html(data: dict) -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")
    picks_html = ""

    for pick in data.get("topPicks", []):
        rank = pick.get("rank", "")
        sym = pick.get("symbol", "")
        name = pick.get("name", "")
        price = pick.get("currentPrice", "—")
        entry = pick.get("entryPrice", "—")
        target = pick.get("targetPrice", "—")
        stop = pick.get("stopLoss", "—")
        upside = pick.get("upside", "—")
        conf = pick.get("confidence", "—")
        catalyst = pick.get("catalyst", "—")
        timeframe = pick.get("timeframe", "—")
        sentiment = pick.get("sentiment", "neutral")
        risk = pick.get("riskLevel", "Medium")
        border = "#00e5a0" if rank == 1 else "#1e2d45"

        picks_html += f"""
        <div style="background:#0d1625;border:1px solid {border};border-radius:8px;padding:20px;margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <div>
              <span style="background:{'#00e5a0' if rank==1 else '#1a2a40'};color:{'#080c14' if rank==1 else '#a0b8d0'};
                border-radius:50%;width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;
                font-size:11px;font-weight:900;margin-right:10px;">#{rank}</span>
              <span style="font-size:22px;font-weight:900;color:#e0eaff;">{sym}</span>
              <span style="font-size:13px;color:#4a6080;margin-left:8px;">{name}</span>
            </div>
            <div style="text-align:right;">
              <div style="font-size:18px;font-weight:700;color:#e0eaff;">{price}</div>
              <div style="font-size:11px;color:{'#00e5a0' if sentiment=='bullish' else '#ff4d6d' if sentiment=='bearish' else '#f0c040'};">
                {sentiment_emoji(sentiment)} {sentiment.upper()}
              </div>
            </div>
          </div>

          <table style="width:100%;border-collapse:collapse;margin-bottom:14px;">
            <tr>
              <td style="padding:8px;background:#0a1020;border-radius:4px;text-align:center;width:25%;">
                <div style="font-size:9px;color:#4a6080;letter-spacing:1px;margin-bottom:4px;">ENTRY ZONE</div>
                <div style="font-size:13px;font-weight:700;color:#00e5a0;">{entry}</div>
              </td>
              <td style="width:4px;"></td>
              <td style="padding:8px;background:#0a1020;border-radius:4px;text-align:center;width:25%;">
                <div style="font-size:9px;color:#4a6080;letter-spacing:1px;margin-bottom:4px;">TARGET</div>
                <div style="font-size:13px;font-weight:700;color:#00aaff;">{target}</div>
              </td>
              <td style="width:4px;"></td>
              <td style="padding:8px;background:#0a1020;border-radius:4px;text-align:center;width:25%;">
                <div style="font-size:9px;color:#4a6080;letter-spacing:1px;margin-bottom:4px;">STOP LOSS</div>
                <div style="font-size:13px;font-weight:700;color:#ff4d6d;">{stop}</div>
              </td>
              <td style="width:4px;"></td>
              <td style="padding:8px;background:#0a1020;border-radius:4px;text-align:center;width:25%;">
                <div style="font-size:9px;color:#4a6080;letter-spacing:1px;margin-bottom:4px;">UPSIDE</div>
                <div style="font-size:13px;font-weight:700;color:#f0c040;">{upside}</div>
              </td>
            </tr>
          </table>

          <div style="background:#0a1020;border-radius:4px;padding:10px 14px;margin-bottom:10px;">
            <span style="font-size:9px;color:#4a6080;letter-spacing:2px;">CATALYST: </span>
            <span style="font-size:13px;color:#a0b8d0;">{catalyst}</span>
          </div>

          <div style="display:flex;gap:20px;font-size:11px;color:#4a6080;">
            <span>CONFIDENCE: <strong style="color:#e0eaff;">{conf}%</strong></span>
            <span>TIMEFRAME: <strong style="color:#a0b8d0;">{timeframe}</strong></span>
            <span>RISK: <strong>{risk_emoji(risk)}</strong></span>
          </div>
        </div>
        """

    watchlist = data.get("watchlist", [])
    watchlist_html = "".join(
        f'<span style="background:#1a2a40;border-radius:4px;padding:4px 12px;font-size:13px;font-weight:700;color:#a0b8d0;margin-right:8px;">{c}</span>'
        for c in watchlist
    )

    btc_sent = data.get("btcSentiment", "neutral")
    summary = data.get("marketSummary", "")

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#080c14;font-family:'Courier New',monospace;">
  <div style="max-width:680px;margin:0 auto;padding:24px 16px;">

    <!-- Header -->
    <div style="margin-bottom:28px;">
      <div style="font-size:10px;letter-spacing:4px;color:#00e5a0;margin-bottom:8px;">● SIGNAL ACTIVE</div>
      <h1 style="margin:0 0 6px;font-size:28px;font-weight:900;color:#e0eaff;letter-spacing:-1px;">
        CRYPTO SIGNAL ENGINE
      </h1>
      <div style="font-size:12px;color:#4a6080;letter-spacing:1px;">{today}</div>
    </div>

    <!-- Market Overview -->
    <div style="background:#0d1625;border:1px solid rgba(0,230,160,0.25);border-radius:8px;padding:20px;margin-bottom:24px;">
      <div style="font-size:10px;letter-spacing:3px;color:#00e5a0;margin-bottom:10px;">MARKET OVERVIEW</div>
      <p style="margin:0 0 12px;line-height:1.7;font-size:14px;color:#c0d8f0;">{summary}</p>
      <span style="font-size:12px;color:#4a6080;">BTC SENTIMENT: </span>
      <span style="font-size:12px;font-weight:700;color:{'#00e5a0' if btc_sent=='bullish' else '#ff4d6d' if btc_sent=='bearish' else '#f0c040'};">
        {sentiment_emoji(btc_sent)} {btc_sent.upper()}
      </span>
    </div>

    <!-- Top 3 Picks -->
    <div style="font-size:10px;letter-spacing:3px;color:#4a6080;margin-bottom:14px;">TOP 3 PICKS</div>
    {picks_html}

    <!-- Watchlist -->
    {"" if not watchlist else f'''
    <div style="background:#0d1625;border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:16px;margin-bottom:20px;">
      <span style="font-size:10px;letter-spacing:3px;color:#4a6080;margin-right:12px;">ALSO WATCHING:</span>
      {watchlist_html}
    </div>
    '''}

    <!-- Footer -->
    <div style="font-size:10px;color:#2a3a50;margin-top:16px;line-height:1.6;">
      ⚠ {data.get("disclaimer", "Not financial advice.")}<br>
      Generated at {datetime.now().strftime("%I:%M %p")} · Crypto Signal Engine
    </div>

  </div>
</body>
</html>
"""


def send_email(html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚀 Crypto Signal — {datetime.now().strftime('%b %d, %Y')}"
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = TO_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, TO_EMAIL, msg.as_string())

    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Email sent to {TO_EMAIL}")


def job():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting daily crypto signal job...")
    try:
        data = get_analysis()
        html = build_email_html(data)
        send_email(html)
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {e}")


if __name__ == "__main__":
    print(f"Crypto Signal Bot started. Will send daily at {SEND_TIME}.")
    # Run once immediately on startup so you can verify it works
    job()
    # Then schedule daily
    schedule.every().day.at(SEND_TIME).do(job)
    while True:
        schedule.run_pending()
        time.sleep(60)

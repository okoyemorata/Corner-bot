"""
============================================
  ETLUX CORNER ALERT BOT
  Telegram: @Etlux_fx
  Rule: 70+ mins, corners <= 6, alert fired
  Platform: 1xBet Nigeria
============================================
"""

import os
import time
import requests
from datetime import datetime

# ─────────────────────────────────────────
#  CONFIG — fill these in before running
# ─────────────────────────────────────────
API_FOOTBALL_KEY = "YOUR_API_FOOTBALL_KEY"   # from api-football.com
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # from @BotFather on Telegram
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"   # your personal chat ID

# ─────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────
CORNER_THRESHOLD = 6        # corners must be <= this at 70+ mins
MINUTE_TRIGGER = 70         # alert fires from this minute onward
MAX_MINUTE = 85             # stop alerting after this (too late)
POLL_INTERVAL = 60          # check every 60 seconds (API updates every minute)
ALERT_COOLDOWN = 900        # don't re-alert same game for 15 minutes (seconds)

# ─────────────────────────────────────────
#  TRACKING — prevents duplicate alerts
# ─────────────────────────────────────────
alerted_fixtures = {}  # {fixture_id: timestamp_of_last_alert}


def log(msg):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}")


def send_telegram(message):
    """Send alert to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            log("✅ Telegram alert sent")
        else:
            log(f"❌ Telegram error: {r.text}")
    except Exception as e:
        log(f"❌ Telegram exception: {e}")


def get_live_fixtures():
    """Fetch all live football fixtures from API-Football."""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-apisports-key": API_FOOTBALL_KEY
    }
    params = {"live": "all"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        data = r.json()
        return data.get("response", [])
    except Exception as e:
        log(f"❌ API error fetching fixtures: {e}")
        return []


def get_fixture_stats(fixture_id):
    """Fetch live statistics for a specific fixture."""
    url = "https://v3.football.api-sports.io/fixtures/statistics"
    headers = {
        "x-apisports-key": API_FOOTBALL_KEY
    }
    params = {"fixture": fixture_id}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        data = r.json()
        return data.get("response", [])
    except Exception as e:
        log(f"❌ API error fetching stats for {fixture_id}: {e}")
        return []


def extract_corners(stats):
    """Extract total corners from both teams' statistics."""
    total_corners = 0
    for team_stats in stats:
        for stat in team_stats.get("statistics", []):
            if stat["type"] == "Corner Kicks":
                val = stat["value"]
                if val and val != "None":
                    try:
                        total_corners += int(val)
                    except:
                        pass
    return total_corners


def can_alert(fixture_id):
    """Check if we haven't alerted this fixture recently."""
    now = time.time()
    last = alerted_fixtures.get(fixture_id, 0)
    return (now - last) > ALERT_COOLDOWN


def build_alert(fixture, minute, corners):
    """Build the Telegram alert message."""
    home = fixture["teams"]["home"]["name"]
    away = fixture["teams"]["away"]["name"]
    league = fixture["league"]["name"]
    country = fixture["league"]["country"]
    score_home = fixture["goals"]["home"] or 0
    score_away = fixture["goals"]["away"] or 0

    remaining = 90 - minute
    max_possible = corners + remaining  # rough max if 1 corner per minute

    message = (
        f"🚨 <b>CORNER ALERT — 1xBet</b> 🚨\n\n"
        f"⚽ <b>{home} vs {away}</b>\n"
        f"🏆 {league} ({country})\n"
        f"⏱ Minute: <b>{minute}'</b>\n"
        f"📐 Score: {score_home} - {score_away}\n\n"
        f"📌 <b>Corners so far: {corners}</b>\n"
        f"➕ Corners + 3 = <b>{corners + 3}</b>\n"
        f"⏳ ~{remaining} mins remaining\n\n"
        f"✅ <b>ACTION: Go to 1xBet → Find this game → "
        f"Corners → Check UNDER line\n"
        f"If line is {corners + 3}.5 or higher → PLACE BET ✅\n"
        f"If line is {corners + 3} or lower → SKIP ❌</b>\n\n"
        f"💰 Stake: <b>40% of available balance</b>\n"
        f"🎯 Odds target: 1.7 or better"
    )
    return message


def run_bot():
    log("🤖 Etlux Corner Bot started")
    log(f"📡 Polling every {POLL_INTERVAL}s | Trigger: {MINUTE_TRIGGER}+ mins | Max corners: {CORNER_THRESHOLD}")
    send_telegram(
        "🤖 <b>Corner Bot is LIVE</b>\n\n"
        "Monitoring all live football games.\n"
        f"Alert fires when: ⏱ 70+ mins & 📐 corners ≤ {CORNER_THRESHOLD}\n"
        "You'll get notified instantly. Go place it on 1xBet! 🚀"
    )

    while True:
        log("🔍 Scanning live fixtures...")
        fixtures = get_live_fixtures()
        log(f"   Found {len(fixtures)} live games")

        for fixture in fixtures:
            fixture_id = fixture["fixture"]["id"]
            minute = fixture["fixture"]["status"].get("elapsed")

            # Skip if minute data not available
            if minute is None:
                continue

            # Only check in our target window
            if minute < MINUTE_TRIGGER or minute > MAX_MINUTE:
                continue

            # Skip if we already alerted recently
            if not can_alert(fixture_id):
                continue

            # Fetch live stats for this game
            stats = get_fixture_stats(fixture_id)
            corners = extract_corners(stats)

            home = fixture["teams"]["home"]["name"]
            away = fixture["teams"]["away"]["name"]
            log(f"   ⚽ {home} vs {away} | Min: {minute}' | Corners: {corners}")

            # FIRE ALERT if corners meet threshold
            if corners <= CORNER_THRESHOLD:
                log(f"🚨 SIGNAL FOUND — {home} vs {away} | {corners} corners at {minute}'")
                alert_msg = build_alert(fixture, minute, corners)
                send_telegram(alert_msg)
                alerted_fixtures[fixture_id] = time.time()

        log(f"⏸ Sleeping {POLL_INTERVAL}s...\n")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_bot()

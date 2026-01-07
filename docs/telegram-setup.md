# Telegram Bot Setup - EVE Co-Pilot

Complete guide to set up Telegram bot integration for combat alerts and battle reports.

## Prerequisites

- Telegram channel: `infinimind-eve`
- Bot: `@infinimind_eve_bot`
- Bot Token: Already configured in `config.py`

## Step 1: Create Channels

Create two channels in your Telegram channel:

1. **alerts** - For real-time combat hotspot alerts
2. **reports** - For 24h battle reports (every 10 minutes)

**How to create channels:**
1. Open Telegram
2. Go to your channel `infinimind-eve`
3. Create two sub-channels or topics named `alerts` and `reports`

**Alternative:** Create separate channels:
- `infinimind-eve-alerts`
- `infinimind-eve-reports`

## Step 2: Add Bot as Admin

1. Go to each channel
2. Add `@infinimind_eve_bot` as administrator
3. Give bot permissions to:
   - Post messages
   - Edit messages

## Step 3: Get Channel IDs

Run the helper script to get your channel IDs:

```bash
cd /home/cytrex/eve_copilot
python3 get_telegram_channel_ids.py
```

**If no updates found:**
1. Send a test message to each channel
2. Tag the bot: `@infinimind_eve_bot test`
3. Run the script again

**Expected output:**
```
📢 Channel: alerts
   ID: -1001234567890
   Username: @infinimind_eve_alerts

📢 Channel: reports
   ID: -1002345678901
   Username: @infinimind_eve_reports
```

## Step 4: Update Configuration

Edit `/home/cytrex/eve_copilot/config.py`:

```python
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"  # Get from @BotFather
TELEGRAM_ALERTS_CHANNEL = "-1001234567890"  # Replace with your alerts channel ID
TELEGRAM_REPORTS_CHANNEL = "-1002345678901"  # Replace with your reports channel ID
TELEGRAM_ENABLED = True
```

**Or use channel username:**
```python
TELEGRAM_ALERTS_CHANNEL = "@infinimind_eve_alerts"
TELEGRAM_REPORTS_CHANNEL = "@infinimind_eve_reports"
```

## Step 5: Restart Zkillboard Listener

Restart the zkillboard live listener to apply changes:

```bash
screen -S zkill -X quit
screen -dmS zkill bash -c "python3 -m jobs.zkill_live_listener --verbose > /tmp/zkill_telegram.log 2>&1"
```

## Step 6: Set Up Battle Report Cron Job

Add cron job to send 24h battle report every 10 minutes:

```bash
crontab -e
```

Add this line:
```
*/10 * * * * /home/cytrex/eve_copilot/jobs/cron_telegram_report.sh
```

**Verify cron job:**
```bash
crontab -l | grep telegram
```

## Step 7: Test Integration

### Test Alert Sending

```bash
cd /home/cytrex/eve_copilot
python3 << 'EOF'
import asyncio
from telegram_service import telegram_service

async def test():
    message = "🧪 **Test Alert**\n\nThis is a test message from EVE Co-Pilot!"
    result = await telegram_service.send_alert(message)
    print(f"Alert sent: {result}")

asyncio.run(test())
EOF
```

### Test Report Sending

```bash
python3 jobs/telegram_battle_report.py
```

Check your Telegram channels - you should see the messages!

## How It Works

### Combat Alerts (Real-time)

When a hotspot is detected (5+ kills in 5 minutes):
- Enhanced alert is created with:
  - Danger level (multi-factor scoring)
  - Gate camp detection
  - Top 5 expensive ships destroyed
  - Involved corps/alliances
- Sent to **alerts** channel
- Cooldown: 10 minutes per system (prevents spam)

**Example Alert:**
```
⚠️ Combat Hotspot Detected

📍 Location: Rancer (0.4) - Sinq Laison
🔥 Activity: 8 kills in 5 minutes
💰 Total Value: 247.5M ISK (avg 30.9M/kill)
🎯 Danger Level: 🟠 HIGH (9/12 pts)
🚨 Pattern: Bubble Camp (75% confidence)

⚔️ Attacking Forces:
   • Pandemic Legion (12 kills)

💀 Top 5 Most Expensive Losses:
`1.` Eris - 45.2M ISK

⚠️ HIGH ALERT - Active combat zone
```

### Battle Reports (Every 10 minutes)

24h battle report with:
- Global summary (total kills, ISK destroyed)
- Top 5 regions by activity
- Top systems, ships, and destroyed items per region

**Example Report:**
```
⚔️ 24H BATTLE REPORT

🌌 Galactic Summary
• Total Kills: 401
• ISK Destroyed: 78.8B ISK
• Hottest Region: Metropolis

📍 Top 5 Regions

1. Metropolis
• Kills: 44
• ISK: 2,364M
• Top System: Bei (9 kills)
• Hot Items:
  - Hail S: 11,339x
  - Mjolnir Fury Heavy Missile: 10,946x
```

## Monitoring

### Check Alert Logs

```bash
tail -f /tmp/zkill_telegram.log
```

### Check Report Logs

```bash
tail -f /home/cytrex/eve_copilot/logs/telegram_report.log
```

### Check Cron Jobs

```bash
crontab -l
```

## Troubleshooting

### No messages received

1. Check channel IDs are correct in `config.py`
2. Verify bot is admin in channels
3. Check logs for errors

### Bot not responding

1. Verify bot token is correct
2. Check network connectivity
3. Test with `get_telegram_channel_ids.py`

### Alerts not sending

1. Check zkillboard listener is running: `ps aux | grep zkill_live_listener`
2. Check logs: `tail -f /tmp/zkill_telegram.log`
3. Verify `TELEGRAM_ENABLED = True` in config.py

### Reports not sending

1. Check cron job is active: `crontab -l`
2. Check report log: `tail -f logs/telegram_report.log`
3. Verify channel ID is correct

## Disabling Discord (Optional)

If you want to use only Telegram, edit `config.py`:

```python
WAR_DISCORD_ENABLED = False  # Disable Discord alerts
TELEGRAM_ENABLED = True      # Keep Telegram enabled
```

## Next Steps

- Monitor your Telegram channels for alerts
- Adjust thresholds in `zkillboard_live_service.py` if needed
- Set up additional channels for different alert types

---

**Last Updated:** 2026-01-06

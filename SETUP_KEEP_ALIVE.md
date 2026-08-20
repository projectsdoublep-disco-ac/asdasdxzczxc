# Render Bot — Keep-Alive Setup Guide

## How It Works

Your bot now runs on **Render's free tier web service** (no spin-down), but we prevent any inactivity by:

1. **Flask HTTP server** running on port 10000 (in-process with your bot)
2. **Uptime Robot** (free) pinging every 5 minutes to keep it awake

---

## ⚡ Setup Steps

### 1. Deploy to Render (Same as Before)
- Unzip updated files to GitHub repo
- Push to GitHub
- Go to **render.com** → **New +** → **Web Service**
- Select repo, deploy
- Wait for "Flask keep-alive server started on port 10000" in logs ✅

### 2. Get Your Render URL
After deploy completes:
- In Render dashboard, find your service
- Copy the URL at the top (looks like: `https://telegram-bot-xyz.onrender.com`)

### 3. Set Up Uptime Robot (Free Tier)
1. Go to [uptimerobot.com](https://uptimerobot.com)
2. Sign up (free) → verify email
3. Click **+ Add New Monitor**
4. **Monitor Type**: `HTTP(s)`
5. **Friendly Name**: `Telegram Bot Keep-Alive`
6. **URL**: `https://telegram-bot-xyz.onrender.com/health` (paste your Render URL + `/health`)
7. **Monitoring Interval**: `5 minutes` (every 5 min it pings, keeps bot awake)
8. Click **Create Monitor**
9. ✅ Done!

Now Uptime Robot pings your bot every 5 minutes → Render sees incoming traffic → never spins down.

---

## 📊 What's Happening

- **Your bot**: Runs Telegram bot + Flask server simultaneously
- **Flask endpoints**:
  - `/health` — returns `ok` (Uptime Robot pings this)
  - `/` — returns `Telegram bot is running`
- **Uptime Robot**: Pings `/health` every 5 min (free tier)
- **Result**: Your bot stays online 24/7, costs $0/month

---

## 🔍 Verify It's Working

1. Go to your Render URL in browser:
   - `https://telegram-bot-xyz.onrender.com/` should show `Telegram bot is running`
   - `https://telegram-bot-xyz.onrender.com/health` should show `ok`

2. Check Render logs:
   - You should see `Flask keep-alive server started on port 10000`
   - Bot commands work normally in Telegram

3. Check Uptime Robot dashboard:
   - Green checkmark = monitor is pinging successfully

---

## 📝 Files Changed

- **sjs.py**: Added Flask app + background thread
- **requirements.txt**: Added Flask + Werkzeug
- **render.yaml**: Added PORT env var
- **SETUP_KEEP_ALIVE.md**: This file

No changes to your bot logic — it works exactly the same, just with HTTP endpoints.

---

## ❌ Troubleshooting

| Issue | Fix |
|-------|-----|
| Flask fails to start | Check `requirements.txt` has Flask & Werkzeug |
| Uptime Robot shows red | Check Render URL is correct, service is running |
| Bot stops after 15 min | Uptime Robot pings might not be active; re-verify monitor |
| Port conflict | Flask uses port 10000, should be fine on Render |

---

## 🎉 You're Done!

Bot runs free forever, auto-deploys on GitHub push, never spins down.

Questions? Check Render logs for errors.

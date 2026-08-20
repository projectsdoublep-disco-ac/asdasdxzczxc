# Telegram Bot — Render Deployment Guide

## ⚡ Quick Start (5 minutes)

### 1. **Prepare Your GitHub Repo**
   - Go to your GitHub repo (where you already have `sjs.py`)
   - Add these files to the repo root:
     - `requirements.txt` (already in this folder)
     - `render.yaml` (already in this folder)
     - `Procfile` (already in this folder)
   - `sjs.py` stays where it is ✅
   - Push to GitHub

### 2. **Connect Render to GitHub**
   - Go to [render.com](https://render.com) and sign in (or create account)
   - Click **New +** → **Web Service**
   - **Connect Repository**: Select your GitHub repo (authorize if first time)
   - **Repository Name**: Select the repo with your bot code
   - Click **Connect**

### 3. **Configure Render Service**
   - **Name**: `telegram-bot` (anything you like)
   - **Environment**: Select **Python 3.12**
   - **Build Command**: Leave blank (it auto-reads `render.yaml`)
   - **Start Command**: Leave blank (it auto-reads `render.yaml`)
   - **Plan**: **Free** ✅

### 4. **Environment Variables**
   - No additional env vars needed — your tokens are hardcoded in `sjs.py`
   - ⚠️ **IMPORTANT**: In production, move them to Render env vars (see "Security Note" below)

### 5. **Deploy**
   - Click **Create Web Service**
   - Watch the build log — should take 1–2 minutes
   - When logs show "Bot started" → ✅ **Live!**

---

## 🔄 Auto-Deploy on Push
Once connected, every time you push to GitHub (any branch), Render auto-redeploys.
- Push → GitHub → Render auto-pulls & restarts → Bot back online

---

## ⚠️ Free Tier Notes

### **Spin-Down After Inactivity**
Free Render web services **spin down after 15 minutes of no incoming requests**. When a request comes in, they wake up (adds ~30 second cold start).

**Solution for your Telegram bot:**
Since your bot uses **long-polling** (not webhooks), Render sees it as inactive and will spin down. To fix:

**Option A (Recommended):** Use a **free Background Worker** instead
- Render's free tier includes background workers (always-on)
- In Render dashboard: **New → Background Worker**
- Connect the same repo, select **worker** type instead of web service
- Takes same deploy config, no changes needed

**Option B:** Add a simple HTTP endpoint ping
- The bot already runs `app.run_polling()` which is a blocking loop
- Use a separate service (like Uptimerobot, free tier) to ping an HTTP endpoint every 10 minutes to keep it awake
- More complex, less reliable

**I recommend Option A** — switch to a Background Worker, zero extra cost.

---

## 🔒 Security Note

Your tokens are currently **hardcoded in sjs.py**:
```python
TELEGRAM_TOKEN = "8807771466:AAFQbXlaSQb2Odeh-bJVoXg0IXnAmYHhYww"
AUTH_TOKEN = "eyJ0eXAi..."
```

**Before deploying to production**, replace with environment variables:

1. In Render dashboard, go to **Environment** tab
2. Add:
   ```
   TELEGRAM_TOKEN = your_actual_token
   AUTH_TOKEN = your_actual_token
   MEDIA_USER_TOKEN = your_token
   TREBEL_TOKEN = your_token
   ```
3. In `sjs.py`, change:
   ```python
   TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "default_fallback")
   AUTH_TOKEN = os.getenv("AUTH_TOKEN", "default_fallback")
   # etc.
   ```

---

## 📊 Monitoring & Logs

In Render dashboard:
- **Logs tab**: See real-time bot output
- **Metrics tab**: CPU, memory, restart count
- **Events tab**: Deployment history

---

## ❌ Troubleshooting

| Issue | Fix |
|-------|-----|
| Bot offline after 15 min inactivity | Switch to Background Worker (Option A above) |
| "ModuleNotFoundError: No module named X" | Check `requirements.txt` lists all imports |
| Bot starts but crashes | Check logs, look for exceptions |
| No auto-deploy on GitHub push | In Render: click **Repo** in service settings, re-connect |

---

## 🎉 Done!
Your bot is live 24/7 on Render, auto-deploys on every GitHub push, and costs **$0/month** on free tier.

Questions? Reply in Telegram or check Render docs: https://render.com/docs

# 🚀 NSE Swing & Momentum Screener

A free, automated, open-source Swing Trading Web Screener for NSE stocks. Hosted 100% free on **GitHub Pages** with automated daily updates via **GitHub Actions**.

Inspired by quantitative momentum screening and the **RichRoad Trading System**.

---

## 🎯 Supported Swing Scans & Setups

| Setup Tag | Name | Criteria / Philosophy |
| :--- | :--- | :--- |
| **🔥 CB** | **Committed Buyers** | +2.5% to +3% gain from Open, CLV $\ge 0.70$ (top close), body $\ge 55\%$, Volume $\ge 1.75\times$ 20-SMA. Pure institutional buying. |
| **🎯 M10** | **M10 Pullback Touch** | Strong trend ($10 > 20 > 50\text{ EMA}$), price pulling back to touch 10 EMA on low volume. High reward/risk entry. |
| **🌀 TANGLE** | **EMA Tangle Contraction** | 10 EMA & 50 EMA coiled within 6% near 200 EMA with volume dry-up. Coiled spring setup. |
| **🚀 52W_HIGH** | **52W High Breakout** | Price within 2.5% of 52-Week High or new high with volume expansion ($> 1.3\times$). |
| **📈 HIGH_RS** | **RS Leader (Outperformer)** | Strong Relative Strength (RS) outperforming Nifty 50 over 1M (+5%) and 3M (+10%). |
| **⚡ VOL_SHOCK** | **Volume Shocker** | Volume $\ge 3.0\times$ 20-Day SMA with green candle (+2%+ gain). Heavy accumulation. |

---

## 📱 Features

- **Zero Broker Dependency**: Runs on open data pipelines — no broker API limits, no daily expired tokens.
- **1-Click Charts**: Instant buttons for TradingView and FYERS Web charts.
- **Embedded Chart Preview**: Click any row to preview the daily candlestick chart without leaving the page.
- **Automated Daily Scan**: GitHub Actions automatically runs every trading day at 4:00 PM IST (10:30 UTC), updates `data.json`, and updates the website.
- **Mobile Friendly**: Dark theme UI that works seamlessly on mobile, tablet, and PC.

---

## 🛠️ How to Deploy to GitHub Pages in 2 Minutes

### Step 1: Create a GitHub Repository
1. Log in to [GitHub](https://github.com).
2. Click **New Repository** (e.g. name it `nse-swing-screener`).
3. Set visibility to **Public**.

### Step 2: Push this Folder to your Repository
In your terminal, navigate to `F:\intraday_scanner\swing_screener`:
```bash
cd F:\intraday_scanner\swing_screener
git init
git add .
git commit -m "Initial commit: NSE Swing Screener"
git branch -M main
git remote add origin https://github.com/<YOUR-GITHUB-USERNAME>/nse-swing-screener.git
git push -u origin main
```

### Step 3: Enable GitHub Pages
1. Go to your repo on GitHub: **Settings** -> **Pages**.
2. Under **Build and deployment** -> **Source**, select **Deploy from a branch**.
3. Select branch: `main` and folder `/ (root)`, then click **Save**.
4. In 1 minute, your screener will be LIVE at:
   `https://<YOUR-GITHUB-USERNAME>.github.io/nse-swing-screener/`

### Step 4: Enable Automated Daily Scans
1. In your GitHub repo, go to **Settings** -> **Actions** -> **General**.
2. Under **Workflow permissions**, select **Read and write permissions** and click **Save**.
3. Done! GitHub Actions will now automatically update your screener every trading day at 4:00 PM IST.


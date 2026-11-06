"""
NSE Swing Trading & Momentum Screener Engine
=============================================
Scans NSE stocks for non-intraday Swing & Positional setups:
  1. Committed Buyers (CB) - Institutional Accumulation (RichRoad)
  2. M10 Setup (Pullback to 10 EMA in strong trend)
  3. Core Contraction & EMA Tangle (10/50 coiled near 200 EMA)
  4. 52-Week High Breakout (Within 2.5% or fresh high with volume)
  5. High Relative Strength (RS Leader vs Nifty 50)
  6. Volume Shocker (Volume > 3.0x 20-SMA)

Generates data.json for the GitHub Pages static web app.
Zero broker login required - runs 100% automated on GitHub Actions.
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import pytz
import numpy as np
import pandas as pd
import yfinance as yf

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("swing_screener")

# Target Universe: Liquid NSE Equities (Nifty 500 / Mid-Small Cap Momentum candidates)
DEFAULT_TICKERS = [
    # Nifty 50 Core
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "BHARTIARTL", "ITC", "SBIN",
    "LICI", "HINDUNILVR", "LT", "BAJFINANCE", "HCLTECH", "MARUTI", "SUNPHARMA",
    "ADANIENT", "NTPC", "KOTAKBANK", "TITAN", "ONGC", "AXISBANK",
    "ADANIPORTS", "COALINDIA", "POWERGRID", "M&M", "BAJAJFINSV", "TATASTEEL",
    # Leading Momentum & Growth Stocks
    "BEL", "HAL", "VBL", "TRENT", "DIXON", "POLYCAB", "KALYANKJIL", "BOMDYEING",
    "SUZLON", "JIOFIN", "PERSISTENT", "COFORGE", "KPITTECH", "TATAELXSI",
    "MAZDOCK", "COCHINSHIP", "GRSE", "BHEL", "RVNL", "IRFC", "RAILTEL", "IRCON",
    "PFC", "RECLTD", "IREDA", "HUDCO", "NBCC", "MOTHERSON", "BHARATFORG",
    "CHAMBLFERT", "FACT", "RCF", "NATIONALUM", "HINDCOPPER", "VEDL", "NMDC",
    "SAIL", "JINDALSTEL", "JSWSTEEL", "APLAPOLLO", "ASTRAL", "SUPREMEIND",
    "CUMMINSIND", "SIEMENS", "ABB", "CGPOWER", "BOSCHLTD", "THERMAX", "KEI",
    "SCHNEIDER", "KEC", "VOLTAS", "BLUESTARCO", "HAVELLS", "CROMPTON",
    # Defense, Aerospace, Electronics & EMS
    "KAYNES", "DATAPATTNS", "NETWEB", "TEJASNET", "CYIENT", "TATACOMM", "OFSS",
    "HBLPOWER", "TITAGARH", "JWL", "TEXRAIL", "RITES", "CONCOR", "TARSONS",
    # Exchanges, Broking & Financials
    "BSE", "MCX", "CDSL", "ANGELONE", "MOTILALOFS", "CAMS", "KFINTECH", "CHOLAFIN",
    "SHRIRAMFIN", "M&MFIN", "POONAWALLA", "MANAPPURAM", "MUTHOOTFIN", "L&TFH",
    "ABCAPITAL", "IDFCFIRSTB", "FEDERALBNK", "AUBANK", "BANDHANBNK", "BANKBARODA",
    "PNB", "CANBK", "UNIONBANK", "INDIANB",
    # Energy, Power & Green Tech
    "NHPC", "SJVN", "TATAPOWER", "ADANIGREEN", "JSWENERGY", "TORNTPOWER", "CESC",
    "IEX", "INOXWIND", "GENSOL",
    # Pharma, Chemicals, Hospitals & Diagnostics
    "LUPIN", "CIPLA", "DRREDDY", "DIVISLAB", "AUROPHARMA", "MANKIND", "TORNTPHARM",
    "GLENMARK", "ZYDUSLIFE", "ALKEM", "APOLLOHOSP", "MAXHEALTH", "FORTIS",
    "MEDANTA", "LALPATHLAB", "METROPOLIS", "SYNGENE", "PIIND", "DEEPAKNTR",
    "TATACHEM", "SRF", "NAVINFLUOR", "FLUOROCHEM", "ATUL", "AARTIIND",
    "BIOCON", "NATCOPHARM", "IPCALAB", "JBCHEPHARM", "ERIS", "AJANTPHARM", "GRANULES",
    # Consumer, Retail, Textiles & Auto
    "DMART", "V2RETAIL", "RAYMOND", "GOKEX", "KPRMILL", "PAGEIND",
    "ETHOSLTD", "SENCO", "THOMASCOOK", "INDIGO", "EIHOTEL",
    "TAJGVK", "DEVYANI", "JUBLFOOD", "WESTLIFE", "SAPPHIRE", "RADICO", "TIINDIA",
    "ESCORTS", "TVSMOTOR", "BAJAJ-AUTO", "HEROMOTOCO", "ASHOKLEY", "EICHERMOT",
    "CEATLTD", "APOLLOTYRE", "MRF", "BALKRISIND", "EXIDEIND", "SONACOMS", "UNOMINDA",
    # High Momentum Mid & Small Caps (Active Movers)
    "WABAG", "VRLLOG", "APLLTD", "WINDLAS", "TVSELECT", "HPL", "TEXINFRA",
    "AEGISVOPAK", "RAMKY", "TTML", "MTNL", "TTKPRESTIG", "KALAMANDIR", "AGIIL",
    "SAILIFE", "IKIO", "ENTERO", "IVALUE", "MMFL",
    "KIMS", "ANANTRAJ", "SOBHA", "BRIGADE", "PRESTIGE", "DLF",
    "GODREJPROP", "OBEROIRLTY", "PHOENIXLTD", "SIGNATURE", "ELECTCAST"
]


def load_nse_price_bands(cache_dir: str = "data") -> Dict[str, Dict[str, Any]]:
    """
    Downloads official NSE sec_list.csv (Daily Price Bands & Circuit Limits),
    and compares with previous archived list to detect Price Band Increases (UP arrow)
    or Price Band Decreases (DOWN arrow).
    """
    import urllib.request
    import shutil
    os.makedirs(cache_dir, exist_ok=True)
    live_cache_file = os.path.join(cache_dir, "sec_list_latest.csv")
    prev_cache_file = os.path.join(cache_dir, "sec_list_prev.csv")

    # Seed initial previous archive from desktop app if available
    desktop_archive = "C:/Users/Yagna79/Desktop/chartink_fyers_sector_dashboard/data/nse_archive/sec_list_2026-07-02.csv"
    if not os.path.exists(prev_cache_file) and os.path.exists(desktop_archive):
        try:
            shutil.copy(desktop_archive, prev_cache_file)
        except Exception:
            pass

    df_live = None
    url = "https://nsearchives.nseindia.com/content/equities/sec_list.csv"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
            if os.path.exists(live_cache_file):
                with open(live_cache_file, "rb") as f_old:
                    old_content = f_old.read()
                if old_content != content:
                    with open(prev_cache_file, "wb") as f_prev:
                        f_prev.write(old_content)
            with open(live_cache_file, "wb") as f:
                f.write(content)
            df_live = pd.read_csv(live_cache_file)
    except Exception as e:
        logger.warning(f"Could not download live NSE sec_list.csv: {e}")
        if os.path.exists(live_cache_file):
            df_live = pd.read_csv(live_cache_file)

    if df_live is None or df_live.empty:
        return {}

    df_prev = None
    if os.path.exists(prev_cache_file):
        try:
            df_prev = pd.read_csv(prev_cache_file)
        except Exception:
            df_prev = None

    prev_map = {}
    if df_prev is not None and not df_prev.empty and "Symbol" in df_prev.columns and "Band" in df_prev.columns:
        for _, row in df_prev.iterrows():
            s = str(row["Symbol"]).strip().upper()
            b = str(row["Band"]).strip()
            prev_map[s] = b

    results = {}
    for _, row in df_live.iterrows():
        sym = str(row["Symbol"]).strip().upper()
        raw_b = str(row["Band"]).strip()

        is_fno = "no band" in raw_b.lower() or raw_b == "-" or raw_b == "0"
        band_num = None
        if not is_fno:
            try:
                band_num = float(raw_b.replace("%", ""))
            except Exception:
                band_num = None

        band_str = "F&O" if is_fno else f"{int(band_num)}%" if band_num and band_num.is_integer() else f"{band_num}%" if band_num else "20%"

        band_change = "NONE"
        old_band_num = None
        if sym in prev_map:
            prev_raw = prev_map[sym]
            prev_is_fno = "no band" in prev_raw.lower() or prev_raw == "-"
            if not prev_is_fno:
                try:
                    old_band_num = float(prev_raw.replace("%", ""))
                except Exception:
                    pass

        if band_num is not None and old_band_num is not None:
            if band_num > old_band_num:
                band_change = "UP"
            elif band_num < old_band_num:
                band_change = "DOWN"

        clean_old_band = None
        if old_band_num is not None:
            clean_old_band = f"{int(old_band_num)}%" if old_band_num.is_integer() else f"{old_band_num}%"

        results[sym] = {
            "band_num": band_num if band_num is not None else (99.0 if is_fno else 20.0),
            "band_str": band_str,
            "band_change": band_change,
            "old_band": clean_old_band,
            "is_fno": is_fno,
        }

    return results


def fetch_nifty_benchmark(days: int = 365) -> pd.DataFrame:
    """Fetches Nifty 50 benchmark data for calculating Relative Strength (RS)."""
    try:
        nifty = yf.Ticker("^NSEI")
        df = nifty.history(period="1y", interval="1d")
        if not df.empty:
            return df
    except Exception as e:
        logger.warning(f"Could not fetch Nifty benchmark: {e}")
    return pd.DataFrame()


def calc_rs_rating(stock_df: pd.DataFrame, nifty_df: pd.DataFrame, period_days: int) -> float:
    """
    Calculates Relative Strength (RS) of stock vs Nifty benchmark over specified lookback days.
    Positive value indicates outperformance; negative indicates underperformance.
    """
    if stock_df.empty or len(stock_df) < period_days:
        return 0.0

    stock_ret = (stock_df["Close"].iloc[-1] / stock_df["Close"].iloc[-period_days] - 1.0) * 100.0

    if not nifty_df.empty and len(nifty_df) >= period_days:
        nifty_ret = (nifty_df["Close"].iloc[-1] / nifty_df["Close"].iloc[-period_days] - 1.0) * 100.0
        return round(stock_ret - nifty_ret, 1)
    return round(stock_ret, 1)


def evaluate_swing_setups(
    df: pd.DataFrame,
    ticker: str,
    nifty_df: pd.DataFrame,
    band_info: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Evaluates all swing trading setups on completed daily bars."""
    if df.empty or len(df) < 50:
        return None

    b_info = band_info or {}
    band_str = b_info.get("band_str", "20%")
    band_num = b_info.get("band_num", 20.0)
    band_change = b_info.get("band_change", "NONE")
    old_band = b_info.get("old_band")
    is_fno = b_info.get("is_fno", False)

    close = df["Close"].to_numpy()
    open_p = df["Open"].to_numpy()
    high = df["High"].to_numpy()
    low = df["Low"].to_numpy()
    vol = df["Volume"].to_numpy()

    c_cur = float(close[-1])
    o_cur = float(open_p[-1])
    h_cur = float(high[-1])
    l_cur = float(low[-1])
    v_cur = float(vol[-1])
    c_prev = float(close[-2])

    day_range = h_cur - l_cur
    if day_range <= 0:
        return None

    pct_change = round(((c_cur - c_prev) / c_prev) * 100.0, 2)
    clv = round((c_cur - l_cur) / day_range, 2)

    # Moving Averages
    close_series = df["Close"]
    sma10 = float(close_series.rolling(10).mean().iloc[-1])
    sma20 = float(close_series.rolling(20).mean().iloc[-1])
    sma50 = float(close_series.rolling(50).mean().iloc[-1])
    sma200 = float(close_series.rolling(200).mean().iloc[-1]) if len(df) >= 200 else None

    ema10 = float(close_series.ewm(span=10, adjust=False).mean().iloc[-1])
    ema20 = float(close_series.ewm(span=20, adjust=False).mean().iloc[-1])
    ema50 = float(close_series.ewm(span=50, adjust=False).mean().iloc[-1])
    ema200 = float(close_series.ewm(span=200, adjust=False).mean().iloc[-1]) if len(df) >= 200 else None

    # Volume SMA
    vol_sma20 = float(df["Volume"].rolling(20).mean().iloc[-1])
    rvol = round(v_cur / vol_sma20, 2) if vol_sma20 > 0 else 1.0

    # 52-Week High & Low
    high_52w = float(df["High"].iloc[-250:].max()) if len(df) >= 250 else float(df["High"].max())
    low_52w = float(df["Low"].iloc[-250:].min()) if len(df) >= 250 else float(df["Low"].min())
    dist_52w_high_pct = round(((c_cur - high_52w) / high_52w) * 100.0, 1)

    # Relative Strength
    rs_1m = calc_rs_rating(df, nifty_df, 21)
    rs_3m = calc_rs_rating(df, nifty_df, 63)
    rs_6m = calc_rs_rating(df, nifty_df, 126)

    # --- SETUP EVALUATION ---
    setups_matched = []
    setup_tags = []

    # 1. Committed Buyers (CB) - Institutional Accumulation
    gain_from_open = ((c_cur - o_cur) / o_cur * 100.0) if o_cur > 0 else 0.0
    body_pct = abs(c_cur - o_cur) / day_range
    cond_cb = (
        gain_from_open >= 2.5
        and clv >= 0.70
        and body_pct >= 0.55
        and rvol >= 1.75
        and (sma200 is None or c_cur >= sma200 * 0.95)
    )
    if cond_cb:
        setups_matched.append("Committed Buyers (CB)")
        setup_tags.append("CB")

    # 2. Daily M10 Setup (Pullback touch in strong uptrend)
    cond_m10 = (
        ema10 > ema20 > ema50
        and abs(c_cur - ema10) / ema10 <= 0.025
        and rvol <= 1.2
        and c_cur > ema50
    )
    if cond_m10:
        setups_matched.append("M10 Pullback Touch")
        setup_tags.append("M10")

    # 3. Core Contraction & EMA Tangle (Coiled springs near 200 EMA)
    if ema200 is not None:
        tangle_gap = abs(ema10 - ema50) / ema50
        near_200 = 0.85 <= (c_cur / ema200) <= 1.25
        cond_tangle = tangle_gap <= 0.06 and near_200 and rvol <= 1.0
        if cond_tangle:
            setups_matched.append("EMA Tangle Contraction")
            setup_tags.append("TANGLE")

    # 4. 52-Week High Breakout
    cond_52w = (
        dist_52w_high_pct >= -3.0
        and c_cur > o_cur
        and rvol >= 1.3
        and c_cur > sma20 > sma50
    )
    if cond_52w:
        setups_matched.append("52W High Breakout")
        setup_tags.append("52W_HIGH")

    # 5. High Relative Strength Leader
    cond_rs = (
        rs_1m >= 5.0
        and rs_3m >= 10.0
        and c_cur > sma50
        and (sma200 is None or c_cur > sma200)
    )
    if cond_rs:
        setups_matched.append("RS Outperformer")
        setup_tags.append("HIGH_RS")

    # 6. Volume Shocker
    cond_vol_shocker = rvol >= 3.0 and pct_change >= 2.0
    if cond_vol_shocker:
        setups_matched.append("Volume Shocker (3x+ Vol)")
        setup_tags.append("VOL_SHOCK")

    # 7. Price Band Revision Tracking
    if band_change == "UP":
        setups_matched.append(f"Price Band Increased ({old_band} ⬆️ {band_str})")
        setup_tags.append("BAND_UP")
    elif band_change == "DOWN":
        setups_matched.append(f"Price Band Decreased ({old_band} ⬇️ {band_str})")
        setup_tags.append("BAND_DOWN")

    # Priority score for ranking
    score = len(setups_matched) * 10
    if "Committed Buyers (CB)" in setups_matched:
        score += 15
    if "52W High Breakout" in setups_matched:
        score += 10
    if "RS Outperformer" in setups_matched:
        score += 10
    if band_change == "UP":
        score += 15
    if rvol >= 2.5:
        score += 5

    clean_symbol = ticker.replace(".NS", "")

    # Format last 150 daily candles (~7.5 months) for TradingView Lightweight Charts
    candles = []
    tail_df = df.tail(150)
    for idx_dt, row in tail_df.iterrows():
        try:
            d_str = idx_dt.strftime("%Y-%m-%d") if hasattr(idx_dt, "strftime") else str(idx_dt)[:10]
            c_open = round(float(row["Open"]), 2)
            c_high = round(float(row["High"]), 2)
            c_low = round(float(row["Low"]), 2)
            c_close = round(float(row["Close"]), 2)
            c_vol = int(row["Volume"]) if not pd.isna(row["Volume"]) else 0
            if c_high >= c_low and c_open > 0 and c_close > 0:
                candles.append({
                    "time": d_str,
                    "open": c_open,
                    "high": c_high,
                    "low": c_low,
                    "close": c_close,
                    "volume": c_vol,
                })
        except Exception:
            continue

    return {
        "symbol": clean_symbol,
        "price": round(c_cur, 2),
        "change_pct": pct_change,
        "clv": clv,
        "volume": int(v_cur),
        "rvol": rvol,
        "price_band": band_str,
        "band_num": band_num,
        "band_change": band_change,
        "old_band": old_band,
        "is_fno": is_fno,
        "sma10": round(sma10, 1),
        "sma20": round(sma20, 1),
        "sma50": round(sma50, 1),
        "sma200": round(sma200, 1) if sma200 else None,
        "ema10": round(ema10, 1),
        "dist_52w_high": dist_52w_high_pct,
        "rs_1m": rs_1m,
        "rs_3m": rs_3m,
        "rs_6m": rs_6m,
        "score": score,
        "setups": setups_matched,
        "setup_tags": setup_tags,
        "candles": candles,
        "chart_tv": f"https://in.tradingview.com/chart/?symbol=NSE%3A{clean_symbol}",
        "chart_fyers": f"https://trade.fyers.in/?symbol=NSE:{clean_symbol}-EQ",
    }


def run_full_screener(tickers: Optional[List[str]] = None, output_json: str = "data.json") -> List[Dict[str, Any]]:
    """Runs the complete screening pipeline and writes data.json."""
    tz = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(tz)
    logger.info(f"Starting NSE Swing Screener at {now_ist.strftime('%Y-%m-%d %H:%M:%S IST')}...")

    symbols = tickers or DEFAULT_TICKERS
    # Format with .NS suffix for Yahoo Finance
    yf_symbols = [f"{s}.NS" if not s.endswith(".NS") else s for s in symbols]

    logger.info(f"Fetching benchmark Nifty 50...")
    nifty_df = fetch_nifty_benchmark()

    logger.info(f"Loading official NSE Price Bands & Circuit Limits...")
    bands_dict = load_nse_price_bands()

    logger.info(f"Downloading history for {len(yf_symbols)} tickers in batch...")
    # Batch download past 1 year daily candles
    raw_data = yf.download(
        tickers=yf_symbols,
        period="1y",
        interval="1d",
        group_by="ticker",
        threads=True,
        progress=False,
    )

    results = []
    for yf_sym in yf_symbols:
        clean = yf_sym.replace(".NS", "")
        try:
            if isinstance(raw_data.columns, pd.MultiIndex):
                if yf_sym in raw_data.columns.levels[0]:
                    df_sym = raw_data[yf_sym].dropna(how="all").copy()
                elif clean in raw_data.columns.levels[0]:
                    df_sym = raw_data[clean].dropna(how="all").copy()
                else:
                    continue
            else:
                df_sym = raw_data.copy()

            if df_sym.empty or len(df_sym) < 30:
                continue

            b_info = bands_dict.get(clean.upper())
            record = evaluate_swing_setups(df_sym, clean, nifty_df, band_info=b_info)
            if record and (len(record["setups"]) > 0 or record["score"] > 0):
                results.append(record)

        except Exception as e:
            logger.debug(f"Error processing {clean}: {e}")
            continue

    # Sort results by score descending, then by rvol descending
    results.sort(key=lambda x: (x["score"], x["rvol"], x["change_pct"]), reverse=True)

    payload = {
        "metadata": {
            "screener_name": "NSE Swing & Momentum Screener",
            "last_updated_ist": now_ist.strftime("%d %b %Y, %I:%M %p IST"),
            "total_scanned": len(symbols),
            "matches_found": len(results),
            "setups_supported": [
                {"tag": "CB", "name": "Committed Buyers (CB)", "desc": "+3% gain, CLV > 0.70, 2x Vol"},
                {"tag": "M10", "name": "M10 Pullback Touch", "desc": "10>20>50 EMA, touch 10 EMA, low vol"},
                {"tag": "TANGLE", "name": "EMA Tangle", "desc": "Coiled 10/50 EMA near 200 EMA"},
                {"tag": "52W_HIGH", "name": "52W High Breakout", "desc": "Within 2.5% of 52W High + Vol"},
                {"tag": "HIGH_RS", "name": "High RS Leader", "desc": "Outperforming Nifty over 1M/3M"},
                {"tag": "VOL_SHOCK", "name": "Volume Shocker", "desc": "Volume > 3.0x 20-SMA"},
                {"tag": "BAND_UP", "name": "Band Increased ⬆️", "desc": "Circuit limit expanded (e.g. 5%->10%, 10%->20%)"},
                {"tag": "BAND_DOWN", "name": "Band Decreased ⬇️", "desc": "Circuit limit reduced (Surveillance/ESM)"},
            ]
        },
        "stocks": results
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(',', ':'))

    logger.info(f"Done! Evaluated {len(symbols)} stocks -> {len(results)} matches written to {output_json}.")
    return results


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    run_full_screener(output_json=out_file)


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
# Default curated list of ~250 top momentum & liquid tickers across Large, Mid, Small caps
DEFAULT_TICKERS = [
    # Nifty 50 Core
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "BHARTIARTL", "ITC", "SBIN",
    "LICI", "HINDUNILVR", "LT", "BAJFINANCE", "HCLTECH", "MARUTI", "SUNPHARMA",
    "ADANIENT", "TATAMOTORS", "NTPC", "KOTAKBANK", "TITAN", "ONGC", "AXISBANK",
    "ADANIPORTS", "COALINDIA", "POWERGRID", "M&M", "BAJAJFINSV", "TATASTEEL",
    # Leading Momentum & Growth Stocks
    "BEL", "HAL", "VBL", "TRENT", "DIXON", "POLYCAB", "KALYANKJIL", "BOMDYEING",
    "SUZLON", "ZOMATO", "JIOFIN", "PERSISTENT", "COFORGE", "KPITTECH", "TATAELXSI",
    "MAZDOCK", "COCHINSHIP", "GRSE", "BHEL", "RVNL", "IRFC", "RAILTEL", "IRCON",
    "PFC", "RECLTD", "IREDA", "HUDCO", "NBCC", "MOTHERSON", "BHARATFORG",
    "CHAMBLFERT", "FACT", "RCF", "NATIONALUM", "HINDCOPPER", "VEDL", "NMDC",
    "SAIL", "JINDALSTEL", "JSWSTEEL", "APLAPOLLO", "ASTRAL", "SUPREMEIND",
    "CUMMINSIND", "SIEMENS", "ABB", "CGPOWER", "BOSCHLTD", "THERMAX", "KEI",
    "SCHNEIDER", "KEC", "VOLTAS", "BLUESTARCO", "HAVELLS", "CROMPTON",
    # Pharma, Chemicals, Hospitals & Diagnostics
    "LUPIN", "CIPLA", "DRREDDY", "DIVISLAB", "AUROPHARMA", "MANKIND", "TORNTPHARM",
    "GLENMARK", "ZYDUSLIFE", "ALKEM", "APOLLOHOSP", "MAXHEALTH", "FORTIS",
    "MEDANTA", "LALPATHLAB", "METROPOLIS", "SYNGENE", "PIIND", "DEEPAKNTR",
    "TATACHEM", "SRF", "NAVINFLUOR", "FLUOROCHEM", "ATUL", "AARTIIND",
    # Consumer, Retail, Textiles & Auto
    "DMART", "V2RETAIL", "SHOPPERS", "RAYMOND", "GOKEX", "KPRMILL", "PAGEIND",
    "TITAN", "ETHOSLTD", "SENCO", "THOMASCOOK", "INDIGO", "SPICEJET", "EIHOTEL",
    "TAJGVK", "DEVYANI", "JUBLFOOD", "WESTLIFE", "SAPPHIRE", "RADICO", "TIINDIA",
    "ESCORTS", "TVSMOTOR", "BAJAJ-AUTO", "HEROMOTOCO", "ASHOKLEY", "EICHERMOT",
    # High Momentum Mid & Small Caps (including recently active movers)
    "WABAG", "VRLLOG", "APLLTD", "WINDLAS", "TVSELECT", "HPL", "TEXINFRA",
    "AEGISVOPAK", "RAMKY", "TTML", "MTNL", "TTKPRESTIG", "KALAMANDIR", "AGIIL",
    "SAILIFE", "IKIO", "ENTERO", "IVALUE", "MMFL", "GENSOL", "INOXWIND",
    "SWANENERGY", "KIMS", "ANANTRAJ", "SOBHA", "BRIGADE", "PRESTIGE", "DLF",
    "GODREJPROP", "OBEROIRLTY", "MACROTECH", "PHOENIXLTD", "SIGNATURE"
]


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


def evaluate_swing_setups(df: pd.DataFrame, ticker: str, nifty_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Evaluates all swing trading setups on completed daily bars."""
    if df.empty or len(df) < 50:
        return None

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

    # Priority score for ranking
    score = len(setups_matched) * 10
    if "Committed Buyers (CB)" in setups_matched:
        score += 15
    if "52W High Breakout" in setups_matched:
        score += 10
    if "RS Outperformer" in setups_matched:
        score += 10
    if rvol >= 2.5:
        score += 5

    clean_symbol = ticker.replace(".NS", "")

    return {
        "symbol": clean_symbol,
        "price": round(c_cur, 2),
        "change_pct": pct_change,
        "clv": clv,
        "volume": int(v_cur),
        "rvol": rvol,
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

            record = evaluate_swing_setups(df_sym, clean, nifty_df)
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
            ]
        },
        "stocks": results
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    logger.info(f"Done! Evaluated {len(symbols)} stocks -> {len(results)} matches written to {output_json}.")
    return results


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    run_full_screener(output_json=out_file)


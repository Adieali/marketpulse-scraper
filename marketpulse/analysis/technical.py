"""
MarketPulse — Technical Analysis
Computes RSI, MACD, Bollinger Bands, Moving Averages and more
from a list of OHLCV dictionaries or a pandas DataFrame.
"""

from __future__ import annotations

import math
from typing import List, Dict, Optional


def _ema(values: List[float], period: int) -> List[Optional[float]]:
    """Exponential Moving Average."""
    result = [None] * len(values)
    if len(values) < period:
        return result
    k = 2.0 / (period + 1)
    sma = sum(values[:period]) / period
    result[period - 1] = sma
    for i in range(period, len(values)):
        result[i] = values[i] * k + result[i - 1] * (1 - k)
    return result


def sma(values: List[float], period: int) -> List[Optional[float]]:
    """Simple Moving Average."""
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        result[i] = round(sum(values[i - period + 1: i + 1]) / period, 4)
    return result


def rsi(closes: List[float], period: int = 14) -> List[Optional[float]]:
    """Relative Strength Index (Wilder smoothing)."""
    result = [None] * len(closes)
    if len(closes) < period + 1:
        return result

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(closes)):
        idx = i - 1  # deltas index
        avg_gain = (avg_gain * (period - 1) + gains[idx]) / period
        avg_loss = (avg_loss * (period - 1) + losses[idx]) / period
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = round(100 - (100 / (1 + rs)), 2)

    return result


def macd(
    closes: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Dict[str, List[Optional[float]]]:
    """MACD line, Signal line, and Histogram."""
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    macd_line = [
        round(f - s, 4) if f is not None and s is not None else None
        for f, s in zip(ema_fast, ema_slow)
    ]

    # Signal = EMA of MACD line (skip Nones)
    valid_start = next((i for i, v in enumerate(macd_line) if v is not None), None)
    signal_line = [None] * len(macd_line)
    if valid_start is not None:
        valid_macd = [v for v in macd_line if v is not None]
        sig = _ema(valid_macd, signal)
        j = 0
        for i in range(valid_start, len(macd_line)):
            signal_line[i] = sig[j]
            j += 1

    histogram = [
        round(m - s, 4) if m is not None and s is not None else None
        for m, s in zip(macd_line, signal_line)
    ]

    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def bollinger_bands(
    closes: List[float],
    period: int = 20,
    std_dev: float = 2.0,
) -> Dict[str, List[Optional[float]]]:
    """Bollinger Bands: upper, middle (SMA), lower."""
    middle = sma(closes, period)
    upper = [None] * len(closes)
    lower = [None] * len(closes)

    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1: i + 1]
        mean = middle[i]
        variance = sum((x - mean) ** 2 for x in window) / period
        sd = math.sqrt(variance)
        upper[i] = round(mean + std_dev * sd, 4)
        lower[i] = round(mean - std_dev * sd, 4)

    return {"upper": upper, "middle": middle, "lower": lower}


def compute_all_indicators(
    history: List[Dict],
    ticker: str = "",
) -> Dict:
    """
    Given a list of {"date": str, "close": float, ...} dicts (sorted oldest→newest),
    compute and return all indicators as a dict ready for JSON export.
    """
    if not history:
        return {}

    history_sorted = sorted(history, key=lambda r: r["date"])
    closes = [float(r["close"]) for r in history_sorted]
    dates  = [r["date"] for r in history_sorted]

    ma20  = sma(closes, 20)
    ma50  = sma(closes, 50)
    ma200 = sma(closes, 200)
    rsi14 = rsi(closes, 14)
    macd_data = macd(closes)
    bb    = bollinger_bands(closes, 20)

    # Build timeline array for the web dashboard
    timeline = []
    for i, row in enumerate(history_sorted):
        timeline.append({
            "date":           row["date"],
            "open":           row.get("open"),
            "high":           row.get("high"),
            "low":            row.get("low"),
            "close":          row.get("close"),
            "volume":         row.get("volume"),
            "ma20":           ma20[i],
            "ma50":           ma50[i],
            "ma200":          ma200[i],
            "rsi":            rsi14[i],
            "macd":           macd_data["macd"][i],
            "macd_signal":    macd_data["signal"][i],
            "macd_histogram": macd_data["histogram"][i],
            "bb_upper":       bb["upper"][i],
            "bb_middle":      bb["middle"][i],
            "bb_lower":       bb["lower"][i],
        })

    # Latest values summary
    last = {k: v for k, v in timeline[-1].items() if v is not None} if timeline else {}

    return {
        "ticker":   ticker,
        "timeline": timeline,
        "latest":   last,
        "summary": {
            "rsi_signal":   _rsi_signal(last.get("rsi")),
            "macd_signal":  _macd_signal(last.get("macd"), last.get("macd_signal")),
            "trend":        _trend_signal(last.get("close"), last.get("ma50"), last.get("ma200")),
        },
    }


def _rsi_signal(rsi_val) -> str:
    if rsi_val is None:
        return "N/A"
    if rsi_val >= 70:
        return "Overbought"
    if rsi_val <= 30:
        return "Oversold"
    return "Neutral"


def _macd_signal(macd_val, signal_val) -> str:
    if macd_val is None or signal_val is None:
        return "N/A"
    return "Bullish" if macd_val > signal_val else "Bearish"


def _trend_signal(close, ma50, ma200) -> str:
    if close is None or ma50 is None or ma200 is None:
        return "N/A"
    if close > ma50 > ma200:
        return "Strong Uptrend"
    if close > ma50:
        return "Uptrend"
    if close < ma50 < ma200:
        return "Strong Downtrend"
    return "Downtrend"

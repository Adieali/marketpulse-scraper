"""
Tests for marketpulse.analysis.technical
"""
import math
import pytest

from marketpulse.analysis.technical import (
    sma, rsi, macd, bollinger_bands, compute_all_indicators,
    _rsi_signal, _macd_signal, _trend_signal,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture
def flat_closes():
    """Constant price series — all indicators should be neutral."""
    return [100.0] * 50


@pytest.fixture
def trending_up():
    """Steadily rising series."""
    return [100.0 + i * 0.5 for i in range(60)]


@pytest.fixture
def trending_down():
    """Steadily falling series."""
    return [200.0 - i * 0.5 for i in range(60)]


@pytest.fixture
def sample_history():
    """OHLCV dicts (250 trading days)."""
    import random
    random.seed(42)
    price = 150.0
    rows = []
    for i in range(250):
        price += random.uniform(-2, 2)
        price = max(price, 10)
        rows.append({
            "date":   f"2024-{(i // 30 + 1):02d}-{(i % 28 + 1):02d}",
            "open":   round(price - 0.5, 2),
            "high":   round(price + 1.0, 2),
            "low":    round(price - 1.0, 2),
            "close":  round(price, 2),
            "volume": random.randint(1_000_000, 5_000_000),
        })
    return rows


# ── SMA ───────────────────────────────────────────────────────────────────────
class TestSMA:
    def test_correct_value(self):
        result = sma([1, 2, 3, 4, 5], 3)
        assert result[2] == 2.0
        assert result[4] == 4.0

    def test_leading_nones(self):
        result = sma([10] * 10, 5)
        assert all(v is None for v in result[:4])
        assert all(v == 10.0 for v in result[4:])

    def test_flat_series(self, flat_closes):
        result = sma(flat_closes, 20)
        non_none = [v for v in result if v is not None]
        assert all(v == 100.0 for v in non_none)

    def test_too_short(self):
        result = sma([1, 2], 5)
        assert all(v is None for v in result)


# ── RSI ───────────────────────────────────────────────────────────────────────
class TestRSI:
    def test_range_0_to_100(self, trending_up):
        result = rsi(trending_up, 14)
        non_none = [v for v in result if v is not None]
        assert all(0 <= v <= 100 for v in non_none)

    def test_rising_series_overbought(self, trending_up):
        result = rsi(trending_up, 14)
        last = next(v for v in reversed(result) if v is not None)
        assert last > 70  # Strong uptrend → overbought

    def test_falling_series_oversold(self, trending_down):
        result = rsi(trending_down, 14)
        last = next(v for v in reversed(result) if v is not None)
        assert last < 30  # Strong downtrend → oversold

    def test_flat_series_neutral(self, flat_closes):
        # All gains and losses are zero — RSI undefined, expect None or 100
        result = rsi(flat_closes, 14)
        non_none = [v for v in result if v is not None]
        assert all(v == 100.0 for v in non_none)

    def test_signal_labels(self):
        assert _rsi_signal(72) == "Overbought"
        assert _rsi_signal(28) == "Oversold"
        assert _rsi_signal(50) == "Neutral"
        assert _rsi_signal(None) == "N/A"


# ── MACD ──────────────────────────────────────────────────────────────────────
class TestMACD:
    def test_returns_three_keys(self, trending_up):
        result = macd(trending_up)
        assert set(result.keys()) == {"macd", "signal", "histogram"}

    def test_length_matches_input(self, trending_up):
        result = macd(trending_up)
        for key in result:
            assert len(result[key]) == len(trending_up)

    def test_uptrend_bullish(self, trending_up):
        result = macd(trending_up)
        last_macd = next(v for v in reversed(result["macd"]) if v is not None)
        last_sig  = next(v for v in reversed(result["signal"]) if v is not None)
        assert last_macd > last_sig  # MACD above signal → bullish

    def test_signal_label(self):
        assert _macd_signal(1.5, 0.5) == "Bullish"
        assert _macd_signal(0.5, 1.5) == "Bearish"
        assert _macd_signal(None, 1.0) == "N/A"


# ── Bollinger Bands ───────────────────────────────────────────────────────────
class TestBollingerBands:
    def test_returns_three_keys(self, flat_closes):
        result = bollinger_bands(flat_closes, 20)
        assert set(result.keys()) == {"upper", "middle", "lower"}

    def test_upper_above_lower(self, sample_history):
        closes = [r["close"] for r in sample_history]
        result = bollinger_bands(closes, 20)
        for u, l in zip(result["upper"], result["lower"]):
            if u is not None and l is not None:
                assert u >= l

    def test_flat_series_zero_width(self, flat_closes):
        result = bollinger_bands(flat_closes, 20)
        # With constant prices, std_dev = 0, so upper == lower == middle
        for i in range(19, len(flat_closes)):
            assert result["upper"][i] == pytest.approx(100.0)
            assert result["lower"][i] == pytest.approx(100.0)


# ── Compute All Indicators ────────────────────────────────────────────────────
class TestComputeAllIndicators:
    def test_returns_expected_keys(self, sample_history):
        result = compute_all_indicators(sample_history, "TEST")
        assert "timeline" in result
        assert "latest" in result
        assert "summary" in result
        assert result["ticker"] == "TEST"

    def test_timeline_length(self, sample_history):
        result = compute_all_indicators(sample_history, "TEST")
        assert len(result["timeline"]) == len(sample_history)

    def test_empty_history(self):
        result = compute_all_indicators([], "EMPTY")
        assert result == {}

    def test_summary_has_signals(self, sample_history):
        result = compute_all_indicators(sample_history, "TEST")
        s = result["summary"]
        assert s["rsi_signal"] in ("Overbought", "Oversold", "Neutral", "N/A")
        assert s["macd_signal"] in ("Bullish", "Bearish", "N/A")
        assert "trend" in s

    def test_trend_labels(self):
        assert _trend_signal(110, 100, 90) == "Strong Uptrend"
        assert _trend_signal(95, 100, 90) == "Uptrend"
        assert _trend_signal(80, 90, 100) == "Strong Downtrend"
        assert _trend_signal(None, None, None) == "N/A"

"""
Tests for MarketPulse pipelines (Validation, Cleaning, Dedup).
"""
import pytest
from unittest.mock import MagicMock

from marketpulse.items import StockQuoteItem, CryptoItem, HistoricalPriceItem
from marketpulse.pipelines import ValidationPipeline, CleaningPipeline, DuplicateFilterPipeline


@pytest.fixture
def spider():
    return MagicMock()


@pytest.fixture
def valid_quote():
    return StockQuoteItem(
        ticker="AAPL",
        name="Apple Inc.",
        market="US",
        exchange="NASDAQ",
        currency="USD",
        price=175.50,
        change_pct=1.25,
        scraped_at="2024-01-15T10:00:00+00:00",
    )


@pytest.fixture
def valid_crypto():
    return CryptoItem(
        coin_id="bitcoin",
        symbol="BTC",
        name="Bitcoin",
        price_usd=42000.0,
        change_24h=2.5,
        scraped_at="2024-01-15T10:00:00+00:00",
    )


# ── Validation ────────────────────────────────────────────────────────────────
class TestValidationPipeline:
    def test_valid_quote_passes(self, valid_quote, spider):
        pipeline = ValidationPipeline()
        result = pipeline.process_item(valid_quote, spider)
        assert result["ticker"] == "AAPL"

    def test_missing_ticker_raises(self, spider):
        pipeline = ValidationPipeline()
        item = StockQuoteItem(name="Unknown", price=100.0)
        with pytest.raises(Exception, match="missing ticker"):
            pipeline.process_item(item, spider)

    def test_valid_crypto_passes(self, valid_crypto, spider):
        pipeline = ValidationPipeline()
        result = pipeline.process_item(valid_crypto, spider)
        assert result["coin_id"] == "bitcoin"

    def test_missing_coin_id_raises(self, spider):
        pipeline = ValidationPipeline()
        item = CryptoItem(symbol="BTC", name="Bitcoin", price_usd=42000.0)
        with pytest.raises(Exception, match="missing coin_id"):
            pipeline.process_item(item, spider)

    def test_valid_history_passes(self, spider):
        pipeline = ValidationPipeline()
        item = HistoricalPriceItem(ticker="AAPL", date="2024-01-15", close=175.0)
        result = pipeline.process_item(item, spider)
        assert result["ticker"] == "AAPL"

    def test_missing_history_date_raises(self, spider):
        pipeline = ValidationPipeline()
        item = HistoricalPriceItem(ticker="AAPL", close=175.0)
        with pytest.raises(Exception, match="missing ticker/date"):
            pipeline.process_item(item, spider)


# ── Cleaning ──────────────────────────────────────────────────────────────────
class TestCleaningPipeline:
    def test_nan_replaced_with_none(self, spider):
        pipeline = CleaningPipeline()
        item = StockQuoteItem(
            ticker="AAPL",
            price=float("nan"),
            change_pct=1.0,
        )
        result = pipeline.process_item(item, spider)
        assert result["price"] is None

    def test_change_pct_decimal_normalized(self, spider):
        """change_pct=0.025 should be normalized to 2.5."""
        pipeline = CleaningPipeline()
        item = StockQuoteItem(ticker="AAPL", price=175.0, change_pct=0.025)
        result = pipeline.process_item(item, spider)
        assert result["change_pct"] == pytest.approx(2.5)

    def test_crypto_pct_rounded(self, spider):
        pipeline = CleaningPipeline()
        item = CryptoItem(
            coin_id="bitcoin", symbol="BTC", name="Bitcoin",
            price_usd=42000.0,
            change_24h=2.123456789,
        )
        result = pipeline.process_item(item, spider)
        assert result["change_24h"] == pytest.approx(2.1235, rel=1e-3)


# ── Deduplication ─────────────────────────────────────────────────────────────
class TestDuplicateFilterPipeline:
    def test_first_item_passes(self, valid_quote, spider):
        pipeline = DuplicateFilterPipeline()
        result = pipeline.process_item(valid_quote, spider)
        assert result["ticker"] == "AAPL"

    def test_duplicate_quote_dropped(self, valid_quote, spider):
        pipeline = DuplicateFilterPipeline()
        pipeline.process_item(valid_quote, spider)
        with pytest.raises(Exception, match="Duplicate quote"):
            pipeline.process_item(valid_quote, spider)

    def test_different_ticker_passes(self, valid_quote, spider):
        pipeline = DuplicateFilterPipeline()
        pipeline.process_item(valid_quote, spider)
        item2 = StockQuoteItem(
            ticker="MSFT", name="Microsoft", price=380.0,
            scraped_at="2024-01-15T10:00:00+00:00",
        )
        result = pipeline.process_item(item2, spider)
        assert result["ticker"] == "MSFT"

    def test_duplicate_history_dropped(self, spider):
        pipeline = DuplicateFilterPipeline()
        item = HistoricalPriceItem(ticker="AAPL", date="2024-01-15", close=175.0)
        pipeline.process_item(item, spider)
        with pytest.raises(Exception, match="Duplicate history"):
            pipeline.process_item(item, spider)

    def test_different_date_history_passes(self, spider):
        pipeline = DuplicateFilterPipeline()
        item1 = HistoricalPriceItem(ticker="AAPL", date="2024-01-14", close=174.0)
        item2 = HistoricalPriceItem(ticker="AAPL", date="2024-01-15", close=175.0)
        pipeline.process_item(item1, spider)
        result = pipeline.process_item(item2, spider)
        assert result["date"] == "2024-01-15"

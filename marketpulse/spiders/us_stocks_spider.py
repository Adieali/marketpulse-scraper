"""
MarketPulse — US Stocks Spider
Collects quotes, fundamentals and historical prices for US tickers
using Yahoo Finance (yfinance library + HTML fallback via Scrapy).
"""

import json
import logging
from datetime import datetime, timezone

import scrapy
import yfinance as yf

from marketpulse.items import StockQuoteItem, StockFundamentalsItem, HistoricalPriceItem

logger = logging.getLogger(__name__)

# Default watchlist — can be overridden via CLI
DEFAULT_US_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "TSLA", "JPM", "JNJ", "V",
    "SPY", "QQQ",  # ETFs
]


class USStocksSpider(scrapy.Spider):
    name = "us_stocks"
    custom_settings = {
        "ROBOTSTXT_OBEY": False,  # yfinance fetches directly
        "DOWNLOAD_DELAY": 0.5,
    }

    def __init__(self, tickers=None, period="1y", *args, **kwargs):
        super().__init__(*args, **kwargs)
        if tickers:
            self.tickers = [t.strip().upper() for t in tickers.split(",")]
        else:
            self.tickers = DEFAULT_US_TICKERS
        self.period = period  # e.g. "1y", "6mo", "3mo"

    async def start(self):
        """Use a dummy request to trigger the spider; actual data via yfinance."""
        yield scrapy.Request(
            url="https://finance.yahoo.com",
            callback=self.fetch_all,
            dont_filter=True,
        )

    def fetch_all(self, response):
        now = datetime.now(timezone.utc).isoformat()
        for ticker_sym in self.tickers:
            try:
                ticker = yf.Ticker(ticker_sym)
                info = ticker.info or {}
                hist = ticker.history(period=self.period)

                # ── Quote Item ────────────────────────────────────────────
                yield StockQuoteItem(
                    ticker=ticker_sym,
                    name=info.get("longName") or info.get("shortName", ticker_sym),
                    market="US",
                    exchange=info.get("exchange", ""),
                    currency=info.get("currency", "USD"),
                    price=info.get("currentPrice") or info.get("regularMarketPrice"),
                    open_price=info.get("open") or info.get("regularMarketOpen"),
                    high=info.get("dayHigh") or info.get("regularMarketDayHigh"),
                    low=info.get("dayLow") or info.get("regularMarketDayLow"),
                    prev_close=info.get("previousClose") or info.get("regularMarketPreviousClose"),
                    volume=info.get("volume") or info.get("regularMarketVolume"),
                    avg_volume=info.get("averageVolume"),
                    change=round(
                        (info.get("currentPrice", 0) or 0) -
                        (info.get("previousClose", 0) or 0), 4
                    ),
                    change_pct=info.get("regularMarketChangePercent"),
                    market_cap=info.get("marketCap"),
                    week_52_high=info.get("fiftyTwoWeekHigh"),
                    week_52_low=info.get("fiftyTwoWeekLow"),
                    scraped_at=now,
                )

                # ── Fundamentals Item ─────────────────────────────────────
                yield StockFundamentalsItem(
                    ticker=ticker_sym,
                    name=info.get("longName", ticker_sym),
                    sector=info.get("sector", ""),
                    industry=info.get("industry", ""),
                    pe_ratio=info.get("trailingPE"),
                    pb_ratio=info.get("priceToBook"),
                    ps_ratio=info.get("priceToSalesTrailing12Months"),
                    eps=info.get("trailingEps"),
                    revenue=info.get("totalRevenue"),
                    net_income=info.get("netIncomeToCommon"),
                    profit_margin=info.get("profitMargins"),
                    dividend_yield=info.get("dividendYield"),
                    dividend_per_share=info.get("dividendRate"),
                    beta=info.get("beta"),
                    forward_pe=info.get("forwardPE"),
                    peg_ratio=info.get("pegRatio"),
                    debt_to_equity=info.get("debtToEquity"),
                    return_on_equity=info.get("returnOnEquity"),
                    free_cash_flow=info.get("freeCashflow"),
                    scraped_at=now,
                )

                # ── Historical prices ─────────────────────────────────────
                for date_idx, row in hist.iterrows():
                    yield HistoricalPriceItem(
                        ticker=ticker_sym,
                        date=str(date_idx.date()),
                        open=round(float(row["Open"]), 4),
                        high=round(float(row["High"]), 4),
                        low=round(float(row["Low"]), 4),
                        close=round(float(row["Close"]), 4),
                        adj_close=round(float(row.get("Adj Close", row["Close"])), 4),
                        volume=int(row["Volume"]),
                    )

                logger.info(f"[US] Fetched {ticker_sym}: {len(hist)} historical rows")

            except Exception as exc:
                logger.error(f"[US] Error fetching {ticker_sym}: {exc}")

"""
MarketPulse — Euronext / EU Stocks Spider
Collects quotes and fundamentals for French & European blue-chips
using yfinance (Yahoo Finance tickers with .PA / .DE / .MI suffixes)
+ Boursorama HTML scraping for additional FR market data.
"""

import logging
from datetime import datetime, timezone

import scrapy
import yfinance as yf
from scrapy_playwright.page import PageMethod

from marketpulse.items import StockQuoteItem, StockFundamentalsItem, HistoricalPriceItem

logger = logging.getLogger(__name__)

DEFAULT_EU_TICKERS = [
    # France — CAC40 leaders
    "MC.PA",   # LVMH
    "TTE.PA",  # TotalEnergies
    "SAN.PA",  # Sanofi
    "AIR.PA",  # Airbus
    "BNP.PA",  # BNP Paribas
    "OR.PA",   # L'Oréal
    "KER.PA",  # Kering
    "SAF.PA",  # Safran
    # Germany — DAX
    "SAP.DE",  # SAP
    "SIE.DE",  # Siemens
    "BMW.DE",  # BMW
    # Pan-EU ETF
    "EWQ",     # iShares MSCI France ETF
]


class EuronextSpider(scrapy.Spider):
    name = "euronext"
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": 1.0,
    }

    def __init__(self, tickers=None, period="1y", *args, **kwargs):
        super().__init__(*args, **kwargs)
        if tickers:
            self.tickers = [t.strip() for t in tickers.split(",")]
        else:
            self.tickers = DEFAULT_EU_TICKERS
        self.period = period

    def start_requests(self):
        yield scrapy.Request(
            url="https://www.boursorama.com/bourse/actions/cotations/",
            callback=self.fetch_yfinance,
            meta={
                "playwright": True,
                "playwright_include_page": False,
                "playwright_page_methods": [
                    PageMethod("wait_for_load_state", "domcontentloaded"),
                ],
            },
            dont_filter=True,
            errback=self.on_error,
        )

    def on_error(self, failure):
        logger.warning(f"Boursorama unreachable, falling back to yfinance: {failure}")
        return self._fetch_all_yfinance()

    def fetch_yfinance(self, response):
        yield from self._fetch_all_yfinance()

    def _fetch_all_yfinance(self):
        now = datetime.now(timezone.utc).isoformat()
        for ticker_sym in self.tickers:
            try:
                ticker = yf.Ticker(ticker_sym)
                info = ticker.info or {}
                hist = ticker.history(period=self.period)

                market = "EU" if ("." in ticker_sym and ticker_sym.split(".")[-1] in
                                  ("PA", "DE", "MI", "AS", "BR", "MC")) else "US"

                yield StockQuoteItem(
                    ticker=ticker_sym,
                    name=info.get("longName") or info.get("shortName", ticker_sym),
                    market=market,
                    exchange=info.get("exchange", ""),
                    currency=info.get("currency", "EUR"),
                    price=info.get("currentPrice") or info.get("regularMarketPrice"),
                    open_price=info.get("open") or info.get("regularMarketOpen"),
                    high=info.get("dayHigh"),
                    low=info.get("dayLow"),
                    prev_close=info.get("previousClose"),
                    volume=info.get("volume"),
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

                for date_idx, row in hist.iterrows():
                    yield HistoricalPriceItem(
                        ticker=ticker_sym,
                        date=str(date_idx.date()),
                        open=round(float(row["Open"]), 4),
                        high=round(float(row["High"]), 4),
                        low=round(float(row["Low"]), 4),
                        close=round(float(row["Close"]), 4),
                        adj_close=round(float(row["Close"]), 4),
                        volume=int(row["Volume"]),
                    )

                logger.info(f"[EU] Fetched {ticker_sym}: {len(hist)} rows")

            except Exception as exc:
                logger.error(f"[EU] Error fetching {ticker_sym}: {exc}")

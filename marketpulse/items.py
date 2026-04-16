"""
MarketPulse Scraper — Data Items
Defines Scrapy Item schemas for stocks, crypto and fundamentals.
"""

import scrapy


class StockQuoteItem(scrapy.Item):
    """Real-time / delayed stock quote (US & EU)."""
    ticker          = scrapy.Field()   # e.g. "AAPL", "MC.PA"
    name            = scrapy.Field()
    market          = scrapy.Field()   # "US" | "EU"
    exchange        = scrapy.Field()   # "NASDAQ" | "NYSE" | "Euronext"
    currency        = scrapy.Field()   # "USD" | "EUR"
    price           = scrapy.Field()   # float — current price
    open_price      = scrapy.Field()
    high            = scrapy.Field()
    low             = scrapy.Field()
    prev_close      = scrapy.Field()
    volume          = scrapy.Field()   # int
    avg_volume      = scrapy.Field()
    change          = scrapy.Field()   # float — absolute change
    change_pct      = scrapy.Field()   # float — % change
    market_cap      = scrapy.Field()   # float
    week_52_high    = scrapy.Field()
    week_52_low     = scrapy.Field()
    scraped_at      = scrapy.Field()   # ISO 8601


class StockFundamentalsItem(scrapy.Item):
    """Fundamental financial data per ticker."""
    ticker              = scrapy.Field()
    name                = scrapy.Field()
    sector              = scrapy.Field()
    industry            = scrapy.Field()
    pe_ratio            = scrapy.Field()   # P/E
    pb_ratio            = scrapy.Field()   # P/B
    ps_ratio            = scrapy.Field()   # P/S
    eps                 = scrapy.Field()   # Earnings per share
    revenue             = scrapy.Field()
    net_income          = scrapy.Field()
    profit_margin       = scrapy.Field()
    dividend_yield      = scrapy.Field()   # float %
    dividend_per_share  = scrapy.Field()
    beta                = scrapy.Field()
    forward_pe          = scrapy.Field()
    peg_ratio           = scrapy.Field()
    debt_to_equity      = scrapy.Field()
    return_on_equity    = scrapy.Field()
    free_cash_flow      = scrapy.Field()
    scraped_at          = scrapy.Field()


class HistoricalPriceItem(scrapy.Item):
    """OHLCV historical price point."""
    ticker      = scrapy.Field()
    date        = scrapy.Field()   # "YYYY-MM-DD"
    open        = scrapy.Field()
    high        = scrapy.Field()
    low         = scrapy.Field()
    close       = scrapy.Field()
    adj_close   = scrapy.Field()
    volume      = scrapy.Field()


class CryptoItem(scrapy.Item):
    """Cryptocurrency data from CoinGecko."""
    coin_id         = scrapy.Field()   # "bitcoin"
    symbol          = scrapy.Field()   # "btc"
    name            = scrapy.Field()
    price_usd       = scrapy.Field()
    price_eur       = scrapy.Field()
    market_cap_usd  = scrapy.Field()
    volume_24h      = scrapy.Field()
    change_1h       = scrapy.Field()
    change_24h      = scrapy.Field()
    change_7d       = scrapy.Field()
    ath             = scrapy.Field()   # All-time high
    ath_change_pct  = scrapy.Field()
    circulating_supply = scrapy.Field()
    total_supply    = scrapy.Field()
    rank            = scrapy.Field()
    scraped_at      = scrapy.Field()

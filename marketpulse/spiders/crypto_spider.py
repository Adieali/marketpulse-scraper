"""
MarketPulse — Crypto Spider
Fetches cryptocurrency data from CoinGecko public API (no key required).
Covers top coins + historical OHLCV data.
"""

import json
import logging
from datetime import datetime, timezone

import scrapy

from marketpulse.items import CryptoItem, HistoricalPriceItem

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

DEFAULT_COINS = [
    "bitcoin", "ethereum", "binancecoin", "solana", "ripple",
    "cardano", "avalanche-2", "chainlink", "polkadot", "dogecoin",
    "litecoin", "uniswap", "aave", "maker", "the-graph",
]

COINS_PER_PAGE = 50   # CoinGecko max


class CryptoSpider(scrapy.Spider):
    name = "crypto"
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        # CoinGecko free tier: ~10 req/min on OHLC endpoint.
        # Force fully-sequential requests (concurrency=1, delay=6s -> 10 req/min).
        "DOWNLOAD_DELAY": 6.0,
        "RANDOMIZE_DOWNLOAD_DELAY": False,
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "AUTOTHROTTLE_ENABLED": False,   # let the fixed delay govern
        "RETRY_HTTP_CODES": [429, 500, 502, 503, 504],
        "RETRY_TIMES": 5,
    }

    def __init__(self, coins=None, history_days="365", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.coins = coins.split(",") if coins else DEFAULT_COINS
        self.history_days = history_days

    async def start(self):
        # Step 1: bulk market data for all default coins
        ids_param = "%2C".join(DEFAULT_COINS)
        url = (
            f"{COINGECKO_BASE}/coins/markets"
            f"?vs_currency=usd"
            f"&ids={ids_param}"
            f"&order=market_cap_desc"
            f"&per_page={COINS_PER_PAGE}"
            f"&page=1"
            f"&sparkline=false"
            f"&price_change_percentage=1h%2C24h%2C7d"
            f"&locale=en"
        )
        yield scrapy.Request(url, callback=self.parse_markets)

    def parse_markets(self, response):
        now = datetime.now(timezone.utc).isoformat()
        data = json.loads(response.text)
        for coin in data:
            yield CryptoItem(
                coin_id=coin["id"],
                symbol=coin["symbol"].upper(),
                name=coin["name"],
                price_usd=coin.get("current_price"),
                price_eur=None,   # fetched separately if needed
                market_cap_usd=coin.get("market_cap"),
                volume_24h=coin.get("total_volume"),
                change_1h=coin.get("price_change_percentage_1h_in_currency"),
                change_24h=coin.get("price_change_percentage_24h"),
                change_7d=coin.get("price_change_percentage_7d_in_currency"),
                ath=coin.get("ath"),
                ath_change_pct=coin.get("ath_change_percentage"),
                circulating_supply=coin.get("circulating_supply"),
                total_supply=coin.get("total_supply"),
                rank=coin.get("market_cap_rank"),
                scraped_at=now,
            )
            # Schedule historical OHLCV fetch
            yield scrapy.Request(
                url=f"{COINGECKO_BASE}/coins/{coin['id']}/ohlc"
                    f"?vs_currency=usd&days={self.history_days}",
                callback=self.parse_ohlcv,
                cb_kwargs={"coin_id": coin["id"]},
            )

    def parse_ohlcv(self, response, coin_id):
        """
        CoinGecko OHLCV format: [[timestamp_ms, open, high, low, close], ...]
        """
        try:
            data = json.loads(response.text)
            for candle in data:
                ts_ms, open_, high, low, close = candle
                date_str = datetime.fromtimestamp(
                    ts_ms / 1000, tz=timezone.utc
                ).strftime("%Y-%m-%d")
                yield HistoricalPriceItem(
                    ticker=coin_id,
                    date=date_str,
                    open=round(open_, 6),
                    high=round(high, 6),
                    low=round(low, 6),
                    close=round(close, 6),
                    adj_close=round(close, 6),
                    volume=None,
                )
            logger.info(f"[Crypto] {coin_id}: {len(data)} OHLCV candles")
        except Exception as exc:
            logger.error(f"[Crypto] OHLCV parse error for {coin_id}: {exc}")
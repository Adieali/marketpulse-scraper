"""
MarketPulse Scraper — Data Pipelines
Validation → Cleaning → Deduplication → SQLite → CSV → JSON → WebExport
"""

import csv
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from itemadapter import ItemAdapter

from marketpulse.items import (
    StockQuoteItem,
    StockFundamentalsItem,
    HistoricalPriceItem,
    CryptoItem,
)
from marketpulse.analysis.technical import compute_all_indicators

logger = logging.getLogger(__name__)


# ── 1. Validation Pipeline ────────────────────────────────────────────────────
class ValidationPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        if isinstance(item, (StockQuoteItem, StockFundamentalsItem)):
            if not adapter.get("ticker"):
                raise Exception(f"Dropped: missing ticker in {type(item).__name__}")
        elif isinstance(item, CryptoItem):
            if not adapter.get("coin_id"):
                raise Exception("Dropped: missing coin_id in CryptoItem")
        elif isinstance(item, HistoricalPriceItem):
            if not adapter.get("ticker") or not adapter.get("date"):
                raise Exception("Dropped: missing ticker/date in HistoricalPriceItem")

        return item


# ── 2. Cleaning Pipeline ──────────────────────────────────────────────────────
class CleaningPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        for field in adapter.field_names():
            val = adapter.get(field)
            if isinstance(val, float) and (val != val):  # NaN check
                adapter[field] = None

        if isinstance(item, StockQuoteItem):
            if adapter.get("change_pct"):
                pct = adapter["change_pct"]
                # Normalize — Yahoo sometimes returns 0.05 for 5%
                if abs(pct) < 1 and pct != 0:
                    adapter["change_pct"] = round(pct * 100, 4)

        if isinstance(item, CryptoItem):
            for pct_field in ("change_1h", "change_24h", "change_7d"):
                val = adapter.get(pct_field)
                if val is not None:
                    adapter[pct_field] = round(float(val), 4)

        return item


# ── 3. Deduplication Pipeline ─────────────────────────────────────────────────
class DuplicateFilterPipeline:
    def __init__(self):
        self._seen_quotes: set = set()
        self._seen_hist: set = set()

    def process_item(self, item, spider):
        if isinstance(item, StockQuoteItem):
            key = (item["ticker"], item.get("scraped_at", "")[:10])
            if key in self._seen_quotes:
                raise Exception(f"Duplicate quote: {key}")
            self._seen_quotes.add(key)
        elif isinstance(item, HistoricalPriceItem):
            key = (item["ticker"], item["date"])
            if key in self._seen_hist:
                raise Exception(f"Duplicate history: {key}")
            self._seen_hist.add(key)
        return item


# ── 4. SQLite Pipeline ────────────────────────────────────────────────────────
class SQLitePipeline:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(db_path=crawler.settings.get("SQLITE_PATH", "data/marketpulse.db"))

    def open_spider(self, spider):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def close_spider(self, spider):
        if self.conn:
            self.conn.commit()
            self.conn.close()

    def _create_tables(self):
        self.cursor.executescript("""
        CREATE TABLE IF NOT EXISTS stock_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, name TEXT, market TEXT, exchange TEXT, currency TEXT,
            price REAL, open_price REAL, high REAL, low REAL, prev_close REAL,
            volume INTEGER, avg_volume INTEGER, change REAL, change_pct REAL,
            market_cap REAL, week_52_high REAL, week_52_low REAL,
            scraped_at TEXT,
            UNIQUE(ticker, scraped_at)
        );
        CREATE INDEX IF NOT EXISTS idx_sq_ticker ON stock_quotes(ticker);
        CREATE INDEX IF NOT EXISTS idx_sq_market ON stock_quotes(market);

        CREATE TABLE IF NOT EXISTS stock_fundamentals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT UNIQUE, name TEXT, sector TEXT, industry TEXT,
            pe_ratio REAL, pb_ratio REAL, ps_ratio REAL, eps REAL,
            revenue REAL, net_income REAL, profit_margin REAL,
            dividend_yield REAL, dividend_per_share REAL, beta REAL,
            forward_pe REAL, peg_ratio REAL, debt_to_equity REAL,
            return_on_equity REAL, free_cash_flow REAL, scraped_at TEXT
        );

        CREATE TABLE IF NOT EXISTS historical_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, date TEXT, open REAL, high REAL, low REAL,
            close REAL, adj_close REAL, volume INTEGER,
            UNIQUE(ticker, date)
        );
        CREATE INDEX IF NOT EXISTS idx_hp_ticker ON historical_prices(ticker);
        CREATE INDEX IF NOT EXISTS idx_hp_date   ON historical_prices(date);

        CREATE TABLE IF NOT EXISTS crypto_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coin_id TEXT, symbol TEXT, name TEXT,
            price_usd REAL, price_eur REAL, market_cap_usd REAL,
            volume_24h REAL, change_1h REAL, change_24h REAL, change_7d REAL,
            ath REAL, ath_change_pct REAL,
            circulating_supply REAL, total_supply REAL, rank INTEGER,
            scraped_at TEXT,
            UNIQUE(coin_id, scraped_at)
        );
        CREATE INDEX IF NOT EXISTS idx_cq_coin ON crypto_quotes(coin_id);
        """)
        self.conn.commit()

    def process_item(self, item, spider):
        if isinstance(item, StockQuoteItem):
            self.cursor.execute("""
                INSERT OR REPLACE INTO stock_quotes
                (ticker,name,market,exchange,currency,price,open_price,high,low,prev_close,
                 volume,avg_volume,change,change_pct,market_cap,week_52_high,week_52_low,scraped_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                item.get("ticker"), item.get("name"), item.get("market"),
                item.get("exchange"), item.get("currency"), item.get("price"),
                item.get("open_price"), item.get("high"), item.get("low"),
                item.get("prev_close"), item.get("volume"), item.get("avg_volume"),
                item.get("change"), item.get("change_pct"), item.get("market_cap"),
                item.get("week_52_high"), item.get("week_52_low"), item.get("scraped_at"),
            ))

        elif isinstance(item, StockFundamentalsItem):
            self.cursor.execute("""
                INSERT OR REPLACE INTO stock_fundamentals
                (ticker,name,sector,industry,pe_ratio,pb_ratio,ps_ratio,eps,revenue,
                 net_income,profit_margin,dividend_yield,dividend_per_share,beta,
                 forward_pe,peg_ratio,debt_to_equity,return_on_equity,free_cash_flow,scraped_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                item.get("ticker"), item.get("name"), item.get("sector"),
                item.get("industry"), item.get("pe_ratio"), item.get("pb_ratio"),
                item.get("ps_ratio"), item.get("eps"), item.get("revenue"),
                item.get("net_income"), item.get("profit_margin"),
                item.get("dividend_yield"), item.get("dividend_per_share"),
                item.get("beta"), item.get("forward_pe"), item.get("peg_ratio"),
                item.get("debt_to_equity"), item.get("return_on_equity"),
                item.get("free_cash_flow"), item.get("scraped_at"),
            ))

        elif isinstance(item, HistoricalPriceItem):
            self.cursor.execute("""
                INSERT OR REPLACE INTO historical_prices
                (ticker,date,open,high,low,close,adj_close,volume)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                item.get("ticker"), item.get("date"), item.get("open"),
                item.get("high"), item.get("low"), item.get("close"),
                item.get("adj_close"), item.get("volume"),
            ))

        elif isinstance(item, CryptoItem):
            self.cursor.execute("""
                INSERT OR REPLACE INTO crypto_quotes
                (coin_id,symbol,name,price_usd,price_eur,market_cap_usd,volume_24h,
                 change_1h,change_24h,change_7d,ath,ath_change_pct,
                 circulating_supply,total_supply,rank,scraped_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                item.get("coin_id"), item.get("symbol"), item.get("name"),
                item.get("price_usd"), item.get("price_eur"),
                item.get("market_cap_usd"), item.get("volume_24h"),
                item.get("change_1h"), item.get("change_24h"), item.get("change_7d"),
                item.get("ath"), item.get("ath_change_pct"),
                item.get("circulating_supply"), item.get("total_supply"),
                item.get("rank"), item.get("scraped_at"),
            ))

        self.conn.commit()
        return item


# ── 5. CSV Pipeline ───────────────────────────────────────────────────────────
class CSVPipeline:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self._writers = {}
        self._files = {}

    @classmethod
    def from_crawler(cls, crawler):
        return cls(output_dir=crawler.settings.get("OUTPUT_DIR", "data"))

    def open_spider(self, spider):
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        for name, fields in [
            ("quotes",       ["ticker","name","market","price","change_pct","volume","market_cap","scraped_at"]),
            ("fundamentals", ["ticker","name","sector","pe_ratio","eps","dividend_yield","beta","scraped_at"]),
            ("crypto",       ["coin_id","symbol","name","price_usd","change_24h","market_cap_usd","rank","scraped_at"]),
        ]:
            path = os.path.join(self.output_dir, f"{name}_{ts}.csv")
            f = open(path, "w", newline="", encoding="utf-8-sig")
            self._files[name] = f
            self._writers[name] = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            self._writers[name].writeheader()

    def close_spider(self, spider):
        for f in self._files.values():
            f.close()

    def process_item(self, item, spider):
        if isinstance(item, StockQuoteItem):
            self._writers["quotes"].writerow(dict(ItemAdapter(item)))
        elif isinstance(item, StockFundamentalsItem):
            self._writers["fundamentals"].writerow(dict(ItemAdapter(item)))
        elif isinstance(item, CryptoItem):
            self._writers["crypto"].writerow(dict(ItemAdapter(item)))
        return item


# ── 6. JSON Lines Pipeline ────────────────────────────────────────────────────
class JSONPipeline:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self._files = {}

    @classmethod
    def from_crawler(cls, crawler):
        return cls(output_dir=crawler.settings.get("OUTPUT_DIR", "data"))

    def open_spider(self, spider):
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        for name in ("quotes", "fundamentals", "history", "crypto"):
            path = os.path.join(self.output_dir, f"{name}.jsonl")
            self._files[name] = open(path, "a", encoding="utf-8")

    def close_spider(self, spider):
        for f in self._files.values():
            f.close()

    def process_item(self, item, spider):
        mapping = {
            StockQuoteItem:       "quotes",
            StockFundamentalsItem:"fundamentals",
            HistoricalPriceItem:  "history",
            CryptoItem:           "crypto",
        }
        key = mapping.get(type(item))
        if key:
            self._files[key].write(json.dumps(dict(ItemAdapter(item))) + "\n")
        return item


# ── 7. Web Export Pipeline ────────────────────────────────────────────────────
class WebExportPipeline:
    """
    Accumulates all data in memory, then on spider close:
    - Computes technical indicators
    - Writes web/data/*.json files ready for the Netlify dashboard
    """

    def __init__(self, web_data_dir):
        self.web_data_dir = web_data_dir
        self._quotes: dict = {}
        self._fundamentals: dict = {}
        self._history: dict = {}   # ticker → list of OHLCV dicts
        self._crypto: list = []

    @classmethod
    def from_crawler(cls, crawler):
        return cls(web_data_dir=crawler.settings.get("WEB_DATA_DIR", "web/data"))

    def open_spider(self, spider):
        Path(self.web_data_dir).mkdir(parents=True, exist_ok=True)

    def process_item(self, item, spider):
        if isinstance(item, StockQuoteItem):
            self._quotes[item["ticker"]] = dict(ItemAdapter(item))
        elif isinstance(item, StockFundamentalsItem):
            self._fundamentals[item["ticker"]] = dict(ItemAdapter(item))
        elif isinstance(item, HistoricalPriceItem):
            t = item["ticker"]
            self._history.setdefault(t, []).append(dict(ItemAdapter(item)))
        elif isinstance(item, CryptoItem):
            self._crypto.append(dict(ItemAdapter(item)))
        return item

    def close_spider(self, spider):
        # Build enriched stock objects with indicators
        stocks_output = []
        for ticker, quote in self._quotes.items():
            hist = sorted(self._history.get(ticker, []), key=lambda r: r["date"])
            indicators = compute_all_indicators(hist, ticker) if hist else {}
            stocks_output.append({
                "quote":        quote,
                "fundamentals": self._fundamentals.get(ticker, {}),
                "indicators":   indicators,
            })

        self._write_json("stocks.json", stocks_output)

        # Crypto with indicators
        crypto_output = []
        for coin in self._crypto:
            cid = coin["coin_id"]
            hist = sorted(self._history.get(cid, []), key=lambda r: r["date"])
            indicators = compute_all_indicators(hist, cid) if hist else {}
            crypto_output.append({"quote": coin, "indicators": indicators})

        self._write_json("crypto.json", crypto_output)

        # Metadata
        meta = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "stock_count":  len(stocks_output),
            "crypto_count": len(crypto_output),
        }
        self._write_json("meta.json", meta)
        logger.info(
            f"[WebExport] Wrote {len(stocks_output)} stocks + "
            f"{len(crypto_output)} crypto to {self.web_data_dir}"
        )

    def _write_json(self, filename: str, data):
        path = os.path.join(self.web_data_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)

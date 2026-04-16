# 📈 MarketPulse — Financial Intelligence Scraper

> **Professional financial data pipeline** covering US stocks, European equities and cryptocurrency markets.
> Collects quotes, fundamentals and technical indicators — with a live dark-theme dashboard published on Netlify.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Scrapy](https://img.shields.io/badge/Scrapy-2.11-60A839)](https://scrapy.org)
[![yfinance](https://img.shields.io/badge/yfinance-0.2-blue)](https://pypi.org/project/yfinance/)
[![Netlify](https://img.shields.io/badge/Netlify-deployed-00C7B7?logo=netlify)](https://netlify.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🌐 **Live Dashboard**: [marketpulse.netlify.app](https://marketpulse.netlify.app)

---

## 📋 Features

- **3 data sources**: US stocks (Yahoo Finance), EU stocks (Euronext/Boursorama), Crypto (CoinGecko API)
- **30+ fields per asset**: quote, fundamentals (P/E, EPS, dividends, beta), historical OHLCV
- **Technical indicators** computed from scratch (no ta-lib dependency):
  - RSI (14), MACD (12/26/9), Bollinger Bands (20), SMA 20/50/200
  - Automatic signal labels: Overbought / Oversold / Bullish / Bearish / Trend
- **4-stage pipeline**: Validation → Cleaning → Deduplication → Multi-format output
- **3 output formats**: SQLite, CSV, JSON Lines
- **Web export pipeline**: generates Netlify-ready `web/data/*.json` automatically
- **Rotating User-Agents** + proxy rotation + anti-ban middleware
- **Click CLI**: `mp-scraper scrape / analyze / export / stats`
- **Docker + docker-compose** for isolated production runs
- **22 pytest unit tests** (technical analysis + pipelines)

---

## 🏗 Architecture

```
marketpulse-scraper/
├── marketpulse/
│   ├── spiders/
│   │   ├── us_stocks_spider.py   # Yahoo Finance via yfinance
│   │   ├── euronext_spider.py    # Euronext / Boursorama (CAC40, DAX)
│   │   └── crypto_spider.py     # CoinGecko public API
│   ├── middlewares/
│   │   ├── user_agent.py         # Random UA rotation
│   │   ├── proxy.py              # Proxy rotation (YAML/env)
│   │   ├── retry.py              # Smart retry + soft-ban detection
│   │   └── stats.py             # Request rate tracking
│   ├── analysis/
│   │   └── technical.py         # RSI, MACD, BB, SMA — pure Python
│   ├── items.py                  # StockQuoteItem, FundamentalsItem, CryptoItem
│   ├── pipelines.py              # 7 pipelines incl. WebExportPipeline
│   └── settings.py
├── cli/main.py                   # Click CLI (scrape/analyze/export/stats)
├── web/
│   ├── index.html                # Dark finance dashboard (Chart.js)
│   └── data/                     # Auto-generated JSON by WebExportPipeline
├── tests/
│   ├── test_technical.py         # 14 tests
│   └── test_pipelines.py         # 8 tests
├── config/
│   ├── tickers.yaml
│   └── proxies.yaml
├── netlify.toml
├── Dockerfile
└── docker-compose.yml
```

---

## ⚡ Quick Start

```bash
# Clone & setup
git clone https://github.com/Adieali/marketpulse-scraper.git
cd marketpulse-scraper
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
playwright install chromium

# Scrape all markets (US + EU + Crypto)
mp-scraper scrape --market all --period 1y

# Analyze a specific ticker
mp-scraper analyze --ticker AAPL

# Stats
mp-scraper stats
```

### Docker

```bash
docker-compose up scraper
# Or with custom params:
MARKET=crypto PERIOD=6mo docker-compose up scraper
```

---

## 🖥 CLI Reference

```bash
mp-scraper scrape   --market [us|eu|crypto|all]  --period [1mo|3mo|6mo|1y|2y|5y]
mp-scraper analyze  --ticker AAPL
mp-scraper export   --format [json|csv]  --market US  --min-cap 1000000000
mp-scraper stats    --db data/marketpulse.db
```

---

## 🌐 Dashboard (Netlify)

The `web/` folder is a self-contained static dashboard:
- **Dark Bloomberg-style theme** with animated ticker bar
- **4 tabs**: Overview, US Stocks, EU Stocks, Crypto
- **Sortable / searchable tables** with RSI badges and trend signals
- **Interactive charts**: price + MA20/MA50 on row click
- **Live crypto fallback** via CoinGecko API (no backend needed)

Deploy in one click: connect the repo to Netlify and set **Publish directory = `web`**.

---

## 📊 Indicators

| Indicator | Parameters | Signal |
|-----------|-----------|--------|
| RSI | period=14 | >70 Overbought / <30 Oversold |
| MACD | 12/26/9 | Line > Signal → Bullish |
| Bollinger Bands | period=20, 2σ | — |
| SMA | 20 / 50 / 200 | Close>MA50>MA200 → Strong Uptrend |

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

*Built as a professional portfolio project demonstrating advanced Python data engineering, financial analysis and full-stack deployment.*

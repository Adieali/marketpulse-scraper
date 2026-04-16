"""
MarketPulse Scraper — Scrapy Settings
"""
import os

BOT_NAME = "marketpulse"
SPIDER_MODULES = ["marketpulse.spiders"]
NEWSPIDER_MODULE = "marketpulse.spiders"

# ── Politeness ────────────────────────────────────────────────────────────────
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 2.0
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 15.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# ── Retry ─────────────────────────────────────────────────────────────────────
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [403, 429, 500, 502, 503, 504]

# ── Cache (dev only) ──────────────────────────────────────────────────────────
HTTPCACHE_ENABLED = os.getenv("SCRAPY_CACHE", "false").lower() == "true"
HTTPCACHE_EXPIRATION_SECS = 3600
HTTPCACHE_DIR = ".scrapy/httpcache"

# ── Playwright ────────────────────────────────────────────────────────────────
DOWNLOAD_HANDLERS = {
    "http":  "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True, "args": ["--no-sandbox"]}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# ── Middlewares ───────────────────────────────────────────────────────────────
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "marketpulse.middlewares.user_agent.RandomUserAgentMiddleware": 400,
    "marketpulse.middlewares.proxy.ProxyRotationMiddleware": 410,
    "marketpulse.middlewares.retry.RetryOnBanMiddleware": 420,
    "marketpulse.middlewares.stats.StatsMiddleware": 430,
}

# ── Pipelines ─────────────────────────────────────────────────────────────────
ITEM_PIPELINES = {
    "marketpulse.pipelines.ValidationPipeline": 100,
    "marketpulse.pipelines.CleaningPipeline": 200,
    "marketpulse.pipelines.DuplicateFilterPipeline": 300,
    "marketpulse.pipelines.SQLitePipeline": 400,
    "marketpulse.pipelines.CSVPipeline": 500,
    "marketpulse.pipelines.JSONPipeline": 600,
    "marketpulse.pipelines.WebExportPipeline": 700,
}

# ── Storage ───────────────────────────────────────────────────────────────────
SQLITE_PATH = os.getenv("SQLITE_PATH", "data/marketpulse.db")
OUTPUT_DIR   = os.getenv("OUTPUT_DIR", "data")
WEB_DATA_DIR = os.getenv("WEB_DATA_DIR", "web/data")

# ── Proxy ─────────────────────────────────────────────────────────────────────
PROXY_ENABLED = os.getenv("PROXY_ENABLED", "false").lower() == "true"
PROXY_FILE    = os.getenv("PROXY_FILE", "config/proxies.yaml")

# ── Feed ─────────────────────────────────────────────────────────────────────
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEEDS = {}

# ── Log ──────────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

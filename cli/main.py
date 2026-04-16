"""
MarketPulse CLI
Usage:
  mp-scraper scrape --market us|eu|crypto|all
  mp-scraper analyze --ticker AAPL
  mp-scraper export  --format csv|json --output DIR
  mp-scraper stats   --db data/marketpulse.db
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def _run_spider(spider_name: str, extra_settings: dict = None, **kwargs):
    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "marketpulse.settings")
    settings = get_project_settings()
    if extra_settings:
        for k, v in extra_settings.items():
            settings.set(k, v)

    process = CrawlerProcess(settings)
    process.crawl(spider_name, **kwargs)
    process.start()


@click.group()
@click.version_option("1.0.0", prog_name="mp-scraper")
def cli():
    """MarketPulse — Professional financial data scraper."""


# ── scrape ────────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--market", "-m", default="all",
              type=click.Choice(["us", "eu", "crypto", "all"]),
              help="Market to scrape. [default: all]")
@click.option("--tickers", "-t", default=None,
              help="Comma-separated list of tickers (overrides defaults).")
@click.option("--period", "-p", default="1y",
              type=click.Choice(["1mo", "3mo", "6mo", "1y", "2y", "5y"]),
              help="Historical period to fetch. [default: 1y]")
@click.option("--output-dir", "-o", default="data",
              help="Output directory for CSV/JSON/SQLite. [default: data]")
@click.option("--web-dir", default="web/data",
              help="Directory for Netlify-ready JSON files. [default: web/data]")
@click.option("--proxy-file", default=None,
              help="Path to proxies YAML file.")
@click.option("--delay", default=2.0, type=float,
              help="Min delay between requests (s). [default: 2.0]")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def scrape(market, tickers, period, output_dir, web_dir, proxy_file, delay, verbose):
    """Launch a market data crawl."""
    extra = {
        "OUTPUT_DIR":   output_dir,
        "WEB_DATA_DIR": web_dir,
        "DOWNLOAD_DELAY": delay,
        "LOG_LEVEL":    "DEBUG" if verbose else "INFO",
    }
    if proxy_file:
        extra["PROXY_FILE"] = proxy_file
        extra["PROXY_ENABLED"] = True

    kwargs = {"period": period}
    if tickers:
        kwargs["tickers"] = tickers

    spiders = {
        "us":     ["us_stocks"],
        "eu":     ["euronext"],
        "crypto": ["crypto"],
        "all":    ["us_stocks", "euronext", "crypto"],
    }[market]

    click.echo(f"\n🚀  MarketPulse Scraper — market: {market.upper()}")
    click.echo(f"    Period: {period} | Output: {output_dir}\n")

    for spider_name in spiders:
        click.echo(f"  ▶ Running spider: {spider_name}")
        _run_spider(spider_name, extra_settings=extra, **kwargs)

    click.echo(f"\n✅  Done. Web data written to: {web_dir}\n")


# ── analyze ───────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--ticker", "-t", required=True,
              help="Ticker symbol to analyze (e.g. AAPL, bitcoin).")
@click.option("--db", default="data/marketpulse.db",
              help="SQLite database path.")
def analyze(ticker, db):
    """Run technical analysis on a specific ticker from the database."""
    from marketpulse.analysis.technical import compute_all_indicators

    if not Path(db).exists():
        click.echo(f"❌  Database not found: {db}", err=True)
        sys.exit(1)

    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT date, open, high, low, close, volume "
        "FROM historical_prices WHERE ticker=? ORDER BY date",
        (ticker,)
    ).fetchall()
    conn.close()

    if not rows:
        click.echo(f"❌  No historical data found for {ticker}.", err=True)
        sys.exit(1)

    history = [
        {"date": r[0], "open": r[1], "high": r[2],
         "low": r[3], "close": r[4], "volume": r[5]}
        for r in rows
    ]

    result = compute_all_indicators(history, ticker)
    summary = result.get("summary", {})
    latest  = result.get("latest", {})

    click.echo(f"\n📊  Technical Analysis — {ticker}")
    click.echo("─" * 44)
    click.echo(f"  Last close:    {latest.get('close', 'N/A')}")
    click.echo(f"  MA20:          {latest.get('ma20', 'N/A')}")
    click.echo(f"  MA50:          {latest.get('ma50', 'N/A')}")
    click.echo(f"  MA200:         {latest.get('ma200', 'N/A')}")
    click.echo(f"  RSI(14):       {latest.get('rsi', 'N/A')}  → {summary.get('rsi_signal', '')}")
    click.echo(f"  MACD:          {latest.get('macd', 'N/A')}  → {summary.get('macd_signal', '')}")
    click.echo(f"  BB Upper:      {latest.get('bb_upper', 'N/A')}")
    click.echo(f"  BB Lower:      {latest.get('bb_lower', 'N/A')}")
    click.echo(f"  Trend:         {summary.get('trend', 'N/A')}")
    click.echo("")


# ── export ────────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--db", default="data/marketpulse.db")
@click.option("--format", "fmt", default="json",
              type=click.Choice(["json", "csv"]))
@click.option("--output", "-o", default="data/export")
@click.option("--market", default=None,
              type=click.Choice(["US", "EU", None]), help="Filter by market.")
@click.option("--min-cap", default=None, type=float,
              help="Minimum market cap (USD).")
def export(db, fmt, output, market, min_cap):
    """Re-export data from the SQLite database."""
    if not Path(db).exists():
        click.echo(f"❌  Database not found: {db}", err=True)
        sys.exit(1)

    Path(output).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM stock_quotes WHERE 1=1"
    params = []
    if market:
        query += " AND market=?"
        params.append(market)
    if min_cap:
        query += " AND market_cap >= ?"
        params.append(min_cap)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    data = [dict(r) for r in rows]

    if fmt == "json":
        path = os.path.join(output, "quotes_export.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    else:
        import csv
        path = os.path.join(output, "quotes_export.csv")
        if data:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

    click.echo(f"✅  Exported {len(data)} records → {path}")


# ── stats ─────────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--db", default="data/marketpulse.db")
def stats(db):
    """Show database statistics."""
    if not Path(db).exists():
        click.echo(f"❌  Database not found: {db}", err=True)
        sys.exit(1)

    conn = sqlite3.connect(db)
    q = lambda sql: conn.execute(sql).fetchone()[0]

    click.echo("\n📊  MarketPulse — Database Statistics")
    click.echo("─" * 44)
    click.echo(f"  Stock quotes     : {q('SELECT COUNT(*) FROM stock_quotes'):>8,}")
    us_count = q("SELECT COUNT(*) FROM stock_quotes WHERE market='US'")
    eu_count = q("SELECT COUNT(*) FROM stock_quotes WHERE market='EU'")
    click.echo(f"  US stocks        : {us_count:>8,}")
    click.echo(f"  EU stocks        : {eu_count:>8,}")
    click.echo(f"  Fundamentals     : {q('SELECT COUNT(*) FROM stock_fundamentals'):>8,}")
    click.echo(f"  Historical rows  : {q('SELECT COUNT(*) FROM historical_prices'):>8,}")
    click.echo(f"  Crypto quotes    : {q('SELECT COUNT(*) FROM crypto_quotes'):>8,}")

    top = conn.execute(
        "SELECT ticker, price FROM stock_quotes ORDER BY market_cap DESC NULLS LAST LIMIT 5"
    ).fetchall()
    if top:
        click.echo("\n  Top 5 by market cap:")
        for row in top:
            click.echo(f"    {row[0]:<12} ${row[1] or 0:>10,.2f}")

    conn.close()
    click.echo("")


if __name__ == "__main__":
    cli()

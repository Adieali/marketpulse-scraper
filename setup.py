from setuptools import setup, find_packages

setup(
    name="marketpulse-scraper",
    version="1.0.0",
    description="Professional financial market data scraper — US, EU & Crypto",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "scrapy>=2.11",
        "scrapy-playwright>=0.0.33",
        "yfinance>=0.2.36",
        "pandas>=2.1",
        "click>=8.1",
        "pyyaml>=6.0",
        "itemadapter>=0.9",
        "requests>=2.31",
    ],
    entry_points={
        "console_scripts": [
            "mp-scraper=cli.main:cli",
        ],
    },
)

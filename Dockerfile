FROM python:3.11-slim

# Install system deps for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libxml2-dev libxslt-dev zlib1g-dev \
    wget curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps

COPY . .
RUN pip install -e .

RUN useradd -m scraper && chown -R scraper:scraper /app
USER scraper

RUN mkdir -p data web/data

ENTRYPOINT ["mp-scraper"]
CMD ["scrape", "--market", "all"]

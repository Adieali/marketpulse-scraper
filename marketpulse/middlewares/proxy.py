"""Proxy rotation middleware."""
import logging
import os
import random

import yaml

logger = logging.getLogger(__name__)


class ProxyRotationMiddleware:
    def __init__(self, proxies=None, enabled=False):
        self.proxies = proxies or []
        self.enabled = enabled

    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool("PROXY_ENABLED", False)
        proxies = []
        if enabled:
            env_proxies = os.getenv("PROXIES", "")
            if env_proxies:
                proxies = [p.strip() for p in env_proxies.split(",") if p.strip()]
            else:
                proxy_file = crawler.settings.get("PROXY_FILE", "config/proxies.yaml")
                try:
                    with open(proxy_file) as f:
                        data = yaml.safe_load(f)
                        proxies = data.get("proxies", [])
                except FileNotFoundError:
                    logger.warning(f"Proxy file not found: {proxy_file}")
        return cls(proxies=proxies, enabled=enabled)

    def process_request(self, request, spider):
        if self.enabled and self.proxies:
            request.meta["proxy"] = random.choice(self.proxies)

    def process_response(self, request, response, spider):
        if response.status in (403, 429):
            proxy = request.meta.get("proxy", "direct")
            logger.warning(f"Soft ban detected ({response.status}) via {proxy}")
        return response

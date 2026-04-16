"""Smart retry middleware with soft-ban detection."""
import logging

from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message

logger = logging.getLogger(__name__)

BAN_PATTERNS = [
    "access denied", "captcha", "too many requests",
    "rate limit", "blocked", "forbidden",
]


class RetryOnBanMiddleware(RetryMiddleware):
    def process_response(self, request, response, spider):
        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response

        # Soft-ban detection via response body
        if response.status == 200:
            body = response.text.lower()
            if any(p in body for p in BAN_PATTERNS):
                logger.warning(f"Soft ban detected on {request.url}")
                return self._retry(request, "soft_ban", spider) or response

        return response

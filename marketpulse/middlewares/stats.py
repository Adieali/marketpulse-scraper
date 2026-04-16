"""Custom stats middleware — tracks items/sec and per-spider counters."""
import time
import logging

logger = logging.getLogger(__name__)


class StatsMiddleware:
    def __init__(self):
        self._start = time.time()
        self._count = 0

    def process_response(self, request, response, spider):
        self._count += 1
        elapsed = time.time() - self._start
        if self._count % 50 == 0:
            rate = self._count / max(elapsed, 1)
            logger.info(f"[Stats] {self._count} responses | {rate:.1f} req/s")
        return response

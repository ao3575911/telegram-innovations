"""Bounded in-memory token buckets; keys are ephemeral pseudonyms."""

import time
from collections import OrderedDict


class RateLimiter:
    def __init__(self, capacity: int = 10, refill: float = 1.0, max_keys: int = 10000):
        self.capacity = capacity
        self.refill = refill
        self.max_keys = max_keys
        self.buckets: OrderedDict[str, tuple[float, float]] = OrderedDict()

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        tokens, last = self.buckets.pop(key, (float(self.capacity), now))
        tokens = min(self.capacity, tokens + max(0, now - last) * self.refill)
        allowed = tokens >= 1
        self.buckets[key] = (tokens - 1 if allowed else tokens, now)
        while len(self.buckets) > self.max_keys:
            self.buckets.popitem(last=False)
        return allowed

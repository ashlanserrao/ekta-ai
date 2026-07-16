import time
from collections import defaultdict
from backend.app.config import settings

class IPBasedRateLimiter:
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self.request_timestamps = defaultdict(list)

    def is_rate_limited(self, ip: str) -> bool:
        now = time.time()
        # Filter timestamps within window
        self.request_timestamps[ip] = [t for t in self.request_timestamps[ip] if now - t < self.window]
        
        if len(self.request_timestamps[ip]) >= self.limit:
            return True
            
        self.request_timestamps[ip].append(now)
        return False

chat_limiter = IPBasedRateLimiter(limit=settings.RATE_LIMIT_LIMIT, window=settings.RATE_LIMIT_WINDOW)
staff_limiter = IPBasedRateLimiter(limit=30, window=10)

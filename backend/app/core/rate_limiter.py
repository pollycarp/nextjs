"""
Simple in-process rate limiter — Phase 7.

Tracks requests per key (IP or user) in a sliding window.
Uses no external dependencies to avoid Python-3.14 compatibility issues.
"""

from collections import defaultdict
from time import time

# Module-level state — can be patched in tests
MAX_REQUESTS: int = 20
WINDOW_SECONDS: int = 60

_store: dict[str, list[float]] = defaultdict(list)


def reset() -> None:
    """Clear all state — called between tests."""
    _store.clear()


def is_allowed(key: str) -> bool:
    """Return True if the key is within the rate limit."""
    now = time()
    cutoff = now - WINDOW_SECONDS
    _store[key] = [t for t in _store[key] if t > cutoff]
    if len(_store[key]) >= MAX_REQUESTS:
        return False
    _store[key].append(now)
    return True

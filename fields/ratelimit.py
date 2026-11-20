"""Tiny fixed-window rate limiter on Django's cache."""

from __future__ import annotations

from django.core.cache import cache


def allow(key: str, limit: int, window_s: int) -> bool:
    cache_key = f"rl:{key}"
    if cache.add(cache_key, 1, window_s):
        return True
    try:
        count = int(cache.incr(cache_key))
    except ValueError:  # key expired between add() and incr()
        cache.set(cache_key, 1, window_s)
        return True
    return count <= limit

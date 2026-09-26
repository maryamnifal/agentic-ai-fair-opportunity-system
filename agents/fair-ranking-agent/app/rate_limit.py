"""
Rate limiting (Member D's security scope: "Rate limiting").

A simple in-memory FIXED-WINDOW counter per client key (authenticated
username if available, else client IP). Deliberately not a distributed
solution (e.g. Redis-backed) -- this is a university project running as a
single process, so an in-memory dict is sufficient and easy to explain:

  "Each client gets N requests per rolling window of W seconds. Requests
   beyond that get HTTP 429 with a Retry-After header until the window
   resets."
"""

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

MAX_REQUESTS = 10
WINDOW_SECONDS = 60

_hits: Dict[str, Deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    # Prefer the authenticated user if the auth dependency already ran and
    # attached it to request.state; otherwise fall back to client IP.
    user = getattr(request.state, "username", None)
    if user:
        return f"user:{user}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


def rate_limit(request: Request) -> None:
    key = _client_key(request)
    now = time.monotonic()
    window_start = now - WINDOW_SECONDS

    hits = _hits[key]
    while hits and hits[0] < window_start:
        hits.popleft()

    if len(hits) >= MAX_REQUESTS:
        retry_after = int(WINDOW_SECONDS - (now - hits[0])) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: max {MAX_REQUESTS} requests per {WINDOW_SECONDS}s.",
            headers={"Retry-After": str(retry_after)},
        )

    hits.append(now)


def reset_rate_limits_for_tests() -> None:
    _hits.clear()

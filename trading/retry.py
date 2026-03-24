"""
Retry handler for transient API and network errors.
"""
import time
import functools
import logging
from typing import Callable, Any

import requests.exceptions
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class RetryHandler:
    """Wraps any callable with retry-on-transient-error logic."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call func(*args, **kwargs), retrying up to max_retries times on
        transient errors with exponential back-off.
        Raises the original exception after all retries are exhausted.
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except BinanceAPIException as exc:
                # Non-transient 4xx (400-499 except 429): propagate immediately
                if 400 <= exc.status_code <= 499 and exc.status_code != 429:
                    raise

                # Transient: only retry if status code is in TRANSIENT_STATUS_CODES
                if exc.status_code not in TRANSIENT_STATUS_CODES:
                    raise

                last_exception = exc

                if attempt == self.max_retries:
                    break

                # HTTP 429 with Retry-After header overrides back-off
                if exc.status_code == 429:
                    retry_after = self._get_retry_after(exc)
                    if retry_after is not None:
                        time.sleep(retry_after)
                        continue

                delay = 2 ** attempt
                time.sleep(delay)

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                last_exception = exc

                if attempt == self.max_retries:
                    break

                delay = 2 ** attempt
                time.sleep(delay)

        logger.error(
            "All %d retry attempts exhausted. Last error: %s",
            self.max_retries,
            last_exception,
        )
        raise last_exception

    @staticmethod
    def _get_retry_after(exc: BinanceAPIException):
        """Extract Retry-After header value from a BinanceAPIException, if present."""
        response = getattr(exc, "response", None)
        if response is None:
            return None
        headers = getattr(response, "headers", {}) or {}
        value = headers.get("Retry-After")
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
        return None


def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator that wraps a BinanceClient method with RetryHandler.execute."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = RetryHandler(max_retries=max_retries, base_delay=base_delay)
            return handler.execute(func, *args, **kwargs)
        return wrapper
    return decorator

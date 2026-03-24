"""
Unit tests for trading/retry.py — RetryHandler and with_retry decorator.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from binance.exceptions import BinanceAPIException

from trading.retry import RetryHandler, with_retry, TRANSIENT_STATUS_CODES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_binance_exc(status_code: int, retry_after: str = None) -> BinanceAPIException:
    """Build a BinanceAPIException with an optional Retry-After header."""
    response = MagicMock()
    response.status_code = status_code
    headers = {}
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    response.headers = headers
    exc = BinanceAPIException(response, status_code, '{"code": -1, "msg": "error"}')
    exc.status_code = status_code
    exc.response = response
    return exc


# ---------------------------------------------------------------------------
# TRANSIENT_STATUS_CODES
# ---------------------------------------------------------------------------

def test_transient_status_codes_contains_expected():
    assert TRANSIENT_STATUS_CODES == {429, 500, 502, 503, 504}


# ---------------------------------------------------------------------------
# RetryHandler — success on first call
# ---------------------------------------------------------------------------

def test_execute_returns_result_on_success():
    handler = RetryHandler(max_retries=3)
    func = MagicMock(return_value=42)
    assert handler.execute(func, "a", b=1) == 42
    func.assert_called_once_with("a", b=1)


# ---------------------------------------------------------------------------
# RetryHandler — transient 5xx retries
# ---------------------------------------------------------------------------

@patch("trading.retry.time.sleep")
def test_execute_retries_on_500(mock_sleep):
    exc = make_binance_exc(500)
    func = MagicMock(side_effect=[exc, exc, 99])
    handler = RetryHandler(max_retries=3)
    result = handler.execute(func)
    assert result == 99
    assert func.call_count == 3
    # back-off: 2^0=1, 2^1=2
    mock_sleep.assert_has_calls([call(1), call(2)])


@patch("trading.retry.time.sleep")
def test_execute_exhausts_retries_and_raises(mock_sleep):
    exc = make_binance_exc(503)
    func = MagicMock(side_effect=exc)
    handler = RetryHandler(max_retries=3)
    with pytest.raises(BinanceAPIException) as exc_info:
        handler.execute(func)
    assert exc_info.value is exc
    assert func.call_count == 4  # initial + 3 retries


@patch("trading.retry.time.sleep")
def test_execute_exponential_backoff_delays(mock_sleep):
    exc = make_binance_exc(502)
    func = MagicMock(side_effect=[exc, exc, exc, exc])
    handler = RetryHandler(max_retries=3)
    with pytest.raises(BinanceAPIException):
        handler.execute(func)
    # delays: 2^0=1, 2^1=2, 2^2=4
    mock_sleep.assert_has_calls([call(1), call(2), call(4)])


# ---------------------------------------------------------------------------
# RetryHandler — HTTP 429 with Retry-After header
# ---------------------------------------------------------------------------

@patch("trading.retry.time.sleep")
def test_execute_uses_retry_after_header_for_429(mock_sleep):
    exc = make_binance_exc(429, retry_after="7")
    func = MagicMock(side_effect=[exc, "ok"])
    handler = RetryHandler(max_retries=3)
    result = handler.execute(func)
    assert result == "ok"
    mock_sleep.assert_called_once_with(7.0)


@patch("trading.retry.time.sleep")
def test_execute_uses_backoff_for_429_without_retry_after(mock_sleep):
    exc = make_binance_exc(429)  # no Retry-After header
    func = MagicMock(side_effect=[exc, "ok"])
    handler = RetryHandler(max_retries=3)
    result = handler.execute(func)
    assert result == "ok"
    mock_sleep.assert_called_once_with(1)  # 2^0


# ---------------------------------------------------------------------------
# RetryHandler — non-transient 4xx propagates immediately
# ---------------------------------------------------------------------------

@patch("trading.retry.time.sleep")
def test_execute_propagates_non_transient_4xx_immediately(mock_sleep):
    exc = make_binance_exc(400)
    func = MagicMock(side_effect=exc)
    handler = RetryHandler(max_retries=3)
    with pytest.raises(BinanceAPIException) as exc_info:
        handler.execute(func)
    assert exc_info.value is exc
    func.assert_called_once()
    mock_sleep.assert_not_called()


@patch("trading.retry.time.sleep")
def test_execute_propagates_403_immediately(mock_sleep):
    exc = make_binance_exc(403)
    func = MagicMock(side_effect=exc)
    handler = RetryHandler(max_retries=3)
    with pytest.raises(BinanceAPIException):
        handler.execute(func)
    func.assert_called_once()
    mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# RetryHandler — network errors (ConnectionError, Timeout)
# ---------------------------------------------------------------------------

@patch("trading.retry.time.sleep")
def test_execute_retries_on_connection_error(mock_sleep):
    import requests.exceptions
    err = requests.exceptions.ConnectionError("network down")
    func = MagicMock(side_effect=[err, err, "recovered"])
    handler = RetryHandler(max_retries=3)
    result = handler.execute(func)
    assert result == "recovered"
    assert func.call_count == 3


@patch("trading.retry.time.sleep")
def test_execute_retries_on_timeout(mock_sleep):
    import requests.exceptions
    err = requests.exceptions.Timeout("timed out")
    func = MagicMock(side_effect=[err, "ok"])
    handler = RetryHandler(max_retries=3)
    result = handler.execute(func)
    assert result == "ok"
    assert func.call_count == 2


# ---------------------------------------------------------------------------
# RetryHandler — logs error after exhaustion
# ---------------------------------------------------------------------------

@patch("trading.retry.time.sleep")
def test_execute_logs_error_after_exhaustion(mock_sleep):
    exc = make_binance_exc(500)
    func = MagicMock(side_effect=exc)
    handler = RetryHandler(max_retries=2)
    with patch("trading.retry.logger") as mock_logger:
        with pytest.raises(BinanceAPIException):
            handler.execute(func)
        mock_logger.error.assert_called_once()


# ---------------------------------------------------------------------------
# with_retry decorator
# ---------------------------------------------------------------------------

@patch("trading.retry.time.sleep")
def test_with_retry_decorator_wraps_function(mock_sleep):
    @with_retry(max_retries=2)
    def my_func(x):
        return x * 2

    assert my_func(5) == 10


@patch("trading.retry.time.sleep")
def test_with_retry_decorator_retries_on_transient_error(mock_sleep):
    exc = make_binance_exc(503)
    call_count = {"n": 0}

    @with_retry(max_retries=2)
    def flaky():
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise exc
        return "done"

    result = flaky()
    assert result == "done"
    assert call_count["n"] == 3


@patch("trading.retry.time.sleep")
def test_with_retry_preserves_function_name(mock_sleep):
    @with_retry()
    def my_named_func():
        pass

    assert my_named_func.__name__ == "my_named_func"

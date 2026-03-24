"""
Risk management controls for the trading bot.
Enforces configurable limits before order submission.
"""
import os
from datetime import datetime, timezone
from utils.logger import get_logger

logger = get_logger("RiskGuard")


class RiskLimitExceeded(Exception):
    """Raised when an order would breach a configured risk limit."""


class RiskGuard:
    """Enforces risk limits read from environment variables at construction."""

    def __init__(self):
        self.max_position_size = self._read_env("MAX_POSITION_SIZE_USDT")
        self.daily_loss_limit = self._read_env("DAILY_LOSS_LIMIT_USDT")
        self.max_order_notional = self._read_env("MAX_ORDER_NOTIONAL_USDT")
        # {date_str: cumulative_loss} e.g. {"2026-03-19": 42.5}
        self._daily_losses: dict[str, float] = {}

    def _read_env(self, var: str) -> float | None:
        raw = os.environ.get(var)
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            logger.warning(f"RiskGuard: env var {var}={raw!r} is non-numeric; limit disabled")
            return None

    def _today_utc(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def check_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        current_position_notional: float = 0.0,
    ) -> None:
        """
        Raises RiskLimitExceeded if any configured limit is breached.
        No-ops for limits whose env var was absent or invalid.
        """
        order_notional = quantity * price

        if self.max_order_notional is not None and order_notional > self.max_order_notional:
            msg = (
                f"Order rejected: notional {order_notional:.4f} USDT exceeds "
                f"MAX_ORDER_NOTIONAL_USDT={self.max_order_notional:.4f} "
                f"(symbol={symbol}, side={side})"
            )
            logger.warning(msg)
            raise RiskLimitExceeded(msg)

        if self.max_position_size is not None:
            resulting_notional = current_position_notional + order_notional
            if resulting_notional > self.max_position_size:
                msg = (
                    f"Order rejected: resulting position notional {resulting_notional:.4f} USDT "
                    f"exceeds MAX_POSITION_SIZE_USDT={self.max_position_size:.4f} "
                    f"(symbol={symbol}, side={side})"
                )
                logger.warning(msg)
                raise RiskLimitExceeded(msg)

        if self.daily_loss_limit is not None:
            today = self._today_utc()
            cumulative = self._daily_losses.get(today, 0.0)
            if cumulative >= self.daily_loss_limit:
                msg = (
                    f"Order rejected: cumulative daily loss {cumulative:.4f} USDT "
                    f"has reached DAILY_LOSS_LIMIT_USDT={self.daily_loss_limit:.4f} "
                    f"(symbol={symbol}, side={side})"
                )
                logger.warning(msg)
                raise RiskLimitExceeded(msg)

    def record_realised_loss(self, loss_usdt: float) -> None:
        """Add loss_usdt to the in-memory cumulative loss for today (UTC)."""
        today = self._today_utc()
        self._daily_losses[today] = self._daily_losses.get(today, 0.0) + loss_usdt

"""
Position Manager for the Trading Bot.
Handles querying open positions and closing them via reduce-only market orders.
"""
from typing import Any, Dict, List

from trading.client import BinanceClient


class PositionManager:
    """Manages open futures positions: listing and closing."""

    def __init__(self, client: BinanceClient) -> None:
        self.client = client

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Retrieve all open USDT-M futures positions.

        Calls futures_position_information() with no symbol filter and returns
        only entries where positionAmt != 0.
        """
        all_positions = self.client.client.futures_position_information()
        return [p for p in all_positions if float(p["positionAmt"]) != 0]

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Close the open position for *symbol* with a reduce-only MARKET order.

        Raises ValueError if there is no open position for the symbol.
        """
        all_positions = self.client.client.futures_position_information()
        position = next(
            (p for p in all_positions if p["symbol"] == symbol), None
        )

        if position is None or float(position["positionAmt"]) == 0:
            raise ValueError(f"No open position for {symbol}")

        position_amt = float(position["positionAmt"])
        side = "SELL" if position_amt > 0 else "BUY"
        quantity = abs(position_amt)

        return self.client.place_market_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            reduce_only=True,
        )

"""
Output formatters for the Binance Trading Bot.
Provides formatted output for CLI display.
"""
from typing import Dict, List, Any
from tabulate import tabulate
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f"{Fore.CYAN}{text.center(60)}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")


def print_success(text: str):
    """Print success message in green."""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")


def print_error(text: str):
    """Print error message in red."""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")


def print_warning(text: str):
    """Print warning message in yellow."""
    print(f"{Fore.YELLOW}⚠ {text}{Style.RESET_ALL}")


def print_info(text: str):
    """Print info message."""
    print(f"{Fore.BLUE}ℹ {text}{Style.RESET_ALL}")


def print_order_table(orders: List[Dict[str, Any]]):
    """Format and print orders in a table."""
    if not orders:
        print_warning("No orders to display")
        return
    
    headers = ["Order ID", "Symbol", "Side", "Type", "Quantity", "Price", "Status"]
    rows = []
    
    for order in orders:
        row = [
            str(order.get('orderId', 'N/A')),
            order.get('symbol', 'N/A'),
            order.get('side', 'N/A'),
            order.get('type', 'N/A'),
            order.get('origQty', 'N/A'),
            order.get('price', 'N/A'),
            order.get('status', 'N/A')
        ]
        rows.append(row)
    
    print(tabulate(rows, headers=headers, tablefmt="simple"))


def print_balance(balances: Dict[str, Any]):
    """Format and print account balance."""
    print_header("Account Balance")
    
    data = [
        ["Asset", "Wallet Balance", "Available Balance", "Profit/Loss"],
        [
            balances.get('asset', 'USDT'),
            balances.get('walletBalance', '0'),
            balances.get('availableBalance', '0'),
            balances.get('unrealizedProfit', '0')
        ]
    ]
    
    print(tabulate(data[1:], headers=data[0], tablefmt="simple"))


def print_position(position: Dict[str, Any]):
    """Format and print position information."""
    print_header("Position Info")
    
    data = [
        ["Symbol", "Size", "Entry Price", "Mark Price", "PnL", "Leverage"],
        [
            position.get('symbol', 'N/A'),
            position.get('positionAmt', '0'),
            position.get('entryPrice', '0'),
            position.get('markPrice', '0'),
            position.get('unrealizedProfit', '0'),
            position.get('leverage', '1') + 'x'
        ]
    ]
    
    print(tabulate(data[1:], headers=data[0], tablefmt="simple"))


def print_ticker(ticker: Dict[str, Any]):
    """Format and print ticker information."""
    data = [
        ["Property", "Value"],
        ["Symbol", ticker.get('symbol', 'N/A')],
        ["Last Price", ticker.get('lastPrice', 'N/A')],
        ["24h Change", ticker.get('priceChangePercent', 'N/A') + '%'],
        ["24h High", ticker.get('highPrice', 'N/A')],
        ["24h Low", ticker.get('lowPrice', 'N/A')],
        ["24h Volume", ticker.get('volume', 'N/A')],
    ]
    
    print(tabulate(data[1:], headers=data[0], tablefmt="simple"))


def print_order_details(order: Dict[str, Any]):
    """Format and print detailed order information."""
    print_header("Order Details")
    
    exclude_keys = ['clientOrderId', 'time', 'updateTime', 'workingType', 'priceProtect']
    
    data = [[key.capitalize(), str(value)] for key, value in order.items() if key not in exclude_keys]
    
    print(tabulate(data, tablefmt="simple"))


def print_menu(options: List[tuple]):
    """Print a numbered menu."""
    print_header("Main Menu")
    
    for i, (key, description) in enumerate(options, 1):
        print(f"{Fore.YELLOW}{i}.{Style.RESET_ALL} {description}")
    
    print()


def format_price(price: float, precision: int = 2) -> str:
    """Format price with specified precision."""
    return f"{price:.{precision}f}"


def format_quantity(quantity: float, precision: int = 4) -> str:
    """Format quantity with specified precision."""
    return f"{quantity:.{precision}f}"


def format_percentage(value: float) -> str:
    """Format value as percentage."""
    return f"{value:+.2f}%"


def get_side_color(side: str) -> str:
    """Get color for trade side."""
    if side.upper() == 'BUY':
        return Fore.GREEN
    elif side.upper() == 'SELL':
        return Fore.RED
    return Fore.WHITE


def get_status_color(status: str) -> str:
    """Get color for order status."""
    status_upper = status.upper()
    if status_upper == 'NEW':
        return Fore.BLUE
    elif status_upper == 'FILLED':
        return Fore.GREEN
    elif status_upper == 'PARTIALLY_FILLED':
        return Fore.YELLOW
    elif status_upper == 'CANCELLED':
        return Fore.RED
    elif status_upper == 'EXPIRED':
        return Fore.MAGENTA
    return Fore.WHITE

import math
from typing import Optional, Dict, Any


def compute_mid_price(order_book: Dict[str, Any]) -> Optional[float]:
    """
    Estimate the mark price using multiple order book and ticker metrics in priority order.

    Priority:
    1. Mid-price from best_bid and best_ask
    2. One-sided estimation using only best_bid or best_ask
    3. Last traded price
    4. Settlement price
    5. Average of min_price and max_price
    6. Return None if no reliable data found

    Args:
        order_book (Dict[str, Any]): The order book data from Deribit.

    Returns:
        Optional[float]: Estimated mark price, or None if no valid estimation is possible.
    """
    try:
        bid = order_book.get("best_bid_price")
        ask = order_book.get("best_ask_price")
        last = order_book.get("last_price")
        settlement = order_book.get("settlement_price")
        min_price = order_book.get("min_price")
        max_price = order_book.get("max_price")

        if bid and ask and bid > 0 and ask > 0:
            return (bid + ask) / 2

        if bid and bid > 0:
            return bid
        if ask and ask > 0:
            return ask

        if last is not None:
            return last

        if settlement is not None:
            return settlement

        if min_price is not None and max_price is not None and min_price > 0 and max_price > 0:
            return (min_price + max_price) / 2

    except Exception as e:
        print(f"[Warning] Failed to compute mark price: {e}")

    return None


def norm_cdf(x: float) -> float:
    """
    Compute the cumulative distribution function for a standard normal distribution.

    Args:
        x (float): Input value.

    Returns:
        float: CDF value at x.
    """
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def compute_black76_mark_price(ticker: Dict[str, Any], inst_data: Dict[str, Any]) -> Optional[float]:
    """
    Compute the option mark price using the Black-76 model.

    Args:
        ticker (Dict[str, Any]): Ticker data from Deribit.
        inst_data (Dict[str, Any]): Instrument metadata (including strike and expiration).

    Returns:
        Optional[float]: Black-76 mark price normalized by spot price, or None if computation fails.
    """
    try:
        S = float(ticker.get("underlying_price"))
        K = float(inst_data.get("strike"))
        r = float(ticker.get("interest_rate", 0.0))
        sigma = float(ticker.get("mark_iv", 0.0)) / 100
        option_type = inst_data.get("option_type")

        t_now = float(ticker.get("timestamp"))
        t_exp = float(inst_data.get("expiration_timestamp"))
        T = max((t_exp - t_now) / 1000 / 60 / 60 / 24 / 365, 1e-8)

        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None

        F = S * math.exp(r * T)

        d1 = (math.log(F / K) + 0.5 * sigma ** 2 * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        discount = math.exp(-r * T)

        if option_type == "call":
            price = discount * (F * norm_cdf(d1) - K * norm_cdf(d2))
        elif option_type == "put":
            price = discount * (K * norm_cdf(-d2) - F * norm_cdf(-d1))
        else:
            return None

        return price / S

    except Exception as e:
        print(f"[compute_black76_mark_price] Error: {e}")
        return None

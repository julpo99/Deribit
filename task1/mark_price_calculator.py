import math


def compute_mid_price(order_book):
    """
    Robust mark price estimation using all available order book and ticker data.
    Priority:
    1. Mid of best_bid and best_ask (if both present and > 0)
    2. One-sided estimation if only one is present and > 0 (I don't think this case is possible with real life data,
        so it will be skipped)
    3. last_price
    4. settlement_price
    5. average of min_price and max_price
    6. return None if all else fails
    """
    try:
        bid = order_book.get("best_bid_price")
        ask = order_book.get("best_ask_price")
        last = order_book.get("last_price")
        settlement = order_book.get("settlement_price")
        min = order_book.get("min_price")
        max = order_book.get("max_price")

        # 1. Mid-price
        if bid and ask and bid > 0 and ask > 0:
            # print(f'[Debug] Mid-price estimation: bid={bid}, ask={ask}')
            return (bid + ask) / 2

        # 2. One-sided
        if bid and bid > 0:
            # print(f'[Debug] One-sided estimation: bid={bid}')
            return bid
        if ask and ask > 0:
            # print(f'[Debug] One-sided estimation: ask={ask}')
            return ask

        # 3. Last traded price
        if last is not None:
            # print(f'[Debug] Last traded price estimation: last={last}')
            return last

        # 4. Settlement price
        if settlement is not None:
            # print(f'[Debug] Settlement price: settlement={settlement}')
            return settlement

        # 5. Average of min/max (if non-zero and both exist)
        if min is not None and max is not None and min > 0 and max > 0:
            # print(f'[Debug] Average of min/max estimation: min={min}, max={max}')
            return (min + max) / 2

    except Exception as e:
        print(f"[Warning] Failed to compute mark price: {e}")

    # 6. Total failure :/
    return None


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def compute_black76_mark_price(ticker, inst_data):
    """
    Compute the mark price using the Black-76 model,
    based on ticker info and instrument data
    """

    try:
        S = float(ticker.get("underlying_price"))
        K = float(inst_data.get("strike"))
        r = float(ticker.get("interest_rate", 0.0))
        sigma = float(ticker.get("mark_iv", 0.0)) / 100
        option_type = inst_data.get("option_type")

        # Time to expiry in years
        t_now = float(ticker.get("timestamp"))
        t_exp = float(inst_data.get("expiration_timestamp"))
        T = max((t_exp - t_now) / 1000 / 60 / 60 / 24 / 365, 1e-8)

        # Check
        if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
            return None

        # Forward price
        F = S * math.exp(r * T)

        # Black-76 formula
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

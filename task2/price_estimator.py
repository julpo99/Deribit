import json
from typing import Dict, Optional, Union

import numpy as np
import pandas as pd
from pandas import DataFrame

from config import CRYPTOS, AMOUNTS, DATA_DIR


def estimate_price_std(merged_df: DataFrame, label: str, save_debug: bool = False) -> Dict[
    str, Union[int, str, float, Dict[str, Optional[float]]]]:
    """Estimate price based on standard deviation minimization.

    Args:
        merged_df (DataFrame): DataFrame containing merged price data by timestamp.
        label (str): Label for dataset, e.g., "testnet" or "mainnet".
        save_debug (bool): Whether to save debug output (JSON, NumPy array).
    Returns:
        Dict[str, Union[int, str, float, Dict[str, Optional[float]]]]: Dictionary containing the best match details.
    """
    merged_array = merged_df[CRYPTOS].to_numpy()
    merged_array = np.where(merged_array == 0, np.nan, merged_array)

    amount_vector = np.array([AMOUNTS[f"{crypto}_USDC"] for crypto in CRYPTOS])
    prices = merged_array * amount_vector

    valid_counts = np.sum(~np.isnan(prices), axis=1)
    enough_data_mask = valid_counts > 2

    filtered_prices = prices[enough_data_mask]
    filtered_stds = np.nanstd(filtered_prices, axis=1)
    filtered_avgs = np.nanmean(filtered_prices, axis=1)
    filtered_timestamps = merged_df.index[enough_data_mask]

    best_idx = np.nanargmin(filtered_stds)
    timestamp = int(filtered_timestamps[best_idx])
    human_date = pd.to_datetime(timestamp, unit="ms", utc=True).isoformat()
    avg_price = round(float(filtered_avgs[best_idx]), 6)
    std_dev = round(float(filtered_stds[best_idx]), 6)
    prices = filtered_prices[best_idx]

    with open(DATA_DIR / f"best_match_std_{label}.json", "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "date": human_date,
            "price_usd": avg_price,
            "std": std_dev,
            "prices": {
                f"{crypto}_USDC": (round(float(prices[i]), 6) if not np.isnan(prices[i]) else None)
                for i, crypto in enumerate(CRYPTOS)
            }
        }, f, indent=2)

    if save_debug:
        print(f"\nBest match for {label}:")
        print(f"Timestamp: {timestamp} ({human_date}) | Price: ${avg_price:.4f} | Std: {std_dev:.6f}")
        for i, crypto in enumerate(CRYPTOS):
            val = prices[i]
            print(f"  {crypto}_USDC: ${val:.4f}" if not np.isnan(val) else f"  {crypto}_USDC: MISSING")

        np.save(DATA_DIR / f"merged_prices_std_{label}.npy", merged_array)
        with open(DATA_DIR / f"merged_prices_std_{label}.json", "w", encoding="utf-8") as f:
            json.dump(merged_df.reset_index().to_dict(orient="records"), f, indent=2)
        print(f"Saved debug JSON to merged_prices_std_{label}.json")
        print(f"Saved merged numpy array to merged_prices_std_{label}.npy")

    return {"timestamp": timestamp, "date": human_date, "price_usd": avg_price, "std": std_dev,
            "prices": {f"{crypto}_USDC": (round(float(prices[i]), 6) if not np.isnan(prices[i]) else None) for i, crypto
                       in enumerate(CRYPTOS)}, "label" : label}


def estimate_price_mad(merged_df: DataFrame, label: str, save_debug: bool = False) -> Dict[
    str, Union[int, str, float, Dict[str, Optional[float]]]]:
    """Estimate price using Mean Absolute Deviation (MAD) minimization.

    Args:
        merged_df (DataFrame): Merged DataFrame of price data per crypto.
        label (str): Dataset label (e.g., "testnet" or "mainnet").
        save_debug (bool): If True, saves output as JSON and NumPy.
    Returns:
        Dict[str, Union[int, str, float, Dict[str, Optional[float]]]]: Dictionary containing the best match details.
    """
    merged_array = merged_df[CRYPTOS].to_numpy()
    merged_array = np.where(merged_array == 0, np.nan, merged_array)

    amount_vector = np.array([AMOUNTS[f"{crypto}_USDC"] for crypto in CRYPTOS])
    prices = merged_array * amount_vector

    valid_counts = np.sum(~np.isnan(prices), axis=1)
    valid_mask = valid_counts > 2

    filtered_prices = prices[valid_mask]
    filtered_mads = np.nanmean(np.abs(filtered_prices - np.nanmean(filtered_prices, axis=1, keepdims=True)), axis=1)
    filtered_avgs = np.nanmean(filtered_prices, axis=1)
    filtered_timestamps = merged_df.index[valid_mask]

    best_idx = np.argmin(filtered_mads)
    timestamp = int(filtered_timestamps[best_idx])
    human_date = pd.to_datetime(timestamp, unit="ms", utc=True).isoformat()
    avg_price = round(float(filtered_avgs[best_idx]), 6)
    mad_val = round(float(filtered_mads[best_idx]), 6)
    prices = filtered_prices[best_idx]

    with open(DATA_DIR / f"best_match_mad_{label}.json", "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "date": human_date,
            "price_usd": avg_price,
            "mad": mad_val,
            "prices": {
                f"{crypto}_USDC": (round(float(prices[i]), 6) if not np.isnan(prices[i]) else None)
                for i, crypto in enumerate(CRYPTOS)
            }
        }, f, indent=2)

    if save_debug:
        print(f"\nBest MAD-based match for {label}:")
        print(f"Timestamp: {timestamp} ({human_date}) | Price: ${avg_price:.4f} | MAD: {mad_val:.6f}")
        for i, crypto in enumerate(CRYPTOS):
            val = prices[i]
            print(f"  {crypto}_USDC: ${val:.4f}" if not np.isnan(val) else f"  {crypto}_USDC: MISSING")

        np.save(DATA_DIR / f"merged_prices_mad_{label}.npy", merged_array)
        with open(DATA_DIR / f"merged_prices_mad_{label}.json", "w", encoding="utf-8") as f:
            json.dump(merged_df.reset_index().to_dict(orient="records"), f, indent=2)
        print(f"Saved debug JSON to merged_prices_mad_{label}.json")
        print(f"Saved merged numpy array to merged_prices_mad_{label}.npy")

    return {"timestamp": timestamp, "date": human_date, "price_usd": avg_price, "mad": mad_val,
            "prices": {f"{crypto}_USDC": (round(float(prices[i]), 6) if not np.isnan(prices[i]) else None) for i, crypto
                       in enumerate(CRYPTOS)}, "label" : label}


def estimate_price_min_max(merged_df: DataFrame, label: str, save_debug: bool = False) -> Dict[
    str, Union[int, str, float, Dict[str, Optional[float]]]]:
    """Estimate price using Min-Max price spread minimization.

    Args:
        merged_df (DataFrame): Merged DataFrame of crypto prices.
        label (str): Dataset label (testnet or mainnet).
        save_debug (bool): Whether to save NumPy and JSON debug outputs.
    Returns:
        Dict[str, Union[int, str, float, Dict[str, Optional[float]]]]: Dictionary containing the best match details.
    """
    merged_array = merged_df[CRYPTOS].to_numpy()
    merged_array = np.where(merged_array == 0, np.nan, merged_array)

    amount_vector = np.array([AMOUNTS[f"{crypto}_USDC"] for crypto in CRYPTOS])
    prices = merged_array * amount_vector

    valid_counts = np.sum(~np.isnan(prices), axis=1)
    valid_mask = valid_counts > 2

    filtered_prices = prices[valid_mask]
    filtered_spreads = np.nanmax(filtered_prices, axis=1) - np.nanmin(filtered_prices, axis=1)
    filtered_avgs = np.nanmean(filtered_prices, axis=1)
    filtered_timestamps = merged_df.index[valid_mask]

    best_idx = np.argmin(filtered_spreads)
    timestamp = int(filtered_timestamps[best_idx])
    human_date = pd.to_datetime(timestamp, unit="ms", utc=True).isoformat()
    avg_price = round(float(filtered_avgs[best_idx]), 6)
    spread_val = round(float(filtered_spreads[best_idx]), 6)
    prices = filtered_prices[best_idx]

    with open(DATA_DIR / f"best_match_minmax_{label}.json", "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "date": human_date,
            "price_usd": avg_price,
            "minmax": spread_val,
            "prices": {
                f"{crypto}_USDC": (round(float(prices[i]), 6) if not np.isnan(prices[i]) else None)
                for i, crypto in enumerate(CRYPTOS)
            }
        }, f, indent=2)

    if save_debug:
        print(f"\nBest Min-Max Spread match for {label}:")
        print(f"Timestamp: {timestamp} ({human_date}) | Price: ${avg_price:.4f} | Spread: {spread_val:.6f}")
        for i, crypto in enumerate(CRYPTOS):
            val = prices[i]
            print(f"  {crypto}_USDC: ${val:.4f}" if not np.isnan(val) else f"  {crypto}_USDC: MISSING")

        np.save(DATA_DIR / f"merged_prices_minmax_{label}.npy", merged_array)
        with open(DATA_DIR / f"merged_prices_minmax_{label}.json", "w", encoding="utf-8") as f:
            json.dump(merged_df.reset_index().to_dict(orient="records"), f, indent=2)
        print(f"Saved debug JSON to merged_prices_minmax_{label}.json")
        print(f"Saved merged numpy array to merged_prices_minmax_{label}.npy")

    return {"timestamp": timestamp, "date": human_date, "price_usd": avg_price, "minmax": spread_val,
            "prices": {f"{crypto}_USDC": (round(float(prices[i]), 6) if not np.isnan(prices[i]) else None) for i, crypto
                       in enumerate(CRYPTOS)}, "label" : label}

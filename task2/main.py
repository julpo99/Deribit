import argparse
import asyncio
import datetime
import json
from typing import Callable, Dict, List, Union, Optional

import pandas as pd

from config import DATA_DIR
from data_collection import collect_data, merge_data
from price_estimator import (
    estimate_price_std,
    estimate_price_mad,
    estimate_price_min_max,
)

# Mapping from method name to function
ESTIMATORS: Dict[
    str, Callable[[pd.DataFrame, str, bool], Dict[str, Union[int, str, float, Dict[str, Optional[float]]]]]] = {
    "std": estimate_price_std,
    "mad": estimate_price_mad,
    "minmax": estimate_price_min_max,
}


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Determine historical USD price of a king coconut.")
    parser.add_argument("--steps", type=int, default=2, help="Number of time steps (default: 2)")
    parser.add_argument("--delta_years", type=float, default=2.5, help="Years between time steps (default delta: 2.5)")
    parser.add_argument("--debug", action="store_true", help="Save debug JSON and numpy output")
    parser.add_argument(
        "--method",
        choices=ESTIMATORS.keys(),
        default="std",
        help="Price estimation method: std, mad, or minmax (default: std)"
    )
    parser.add_argument(
        "--supplement-paxg",
        action="store_true",
        help="Supplement missing PAXG values using Yahoo Finance closing prices"
    )
    parser.add_argument(
        "--supplement-paxg-from-testnet",
        action="store_true",
        help="Supplement missing PAXG values in mainnet data using testnet data instead of Yahoo Finance"
    )
    return parser.parse_args()


def generate_backdated_timestamps(steps: int, delta_years: float) -> List[int]:
    """
    Generate a list of millisecond timestamps spaced backwards in time.

    Args:
        steps (int): Number of time points.
        delta_years (float): Years between steps.

    Returns:
        List[int]: List of UNIX timestamps in milliseconds.
    """
    now = datetime.datetime.now(tz=datetime.UTC)
    return [
        int((now - datetime.timedelta(days=365 * delta_years * i)).timestamp() * 1000)
        for i in range(steps)
    ]


async def run_analysis(ts_steps: List[int],
                       method_func: Callable[[pd.DataFrame, str, bool], Dict[str, Union[int, str, float, Dict[str,
                       Optional[float]]]]],
                       save_debug: bool = False,
                       supplement_paxg: bool = False,
                       supplement_paxg_from_testnet: bool = False) -> None:
    """
    Run the full pipeline: collect data, merge it, and estimate coconut price.

    Args:
        ts_steps (List[int]): List of timestamps to request data from.
        method_func (Callable): Function to use for price estimation.
        save_debug (bool): Whether to save debug files.
        supplement_paxg (bool): Whether to supplement missing PAXG values from Yahoo Finance.
        supplement_paxg_from_testnet (bool): Whether to use testnet data for PAXG supplementation.
    """
    testnet_data, mainnet_data = await asyncio.gather(
        collect_data(ts_steps, is_testnet=True),
        collect_data(ts_steps, is_testnet=False)
    )

    df_test = merge_data(testnet_data, supplement_paxg=supplement_paxg)
    df_main = merge_data(mainnet_data,
                         supplement_paxg=supplement_paxg,
                         supplement_paxg_from_testnet=supplement_paxg_from_testnet,
                         testnet_df=df_test if supplement_paxg_from_testnet else None)

    result_test = method_func(df_test, label="testnet", save_debug=save_debug)
    result_main = method_func(df_main, label="mainnet", save_debug=save_debug)

    # Compare based on lowest score (std/mad/spread)
    best = min(
        [result_test, result_main],
        key=lambda x: x.get("std") or x.get("mad") or x.get("minmax")
    )
    print(f"Best overall match comes from {best["label"]}:")
    print(json.dumps(best, indent=2))

    print(f"\nThe King Coconut price in USD is estimated to be: ${best["price_usd"]:.4f}\n")

def main() -> None:
    """
    Main entry point: parse args and run analysis.
    """
    args = parse_args()
    ts_steps = generate_backdated_timestamps(args.steps, args.delta_years)

    if args.debug:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    method_func = ESTIMATORS[args.method]

    asyncio.run(run_analysis(ts_steps,
                             method_func=method_func,
                             save_debug=args.debug,
                             supplement_paxg=args.supplement_paxg,
                             supplement_paxg_from_testnet=args.supplement_paxg_from_testnet))


if __name__ == "__main__":
    main()

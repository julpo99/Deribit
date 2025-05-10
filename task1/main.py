import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any

from client import DeribitClient
from mark_price_calculator import compute_mid_price, compute_black76_mark_price

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"


def save_output(timestamp: float, data: Dict[str, Any], output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    """
    Save computed option mark prices to a JSON file.

    Args:
        timestamp (float): UNIX timestamp used in the filename.
        data (Dict[str, Any]): Computed data to be saved.
        output_dir (Path): Directory to store output files. Defaults to 'task1/output'.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    fname = output_dir / f"prices_{timestamp}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


async def main(args: argparse.Namespace) -> None:
    """
    Connects to the Deribit WebSocket API and periodically fetches and computes mark prices
    for call and put options at given strikes and expiry.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
    """
    client = DeribitClient()
    await client.connect(args.testnet)
    await client.load_instruments(args.expiry)

    start_time = time.time()

    while time.time() - start_time < args.T1:
        output: Dict[str, Dict[str, Any]] = {}
        timestamp = time.time()

        for strike in args.strikes:
            call_inst, put_inst = client.get_call_put_instruments(strike)
            output[str(strike)] = {}

            for inst_name, option_type in [(call_inst, "call"), (put_inst, "put")]:
                if inst_name:
                    inst_data = next((i for i in client.instruments if i["instrument_name"] == inst_name), None)
                    is_standard = inst_data and float(inst_data.get("strike", -1)) == strike

                    try:
                        book = await client.get_order_book(inst_name)

                        if args.black76:
                            ticker = await client.get_ticker(inst_name)
                            computed_mark = compute_black76_mark_price(ticker, inst_data)
                            if computed_mark is None:
                                computed_mark = compute_mid_price(book)
                        else:
                            computed_mark = compute_mid_price(book)

                        computed_mark = round(computed_mark, 4)

                        entry = {"is_standard": is_standard}

                        if is_standard:
                            entry.update({
                                "computed_mark": computed_mark,
                                "deribit_mark": await client.get_mark_price(inst_name),
                                "instrument": inst_name,
                            })
                        else:
                            entry.update({
                                "computed_mark": computed_mark,
                                "closest_instrument": inst_name,
                            })
                            print(f"Strike {strike} {option_type}: closest instrument used → {inst_name}")

                    except Exception as e:
                        entry = {
                            "computed_mark": None,
                            "instrument": inst_name,
                            "is_standard": is_standard,
                            "error": f"Failed to fetch data: {e}",
                        }

                else:
                    entry = {
                        "computed_mark": None,
                        "error": "No matching Deribit instrument",
                        "closest_instrument": inst_name,
                    }
                    print(f"Strike {strike} {option_type}: closest instrument used → {inst_name}")

                entry["testnet"] = args.testnet
                output[str(strike)][option_type] = entry

        save_output(timestamp, output)
        print(f"Saved mark prices at {timestamp}")
        await asyncio.sleep(args.T2)

    await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--expiry", type=str, required=True, help="Expiry date of the options (e.g., '30AUG24').")
    parser.add_argument("--T1", type=float, required=True, help="Total runtime in seconds.")
    parser.add_argument("--T2", type=float, required=True, help="Sleep interval between iterations in seconds.")
    parser.add_argument("--strikes", type=float, nargs="+", required=True, help="List of strike prices to monitor.")
    parser.add_argument("--testnet", action="store_true", help="Use Deribit testnet environment.")
    parser.add_argument("--black76", action="store_true", help="Use Black-76 model for computing mark price.")

    args = parser.parse_args()
    asyncio.run(main(args))

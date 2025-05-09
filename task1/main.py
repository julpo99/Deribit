import argparse
import asyncio
import json
import time
from pathlib import Path

from client import DeribitClient
from mark_price_calculator import compute_mid_price, compute_black76_mark_price

USE_BLACK76 = False
TESTNET = False


def save_output(timestamp, data, output_dir="output"):
    Path(output_dir).mkdir(exist_ok=True)
    fname = f"{output_dir}/prices_{timestamp}.json"
    with open(fname, "w") as f:
        json.dump(data, f, indent=2)


async def main(args):
    # Create the Deribit client
    client = DeribitClient()
    # Connect to the Deribit WebSocket API
    await client.connect(TESTNET)
    # Load the instruments for the specified expiry
    await client.load_instruments(args.expiry)

    start_time = time.time()

    # Run for T1 seconds
    while time.time() - start_time < args.T1:
        output = {}

        # The timestamp could be converted to a human-readable format if needed
        timestamp = int(time.time())

        for strike in args.strikes:
            # Get the call and put instruments for the given strike
            call_inst, put_inst = client.get_call_put_instruments(strike)
            output[str(strike)] = {}

            for inst_name, option_type in [(call_inst, "call"), (put_inst, "put")]:
                if inst_name:
                    inst_data = next((i for i in client.instruments if i["instrument_name"] == inst_name), None)

                    is_standard = inst_data and float(inst_data.get("strike", -1)) == strike

                    try:
                        book = await client.get_order_book(inst_name)

                        if USE_BLACK76:
                            ticker = await client.get_ticker(inst_name)
                            computed_mark = compute_black76_mark_price(ticker, inst_data)
                            if computed_mark is None:
                                computed_mark = compute_mid_price(book)
                        else:
                            computed_mark = compute_mid_price(book)

                        # Round the computed mark to match the precision of the Deribit API, comment the line below
                        # if you want full precision
                        computed_mark = round(computed_mark, 4)

                        entry = {
                            "is_standard": is_standard
                        }

                        if is_standard:
                            entry["computed_mark"] = computed_mark
                            deribit_mark = await client.get_mark_price(inst_name)
                            entry["deribit_mark"] = deribit_mark
                            entry["instrument"] = inst_name
                        else:
                            entry["computed_mark"] = computed_mark
                            entry["closest_instrument"] = inst_name
                            print(f"Strike {strike} {option_type}: closest instrument used → {inst_name}")

                    except Exception as e:
                        entry = {
                            "computed_mark": None,
                            "instrument": inst_name,
                            "is_standard": is_standard,
                            "error": f"Failed to fetch data: {e}"
                        }

                else:
                    entry = {
                        "computed_mark": None,
                        "error": "No matching Deribit instrument",
                        "closest_instrument": inst_name
                    }
                    print(f"Strike {strike} {option_type}: closest instrument used → {inst_name}")

                output[str(strike)][option_type] = entry

                # Add information about testnet or production
                if TESTNET:
                    output[str(strike)][option_type]["testnet"] = True
                else:
                    output[str(strike)][option_type]["testnet"] = False

        save_output(timestamp, output)
        print(f"Saved mark prices at {timestamp}")
        await asyncio.sleep(args.T2)

    await client.close()


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--expiry", type=str, required=True)
    parser.add_argument("--T1", type=int, required=True)
    parser.add_argument("--T2", type=int, required=True)
    parser.add_argument("--strikes", type=float, nargs="+", required=True)
    args = parser.parse_args()

    # Run the main function as an asyncio task
    asyncio.run(main(args))

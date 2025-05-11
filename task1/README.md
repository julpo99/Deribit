# TASK 1: Mark Price Generator for Deribit Expiry

## Overview

This Python application connects to Deribit’s WebSocket API and does the following:

- Subscribes to live market data for BTC options of the expiry specified in the input.
- Retrieves the exact strike instruments for the given strikes if available. Otherwise, it finds the closest
  available strike for computing the mark price.
- Computes (call & put) mark prices for the given strikes every `T2` seconds over a total time of `T1` seconds.
- Saves the output of the computed mark price in a json file and compares it with Deribit’s mark price for standard
  strikes.

## Clone the Repository

```bash
git clone https://github.com/julpo99/Deribit
```

## Install the requirements

```bash
pip install -r ../requirements.txt
```

## Run the Application (Examples)

```bash
python main.py --expiry 23MAY25 --T1 20 --T2 5 --strikes 96000 98000 99800

# For testnet
python main.py --expiry 23MAY25 --T1 20 --T2 5 --strikes 96000 98000 99800 --testnet

# For Black76 model
python main.py --expiry 23MAY25 --T1 20 --T2 5 --strikes 96000 98000 99800 --black76

# For Black76 model on testnet
python main.py --expiry 23MAY25 --T1 20 --T2 5 --strikes 96000 98000 99800 --testnet --black76

```

## Arguments

- `--expiry`: Deribit expiry code (e.g., `23MAY25`)
- `--T1`: Total runtime in seconds (can be float for sub-second precision)
- `--T2`: Interval in seconds between each computation (can be float for sub-second precision)
- `--strikes`: A custom array of strike prices (as numbers)

Optional Arguments:

- `--testnet`: To use the testnet environment.
- `--black76`: To use the Black-76 model for mark price calculation.

## Output

JSON files named `prices_<timestamp>.json` saved to the `output/` directory, containing:

```json
{
  "96000.0": {
    "call": {
      "is_standard": true,
      "computed_mark": 0.0774,
      "deribit_mark": 0.0774,
      "instrument": "BTC-23MAY25-96000-C",
      "testnet": false
    },
    "put": {
      "is_standard": true,
      "computed_mark": 0.0084,
      "deribit_mark": 0.0084,
      "instrument": "BTC-23MAY25-96000-P",
      "testnet": false
    }
  },
  "98000.0": {
    "call": {
      "is_standard": true,
      "computed_mark": 0.0624,
      "deribit_mark": 0.0625,
      "instrument": "BTC-23MAY25-98000-C",
      "testnet": false
    },
    "put": {
      "is_standard": true,
      "computed_mark": 0.0128,
      "deribit_mark": 0.0128,
      "instrument": "BTC-23MAY25-98000-P",
      "testnet": false
    }
  },
  "98800.0": {
    "call": {
      "is_standard": false,
      "computed_mark": 0.0556,
      "closest_instrument": "BTC-23MAY25-99000-C",
      "testnet": false
    },
    "put": {
      "is_standard": false,
      "computed_mark": 0.0157,
      "closest_instrument": "BTC-23MAY25-99000-P",
      "testnet": false
    }
  }
}
```

## Key Challenges

- Handling Deribit’s real-time data over WebSocket reliably.
- Mapping non-standard strike inputs to the nearest valid instrument in order to compute the mark price.
- Mid-price calculation when bid/ask data may be missing.
- Finding a robust way to calculate the mark price for non-standard strikes.
- Testing different mark price calculation methods to ensure accuracy.
- Testnet was offline due to mainance for some time.
- (My IDE had some issues with the SSL certificate, so I had to add some lines to make sure my environment finds the
  certificate as well as the `certifi` package. I did not remove those lines because it should not affect the
  functionality of the code.)

## Design Reasoning

- Mark price is calculated as:
    1. Mid of best_bid and best_ask (if both present and > 0)
    2. One-sided estimation if only one is present and > 0 (I don't think this case is possible with real life data,
       so it will be skipped)
    3. last_price
    4. settlement_price
    5. average of min_price and max_price
    6. return None if all else fails
- Only compare to Deribit’s mark price when a matching instrument exists.
- Real-time loop with `asyncio` to support fast network IO and precise timing.
- Output is saved in a JSON file with a timestamp to avoid overwriting.

## Additional Mark Price Calculation Method (Black76)

- After some online research, it seems that a variant of the Black-Scholes model is used (Black76) to calculate the mark
  price.
- We try to replicate the model and check if we get similar mark prices as the ones from Deribit.
- After some testing, it seems that the Black76 model is more accurate than the mid-price calculation.
- Change the last point perhaps? To:

- We kept the first method as the default because it’s faster and the goal wasn’t to match Deribit’s mark price (as
stated in Slide 2). However, since I had extra time and Slide 3 mentioned grading would be based on how close our mark
price was to Deribit’s, I also implemented a more accurate method for comparison.

- References:
    - https://en.wikipedia.org/wiki/Black_model,
    - https://wiki.dederi.io/PricingModel/mark_price/

## Assumptions

- Strike instruments may not always exist for all inputs; the closest available strike is selected in that case.
- We assume a correct input via command line arguments.
- We only assume positive strikes.
- The application works both on testnet and production, the testnet offered more edge cases to test the code.
- A lot of checks could have been added, but we prioritized clean code and readability over robustness.
- Regex for input validation could be added to ensure the expiry format is correct.
- Many more try and catch could be added to ensure the code does not break in case of an error.
- Mid-price is assumed to be a good and fast approximation of the mark price.
- The code is not optimized for performance, but rather for clarity and maintainability.
- More accurate functions could be added to calculate the mark price, at the cost of performance.
- We assume that the code is run with python 3.12 or higher.

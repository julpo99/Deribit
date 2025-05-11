# TASK 2: Historical USD Price of a King Coconut

## Overview

This project estimates the historical price of a king coconut in USD using data from the Deribit API,
combined with supplementary data if chosen. Multiple statistical methods are supported for
estimation.

The application reverse-engineers the USD price of a coconut by:

- Fetching historical settlement prices of six cryptocurrencies from Deribit (both from testnet and mainnet).
- Calculating the implied USD price based on known coconut prices in each crypto.
- Identifying the best match among implied prices with various statistical methods, indicating price agreement across
  all cryptos.

## Clone the Repository (if not already done)

```bash
git clone https://github.com/julpo99/Deribit
```

## Install the requirements (if not already done)

```bash
pip install -r requirements.txt
```

## Run the Application (Examples)

```bash
python main.py  

python main.py --supplement-paxg-from-testnet

python main.py --method mad --supplement-paxg-from-testnet

python main.py --method minmax --supplement-paxg-from-testnet

python main.py --supplement-paxg-from-yahoo
```

## Optional Arguments:

- `--method`: The method to use for estimation. Options are `std`, `mad`, or `minmax` (default: `std`).
- `--supplement-paxg-from-testnet`: If set, fetches PAXG prices from testnet (only for mainnet).
- `--supplement-paxg-from-yahoo`: If set, fetches PAXG prices from Yahoo Finance (both testnet and mainnet).
- `--steps`: Number of time checkpoints (default: 2).
- `--delta_years`: Number of years between checkpoints (default: 2.5)
- `--debug`: If set, saves intermediate JSON and `.npy` debug data locally.

## Output

The output is shown in the terminal and saved in a JSON file named `best_match_{method}_{net}.json` in the `data/`
directory.

Example of output with supplemented PAXG data from testnet:

```
Best overall match comes from mainnet:
{
  "timestamp": 1731312000044,
  "date": "2024-11-11T08:00:00.044000+00:00",
  "price_usd": 4.208654,
  "std": 0.005696,
  "prices": {
    "BTC_USDC": 4.207644,
    "ETH_USDC": 4.204009,
    "PAXG_USDC": 4.201017,
    "SOL_USDC": 4.207768,
    "XRP_USDC": 4.218236,
    "ADA_USDC": 4.21325
  },
  "label": "mainnet"
}

The King Coconut price in USD is estimated to be: $4.2087

```

## Results

The estimated **USD price of the King Coconut** is:

> **`$4.2087`**

This is obtained by using the **standard deviation minimization** method on the mainnet data with supplemented PAXG
prices from
the testnet. The same result is obtained when using the **mean absolute deviation minimization** method and the
**min-max spread minimization** method.
We obtained a lower standard deviation of **`0.005696`** with supplemented PAXG prices from the testnet, compared to
the supplemented PAXG prices from Yahoo, which had a standard deviation of **`0.007329`**.
(Without supplementation of the PAXG price, the obtained result was **`4.2101`**). _It’s hard to ignore the coincidence
of 4.20 being the final result... (if considering only 2 decimal places without rounding)._

The value was selected based on the date 2024-11-11, for which the converted coconut prices across all supported
cryptocurrencies had the lowest standard deviation. This indicates the highest agreement across markets on the coconut’s
USD value, making it the most likely actual price.

These results were obtained using Deribit’s public WebSocket API function `public/get_last_settlements_by_instrument`,
which returns historical settlement data. For each instrument, we used the mark_price field as the reference price.

While this seemed the most intuitive and comprehensive data source available, we acknowledge that due to our limited
financial domain expertise, we cannot guarantee this was the exact price intended for this estimation. Other price
types (e.g., index_price) might also have been appropriate. If that were the case, the overall methodology and reasoning
would remain valid — the implementation would only require substituting the relevant price field.

Additionally, we used the perpetual contracts (e.g., BTC_USDC-PERPETUAL) in our queries. Again, this choice was made
based on available information, but may differ from what was intended in the original market context.

Nonetheless, the process remains methodologically consistent and easy to adapt with more precise domain knowledge.

## Features

- Fetch historical **settlement prices** for crypto assets from the Deribit WebSocket API
- Merge data across timestamps and crypto symbols
- Support **three estimation methods**:
    - `std`: Standard Deviation Minimization
    - `mad`: Mean Absolute Deviation Minimization
    - `minmax`: Min-Max Spread Minimization
- Handles missing data in PAXG via:
    - Yahoo Finance closing prices
    - Testnet-derived data
- Outputs the **best match** for the coconut price in USD

## Key Challenges

- Deribit API Limitations: each call to Deribit’s get_last_settlements_by_instrument is capped at 1000 records —
  roughly 2.7 years of data at 1 price per day — requiring backdated and batched queries to avoid data truncation.
- WebSocket Management: because we relied on asynchronous WebSocket calls, we had to carefully manage both rate
  limits and ensure consistent response ordering.
- Standard deviation initially produced misleadingly low values when many crypto prices were missing (zeros). This
  was fixed by calculating standard deviation only over non-NaN values.
- Rows with only one valid value also had a standard deviation of zero. We now filter out those cases by requiring
  more than two valid values per row.


- **PAXG Data Missing:**
    - Over 965 PAXG entries were missing from testnet, and 1000 from mainnet.
    - We attempted to supplement missing PAXG prices from CoinGecko, but the 365-day limit on the public API made this
      infeasible.
    - We then switched to Yahoo Finance, using daily closing prices and merging them into the Deribit dataset based on
      the calendar date.
    - Time Alignment: Deribit timestamps are recorded around 08:00 UTC, while Yahoo returns closing prices.
      We therefore shifted Yahoo values one day back to match the assumed Deribit settlement.


- **Anomalies on Certain Dates:**
    - On 2024-11-11, the testnet had 5 missing crypto prices, but that same day produced the best match on the mainnet.
    - On that same day the mainnet only had 1 missing value (PAXG), so the supplementation of the PAXG values is only
      allowed in one direction (testnet to mainnet), but not the other way around. (The other way around would produce
      exactly the same value for that day).
    - Anomalies regarding missing data were also observed on 2024-04-06, 2023-08-07, 2022-02-19, 2023-08-05 and
      2023-08-06.

## Design Reasoning

- **Data Collection**: Settlement data is collected via WebSocket requests to Deribit's API, with backdated timestamps
  spanning several years.
- **Estimation Logic**: For each timestamp, multiply settlement price by known coconut amount per crypto. The row with
  the lowest standard deviation is assumed to be the day of correct pricing.
- **Parallel Execution**: Mainnet and testnet data are fetched in parallel via asyncio, with timestamp-based batching to
  handle API limits.
- **Efficiency**: Batching requests and using a single socket improves performance.
- **Robustness**: Handle missing or partial data; processes both testnet and mainnet.
- **Precision**: The standard deviation method highlights the day with tightest price agreement. Additional methods
  (MAD, minmax) are also available for comparison.

Below is a chronological summary of major improvements made during the development of the solution and their impact on
runtime performance:

## Timeline of Improvements

| Change / Optimization                                          | Rationale                                                          | Runtime Impact               |
|----------------------------------------------------------------|--------------------------------------------------------------------|------------------------------|
| Initial implementation using one WebSocket request per message | Simple and functional baseline                                     | ~10–20s total runtime        |
| Parallel WebSocket queries for testnet and mainnet             | Used `asyncio.gather` to fetch both environments concurrently      | ↓ ~5–10s total runtime       |
| Single WebSocket connection per run                            | Reduced overhead from reconnecting for every message               | ↓ ~4–8s total runtime        |
| Batching all requests before reading responses                 | Improved throughput by pipelining messages                         | -                            |
| Removed redundant nested loops for appending records           | Simplified data accumulation using a flat list                     | ↓ ~4s total runtime          |
| Switched to vectorized NumPy operations                        | Replaced loops with fast array computations                        | ↓ ~3.5s runtime              |
| Avoided std/mad/spread computation on insufficient data        | Prevented misleading results & unnecessary processing              | ↑ accuracy, ↓ slight time    |
| Date-based merging for PAXG Yahoo supplementation              | Prevented inefficient timestamp-level joins                        | ↓ ~3s runtime                |
| Shifted Yahoo prices back one day                              | Aligned mismatched temporal resolution (08:00 UTC vs 00:00 UTC)    | ↑ correctness                |
| PAXG supplementation from testnet                              | Avoided uncertain assumptions from Yahoo; kept timeline consistent | ↑ reliability, ↑ consistency |
| Conditional debug saving (`--debug` flag)                      | Avoids disk writes unless explicitly requested                     | ↓ I/O time, ↓ disk usage     |
| Lightweight JSON output (only best result saved)               | Reduced file I/O and JSON dump time                                | ↓ overhead                   |

> **Current average runtime: ~2.5 seconds (MacBook M2 CPU)**

Although we explored several optimizations, the overall speed is still primarily limited by network latency and the time
it takes to complete multiple WebSocket requests. The most computationally expensive loops were already vectorized with
NumPy, and further overengineering would bring negligible benefit relative to the API call duration. The current setup
strikes a practical balance between performance and maintainability.

## Assumptions

- The coconut shop used the **previous day’s** Deribit **settlement price** as the reference USD value.
- The photo of the coconut price was taken **sometime between 2021 and 2025**.
- We assume the coconut price is greater than zero.
- We assume the **correct price to consider is the `mark_price`** returned by Deribit’s
  `get_last_settlements_by_instrument` API function.
- We did **not investigate** the financial definitions of `mark_price` vs. `settlement_price` vs. `index_price`.
    - Therefore, if a different price type was intended, the logic of the solution would still hold — only a different
      API field would need to be substituted.
- We used **perpetual contracts** (e.g., `BTC_USDC-PERPETUAL`) based on their availability and continuity, although we
  can’t confirm this matches the market context of the original photo.
- We assume the coconut had **non-zero price** (>0).
- The approach assumes **no specific financial domain knowledge** is required. It’s purely based on statistical
  agreement among implied prices.
- When supplementing missing PAXG values:
    - From **Yahoo Finance**, we used **closing prices**, shifted **one day backward** to align with Deribit
      timestamps (usually around 08:00 UTC).
    - From **testnet**, we reused the PAXG value to supplement the mainnet **only** — not the other way around — to
      avoid circular dependencies and preserve the validity of the mainnet result.
- We deliberately avoided using mainnet values to fill testnet data on critical dates (e.g., 2024-11-11), as doing so
  would have made the testnet result artificially identical to the mainnet result, undermining the validity of the
  comparison.

## Requirements

```
asyncio
websockets
requests
certifi
numpy
pandas
yfinance
```

#### Additional Notes:

The `--steps` and `--delta_years` arguments control how far back in time the data is fetched.

Since Deribit returns at most **1000 settlements per request** (≈2.7 years), we use:

- `--steps`: Number of distinct timestamps to query.
- `--delta_years`: Time gap (in years) between them.

This setup prevents hitting API limits and allows flexibility for future scaling (gathering longer periods of data).  
For this task, we used `--steps=2` and `--delta_years=2.5` to safely cover recent history without unnecessary requests.

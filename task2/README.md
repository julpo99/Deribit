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

python main.py --supplement-paxg-from-yahoo

python main.py --method mad --supplement-paxg-from-testnet

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

## Result

The estimated **USD price of the King Coconut** is:

> **`$4.2087`**

Rounded to two decimal places, this gives:

> **`$4.21`**

This value was selected based on the date 2024-11-11, for which the converted coconut prices across all supported
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

- Fetches historical **settlement prices** for crypto assets from the Deribit WebSocket API
- Merges data across timestamps and crypto symbols
- Supports **three estimation methods**:
    - `std`: Standard Deviation Minimization
    - `mad`: Mean Absolute Deviation Minimization
    - `minmax`: Min-Max Spread Minimization
- Handles missing data in PAXG via:
    - Yahoo Finance closing prices
    - Testnet-derived data
- Outputs the **best match** for the coconut price in USD
-

## Key Challenges

- Deribit API Limitations: Each call to Deribit’s get_last_settlements_by_instrument is capped at 1000 records —
  roughly 2.7 years of data — requiring backdated and batched queries to avoid data truncation.
- WebSocket Management: Because we relied on asynchronous WebSocket calls, we had to carefully manage both rate
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
    - Time Alignment: Deribit timestamps are recorded around 08:00 UTC, while Yahoo returns closing prices (~00:00 UTC).
      We therefore shifted Yahoo values one day back to match the assumed Deribit settlement.


- **Anomalies on Certain Dates:**
    - On 2024-11-11, the testnet had 5 missing crypto prices, but that same day produced the best match on the mainnet.
    - On that same day the mainnet only had 1 missing value (PAXG), so the supplementation of the PAXG values is only
      allowed in one direction (testnet to mainnet), but not the other way around. (The other way around would producd
      exactly the same value for that day).

## Design Reasoning and Timeline of Improvements

- **Data Collection**: Settlement data is collected via WebSocket requests to Deribit's API, with backdated timestamps
  spanning several years.
- **Estimation Logic**: For each timestamp, multiply settlement price by known coconut amount per crypto. The row with
  the lowest standard deviation is assumed to be the day of correct pricing.
- **Parallel Execution**: Mainnet and testnet data are fetched in parallel via asyncio, with timestamp-based batching to
  handle API limits.
- **Efficiency**: Batching requests and using a single socket improves performance.
- **Robustness**: Handles missing or partial data; processes both testnet and mainnet.
- **Precision**: The standard deviation method highlights the day with tightest price agreement.

Below is a chronological summary of major improvements made during the development of the solution and their impact on
runtime performance:

The `--steps` and `--delta_years` arguments define how timestamps are back-calculated and used to request historical
data from
Deribit's API.

Because Deribit returns at most **1000 settlement entries** per call (≈ 2.7 years of data), we split requests into
intervals using:

- `--steps`: how many distinct points in time to collect data from.
- `--delta_years`: how far apart those points are in years.

This avoids hitting API limits and gives you full control over how much historical data to fetch.  
And might be useful in the future if more data is needed. For this task, we set `--steps=2` and `--delta_years=2.5` to
get
the most recent data. Before that time no data is present, making the request useless and time-consuming.

| Change / Optimization                                           | Rationale                                                                 | Runtime Impact          |
|-----------------------------------------------------------------|---------------------------------------------------------------------------|-------------------------|
| Initial implementation using one WebSocket request per message  | Simple and functional baseline                                            | ~20–25s total runtime   |
| Parallel WebSocket queries for testnet and mainnet              | Used `asyncio.gather` to fetch both environments concurrently             | ↓ ~15–18s total runtime |
| Single WebSocket connection per run                             | Reduced overhead from reconnecting for every message                      | ↓ ~13–14s total runtime |
| Batching all requests before reading responses                  | Improved throughput by pipelining messages                                | ↓ ~11–12s total runtime |
| Removed redundant nested loops for appending records            | Simplified data accumulation using a flat list                            | ↓ ~10s total runtime    |
| Switched to vectorized NumPy operations                         | Replaced loops with fast array computations                               | ↓ ~7.5s runtime          |
| Avoided std/mad/spread computation on insufficient data         | Prevented misleading results & unnecessary processing                     | ↑ accuracy, ↓ slight time |
| Date-based merging for PAXG Yahoo supplementation               | Prevented inefficient timestamp-level joins                               | ↓ ~6.5s runtime          |
| Shifted Yahoo prices back one day                               | Aligned mismatched temporal resolution (08:00 UTC vs 00:00 UTC)           | ↑ correctness            |
| Conditional debug saving (`--debug` flag)                       | Avoids expensive disk writes unless explicitly requested                  | ↓ I/O time, ↓ disk usage |
| Lightweight JSON output (only best result saved)                | Reduced file I/O and JSON dump time                                       | ↓ overhead               |

> **Current average runtime: ~2.5 seconds (MacBook M2 CPU)**


## Assumptions

- The coconut shop used the previous day’s Deribit settlement price as the USD value.
- The photo was taken sometime between 2021–2025.
- The lowest standard deviation across converted USD values is a strong indicator of the correct day.
- We assume the coconut price is greater than zero.
- We assume this task does not require financial domain knowledge — the analysis is based purely on data alignment
  and estimation.
- The correct field to use is assumed to be the mark_price returned from get_last_settlements_by_instrument.
- We did not investigate the financial definitions of “mark price” vs. “settlement price” and assume the reported
  value on the day is the one to use.
- When supplementing from Yahoo:
- We used the previous day’s closing price to align with Deribit’s early-morning timestamps.
- Due to limited domain expertise, this choice was made on pragmatic grounds and can be adjusted if a more accurate
  price definition becomes available.
- When supplementing mainnet PAXG with testnet data, we avoided doing the same in reverse (i.e., using mainnet to
  fill testnet) to preserve the integrity of the mainnet result.
  json result below:

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


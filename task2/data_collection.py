import json
import ssl
from typing import List, Tuple, Optional, Any, Hashable

import certifi
import pandas as pd
import websockets
import yfinance as yf

from config import CRYPTOS


async def collect_data(ts_steps: List[int], is_testnet: bool = True) -> list[tuple[Hashable, list[tuple[Any, ...]]]]:
    """
    Collect settlement price data from the Deribit WebSocket API for a list of cryptocurrencies and timestamps.

    Args:
        ts_steps (List[int]): List of timestamps (in milliseconds) to query settlement data for.
        is_testnet (bool): Whether to use the testnet or the mainnet Deribit API. Defaults to True (testnet).

    Returns:
        List[Tuple[str, List[Hashable, list[tuple[Any, ...]]]]:
            A list where each element is a tuple containing a cryptocurrency symbol and its list of
            (timestamp, mark_price, human_readable_date) entries.
    """

    base = "test" if is_testnet else "www"
    url = f"wss://{base}.deribit.com/ws/api/v2"
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    async with websockets.connect(url, ssl=ssl_context) as ws:
        requests = []
        msg_ids = []

        for crypto in CRYPTOS:
            for ts in ts_steps:
                msg_id = f"{crypto}_{ts}"
                msg = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "method": "public/get_last_settlements_by_instrument",
                    "params": {
                        "instrument_name": f"{crypto}_USDC-PERPETUAL",
                        "type": "settlement",
                        "count": 1000,
                        "search_start_timestamp": ts
                    }
                }
                requests.append(msg)
                msg_ids.append((crypto, ts, msg_id))
                await ws.send(json.dumps(msg))

        responses = {}
        for _ in range(len(requests)):
            raw = await ws.recv()
            data = json.loads(raw)
            responses[data["id"]] = data

    records = []
    for crypto, ts, msg_id in msg_ids:
        response = responses.get(msg_id, {})
        settlements = response.get("result", {}).get("settlements", [])

        if len(settlements) == 1000 and ts == ts_steps[-1]:
            print(f"[ALERT] {crypto} hit 1000-limit. More historical data may exist.")

        for entry in settlements:
            timestamp = entry.get("timestamp")
            price = entry.get("mark_price")
            if timestamp and price:
                records.append((crypto, timestamp, price))

    df = pd.DataFrame(records, columns=["crypto", "timestamp", "price"])
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.date.astype(str)

    grouped = df.groupby("crypto")[["timestamp", "price", "date"]]
    return [(crypto, list(group.itertuples(index=False, name=None))) for crypto, group in grouped]


def merge_data(results: List[Tuple[str, List[Tuple[int, float, str]]]], supplement_paxg: bool = False,
               supplement_paxg_from_testnet: bool = False, testnet_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Merge collected settlement data into a single DataFrame indexed by timestamp.

    Args:
        results (List[Tuple[str, List[Tuple[int, float, str]]]]):
            List of tuples containing symbol and corresponding settlement data.
        supplement_paxg_from_yahoo (bool): Whether to supplement missing PAXG values from Yahoo Finance.
        supplement_paxg_from_testnet (bool): Whether to use testnet data for PAXG supplementation.

    Returns:
        pd.DataFrame: A merged DataFrame where rows are timestamps and columns are crypto symbols,
                      with prices filled and missing values set to 0.
    """
    crypto_data = {crypto: {} for crypto in CRYPTOS}
    for crypto, data in results:
        for ts, price, _ in data:
            crypto_data[crypto][ts] = price

    df_dict = {}
    for crypto, data in crypto_data.items():
        ts_price = sorted(data.items())
        df = pd.DataFrame(ts_price, columns=["timestamp", crypto])
        df_dict[crypto] = df

    merged_df = None
    for df in df_dict.values():
        merged_df = df if merged_df is None else pd.merge(merged_df, df, on="timestamp", how="outer")

    merged_df = merged_df.fillna(0).sort_values("timestamp")
    # merged_df["date"] = pd.to_datetime(merged_df["timestamp"], unit="ms").astype("str")
    merged_df["date"] = pd.to_datetime(merged_df["timestamp"], unit="ms").dt.strftime("%Y-%m-%d")
    merged_df.set_index("timestamp", inplace=True)

    # Supplment PAXG with tesnet data if required
    if supplement_paxg_from_testnet and testnet_df is not None:
        testnet_paxg = testnet_df[["date", "PAXG"]].copy()
        merged_df = pd.merge(merged_df.reset_index(), testnet_paxg, on="date", how="left", suffixes=("", "_testnet"))
        merged_df["PAXG"] = merged_df.apply(
            lambda row: row["PAXG_testnet"] if row["PAXG"] == 0 else row["PAXG"], axis=1
        )
        merged_df.drop(columns=["PAXG_testnet"], inplace=True)
        merged_df.set_index("timestamp", inplace=True)

    # Supplement PAXG with yahoo Finance data if required
    if supplement_paxg and "PAXG" in CRYPTOS and merged_df["PAXG"].eq(0).any():
        min_ts, max_ts = merged_df.index.min(), merged_df.index.max()
        start = pd.to_datetime(min_ts, unit="ms").strftime("%Y-%m-%d")
        end = pd.to_datetime(max_ts, unit="ms").strftime("%Y-%m-%d")
        paxg_df = supplement_paxg_from_yahoo(start, end)

        # Ensure "date" is string and merge based on "date"
        paxg_df["date"] = paxg_df["date"].astype(str)

        # Join on date to fill missing PAXG values
        merged_df = pd.merge(merged_df.reset_index(), paxg_df, on="date", how="left", suffixes=("", "_yahoo"))
        merged_df["PAXG"] = merged_df.apply(
            lambda row: row["PAXG_yahoo"] if row["PAXG"] == 0 else row["PAXG"], axis=1
        )
        merged_df.drop(columns=["PAXG_yahoo"], inplace=True)
        merged_df.set_index("timestamp", inplace=True)

    return merged_df


def supplement_paxg_from_yahoo(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch PAXG-USD historical close prices from Yahoo Finance and shift dates by one day.

    Args:
        start_date (str): Start date in "YYYY-MM-DD" format.
        end_date (str): End date in "YYYY-MM-DD" format.

    Returns:
        pd.DataFrame: DataFrame with "timestamp" (ms) and "PAXG" price.
    """
    ticker = yf.Ticker("PAXG-USD")
    df = ticker.history(start=start_date, end=end_date)

    df.reset_index(inplace=True)
    df["date"] = (df["Date"] + pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
    df = df[["date", "Close"]].rename(columns={"Close": "PAXG"})
    print(df.head())
    return df

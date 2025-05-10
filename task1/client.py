import json
import ssl
from typing import List, Tuple, Optional

import certifi
import websockets


class DeribitClient:
    """
    Async WebSocket client for interacting with Deribit's public API (testnet or mainnet).
    Supports querying instruments, order books, and mark prices.
    """

    def __init__(self):
        """Initialize the client with empty WebSocket and instrument list."""
        self.ws = None
        self.instruments: List[dict] = []

    async def connect(self, testnet: bool = False) -> None:
        """
        Connect to the Deribit WebSocket API.

        Args:
            testnet (bool): Whether to connect to the testnet. If False, connects to mainnet.
        """
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        url = "wss://test.deribit.com/ws/api/v2" if testnet else "wss://www.deribit.com/ws/api/v2"
        print(f"Connecting to {'testnet' if testnet else 'mainnet'}")
        self.ws = await websockets.connect(url, ssl=ssl_context)

    async def close(self) -> None:
        """Close the WebSocket connection."""
        await self.ws.close()

    async def send(self, message: dict) -> dict:
        """
        Send a message to the WebSocket API and receive the response.

        Args:
            message (dict): JSON-RPC message to send.

        Returns:
            dict: The parsed JSON response.
        """
        await self.ws.send(json.dumps(message))
        response = await self.ws.recv()
        return json.loads(response)

    async def load_instruments(self, expiry: str) -> None:
        """
        Load all BTC option instruments for a given expiry.

        Args:
            expiry (str): Expiry string to match (e.g., "14JUN24").
        """
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "public/get_instruments",
            "params": {
                "currency": "BTC",
                "kind": "option",
                "expired": False
            }
        }

        response = await self.send(msg)

        if "error" in response:
            raise Exception(f"API Error: {response['error']}")

        self.instruments = [i for i in response["result"] if expiry in i["instrument_name"]]
        print(f"Loaded {len(self.instruments)} instruments for expiry {expiry}")

    def get_call_put_instruments(self, strike: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Find the closest available call and put instruments for a given strike.

        Args:
            strike (float): Target strike price.

        Returns:
            Tuple[Optional[str], Optional[str]]: Tuple of closest call and put instrument names.
        """
        closest_call = None
        closest_put = None
        min_call_diff = float('inf')
        min_put_diff = float('inf')

        for inst in self.instruments:
            try:
                inst_strike = float(inst.get("strike", -1))
                option_type = inst.get("option_type")
                diff = abs(inst_strike - strike)

                if option_type == "call" and diff < min_call_diff:
                    min_call_diff = diff
                    closest_call = inst["instrument_name"]
                elif option_type == "put" and diff < min_put_diff:
                    min_put_diff = diff
                    closest_put = inst["instrument_name"]
            except (ValueError, TypeError):
                continue

        return closest_call, closest_put

    async def get_order_book(self, instrument: str) -> dict:
        """
        Fetch the order book for a given instrument.

        Args:
            instrument (str): Instrument name.

        Returns:
            dict: Order book data.
        """
        msg = {
            "jsonrpc": "2.0",
            "id": 42,
            "method": "public/get_order_book",
            "params": {"instrument_name": instrument}
        }
        response = await self.send(msg)
        return response["result"]

    async def get_mark_price(self, instrument: str) -> Optional[float]:
        """
        Fetch the mark price for a given instrument.

        Args:
            instrument (str): Instrument name.

        Returns:
            Optional[float]: The mark price, or None if unavailable.
        """
        msg = {
            "jsonrpc": "2.0",
            "id": 43,
            "method": "public/ticker",
            "params": {"instrument_name": instrument}
        }
        response = await self.send(msg)
        return response["result"].get("mark_price")

    async def get_ticker(self, instrument: str) -> dict:
        """
        Fetch the ticker info for a given instrument.

        Args:
            instrument (str): Instrument name.

        Returns:
            dict: Ticker data from Deribit.
        """
        msg = {
            "jsonrpc": "2.0",
            "id": 44,
            "method": "public/ticker",
            "params": {"instrument_name": instrument}
        }
        response = await self.send(msg)
        return response["result"]

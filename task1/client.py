import json
import ssl

import certifi
import websockets


class DeribitClient:
    def __init__(self):
        self.ws = None
        self.instruments = []

    async def connect(self, testnet=False):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        # The above line shouldn't be necessary, but my virtual environment was having issues with SSL
        if testnet:
            # Connect to the testnet
            print(f'Connecting to testnet')
            self.ws = await websockets.connect("wss://test.deribit.com/ws/api/v2", ssl=ssl_context)
        else:
            # Connect to the mainnet
            self.ws = await websockets.connect("wss://www.deribit.com/ws/api/v2", ssl=ssl_context)

    async def close(self):
        await self.ws.close()

    async def send(self, message):
        await self.ws.send(json.dumps(message))
        response = await self.ws.recv()
        return json.loads(response)

    async def load_instruments(self, expiry):
        # we use the public API method to get the instruments
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

    def get_call_put_instruments(self, strike):
        """
        Get the closest call and put instruments for a given strike price. If possible, the function will return
        the standard instrument (i.e., the one with the exact strike price). If not, it will return the closest
        instrument available.
        :param strike:
        :return: closest_call, closest_put
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
            except:
                continue

        return closest_call, closest_put

    async def get_order_book(self, instrument):
        msg = {
            "jsonrpc": "2.0",
            "id": 42,
            "method": "public/get_order_book",
            "params": {"instrument_name": instrument}
        }
        response = await self.send(msg)
        return response["result"]

    async def get_mark_price(self, instrument):
        msg = {
            "jsonrpc": "2.0",
            "id": 43,
            "method": "public/ticker",
            "params": {"instrument_name": instrument}
        }
        response = await self.send(msg)
        return response["result"].get("mark_price")

    async def get_ticker(self, instrument):
        msg = {
            "jsonrpc": "2.0",
            "id": 44,
            "method": "public/ticker",
            "params": {"instrument_name": instrument}
        }
        response = await self.send(msg)
        return response["result"]

from pathlib import Path

#: List of cryptocurrency symbols used in analysis.
CRYPTOS = ["BTC", "ETH", "PAXG", "SOL", "XRP", "ADA"]

#: Dictionary mapping crypto-USDC pairs to the amount of each asset used for price calculation.
AMOUNTS = {
    "BTC_USDC": 0.00005181,
    "ETH_USDC": 0.0013371,
    "PAXG_USDC": 0.0015856,
    "SOL_USDC": 0.020196,
    "XRP_USDC": 7.2942,
    "ADA_USDC": 7.3376
}

#: Path to the directory where data will be stored and saved.
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

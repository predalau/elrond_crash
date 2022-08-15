from dotenv import load_dotenv
import os

load_dotenv()

DELAY = 0.1
DATABASE_PATH = "game_history.csv"
STARTING_WALLET_AMT = 100
SALT_HASH = os.getenv("HASH")
DATABASE_MAP = {
    "game_history": {
        "identifier": [],
        "hash": [],
        "timestamp": [],
        "pool_size": [],
        "multiplier": [],
        "bets": [],
        "house_profit": [],
        "house": [],
    },
}

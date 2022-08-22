from dotenv import load_dotenv
import os

load_dotenv()

DELAY = 0.1
DATABASE_PATH = "game_history.csv"
BETS_PATH = "bets.csv"
STARTING_WALLET_AMT = 100
SALT_HASH = os.getenv("HASH")
DATABASE_MAP = {
    "game_history": {
        "identifier": [],
        "hash": [],
        "timestamp": [],
        "pool_size": [],
        "multiplier": [],
        "house_profit": [],
        "house": [],
    },
    "bet_history": {
        "hash": [],
        "timestamp": [],
        "address": [],
        "amount": [],
        "hasWon": [],
        "multiplier": [],
        "status": [],
        "profit": [],
    },
}

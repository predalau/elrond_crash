from dotenv import load_dotenv
import os

load_dotenv()

DELAY = 0.025
BETTING_DELAY = 5
BETTING_STAGE_DURATION = 30
DATABASE_PATH = "db-crash-game"
STARTING_WALLET_AMT = 100
SALT_HASH = os.getenv("HASH")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_PASS = os.getenv("DB_PASS")
DB_USER = os.getenv("DB_USER")
REWARDS_WALLET = SC_ADDRESS = os.getenv("SC_ADDRESS")
CHAIN_ID = "D"
DATABASE_MAP = {
    "games": {
        "identifier": [],
        "timestamp": [],
        "hash": [],
        "pool_size": [],
        "multiplier": [],
        "house_profit": [],
        "house_balance": [],
    },
    "bets": {
        "timestamp": [],
        "hash": [],
        "address": [],
        "amount": [],
        "haswon": [],
        "multiplier": [],
        "profit": [],
        "status": [],
    },
}

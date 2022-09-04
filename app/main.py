import psycopg2
from typing import Union, Dict, List
from fastapi import FastAPI
from schemas import BetSchema, UserSchema, ResponseSchema
from helpers import check_player_balance
from objects import Game, Bet
from fastapi.middleware.cors import CORSMiddleware


game = Game()
app = FastAPI()

# TODO make SCHEMAS for all payloads **in progress**

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/currentBets",
    tags=["bets"],
    response_model=List[BetSchema],
)
def get_current_bets() -> List[BetSchema]:
    """
    Get current bets from the SC
    """
    bets = game.bets
    schema = {
        "timestamp": "timestamp",
        "address": "walletAddress",
        "amount": "betAmount",
        "hasWon": "hasWon",
        "multiplier": "multiplier",
        "status": "status",
        "profit": "profit",
    }
    print(bets)
    for bet in bets:
        for elem in schema.keys():
            if elem in bet.keys():
                bet.update({schema[elem]: bet[elem]})

    return bets


@app.get(
    "/lastBets",
    tags=["bets"],
    response_model=List[Dict],
)
def get_last_bets() -> List[Dict]:
    bets = game.data.get_last_game_bets()
    payload = {
        "bets": bets,
        "count": len(bets),
    }
    return payload["bets"]


@app.get(
    "/getLastTenMultipliers",
    tags=["history"],
    response_model=List,
)
def get_last_ten_multipliers():
    multipliers = game.data.get_last_multipliers()
    print(multipliers)
    return multipliers


@app.get("/checkPlayerBalance/{walletAddress}/{balance}/{signer}")
def check_balance(
    walletAddress: str,
    balance: float,
    signer: str,
) -> bool:
    # user = UserSchema(walletAddress=walletAddress, balance=balance, signer=signer)
    payload = {"status": check_player_balance(walletAddress, balance)}
    return payload["status"]


@app.get("/endBetsTimestamp")
def get_end_bets_ts():
    return game.end_bets


@app.get("/gameOverTimestamp")
def get_end_game_ts():
    return game.end_game


@app.post("/placeBet")
def place_bet(data: BetSchema):
    bet = Bet(data.walletAddress, data.betAmount)
    game.add_bet(bet)


@app.post("/cashout")
def cashout(address: str, multiplier: float):
    game.cashout(address, multiplier)


@app.post("/gameOver")
def end_game():
    global game
    try:
        game.end_game()
        game = Game()
    except psycopg2.InterfaceError:
        game.data._connect()
        game.end_game()
        game = Game()


# game.new_game()

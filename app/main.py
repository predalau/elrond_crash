from typing import Union, Dict, List
from fastapi import FastAPI
from schemas import BetSchema, UserSchema, ResponseSchema
from helpers import check_player_balance
from objects import Game, Bet
from fastapi.middleware.cors import CORSMiddleware


game = Game()
app = FastAPI()

# TODO make SCHEMAS for all payloads **in progress**
origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    bets = []
    schema = {
        "address": "walletAddress",
        "amount": "betAmount",
        "hasWon": "hasWon",
        "profit": "profit",
    }
    for bet in game.bets:
        if bet["status"] == "open":
            bets.append(bet)

    for bet in bets:
        for elem in schema.keys():
            if elem in bet.keys():
                bet.update({schema[elem]: bet[elem]})

    return bets


@app.get(
    "/lastBets",
    tags=["bets"],
    response_model=List[BetSchema],
)
def get_last_bets() -> List[BetSchema]:
    bets = game.data.get_last_game_bets()
    payload = {
        "bets": bets,
        "count": len(bets),
    }
    return payload["bets"]


@app.get(
    "/getLastTenMultipliers",
    tags=["history"],
    response_model=List[float],
)
def get_last_ten_multipliers() -> List[float]:
    payload = {"lastMultipliers": game.data.get_last_multipliers()}
    return payload["lastMultipliers"]


@app.get("/checkPlayerBalance/{walletAddress}/{balance}/{signer}")
def check_balance(
    walletAddress: str,
    balance: float,
    signer: str,
) -> bool:
    # user = UserSchema(walletAddress=walletAddress, balance=balance, signer=signer)
    payload = {"status": check_player_balance(walletAddress, balance)}
    return payload["status"]


@app.post("/placeBet")
def place_bet(data: BetSchema):
    bet = Bet(data.walletAddress, data.betAmount)
    game.add_bet(bet)

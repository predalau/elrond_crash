import psycopg2
import nest_asyncio
import base58
from typing import Union, Dict, List
from fastapi import FastAPI
from schemas import BetSchema, UserSchema, ResponseSchema, CashoutBet
from helpers import check_player_balance
from objects import Game, Bet
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta

nest_asyncio.apply()

# loop.create_task(game.countdown_bets_timer())

# TODO make SCHEMAS for all payloads **in progress**

app = FastAPI()

global game
game = Game()

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
async def get_current_bets() -> List[BetSchema]:
    """
    Get current bets from the SC
    """
    bets = game.get_current_bets()

    return bets


@app.get(
    "/lastBets",
    tags=["bets"],
    response_model=List[Dict],
)
async def get_last_bets() -> List[Dict]:
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
async def get_last_ten_multipliers():
    multipliers = game.data.get_last_multipliers()
    print(multipliers)
    return multipliers


@app.get("/checkPlayerBalance/{walletAddress}/{balance}/{signer}")
async def check_balance(
    walletAddress: str,
    balance: float,
    signer: str,
) -> bool:
    # user = UserSchema(walletAddress=walletAddress, balance=balance, signer=signer)
    payload = {"status": check_player_balance(walletAddress, balance)}
    return payload["status"]


@app.get("/getMultiplier")
async def get_current_multiplier():
    mult = bytes(str(game.multiplier), "utf-8")
    print(mult)
    mult = base58.b58encode(mult)
    return {"multiplier": mult}


@app.get("/getCurrentGameState")
async def get_game_state():
    state = game.state
    return {"state": state}


@app.get("/getGameStateChange")
async def change_game_state() -> str:
    state = await game.get_gamestate_change(game.state)
    return state


@app.get("/isGameOver")
async def is_game_over():
    await game.is_game_over()


@app.get("/endBetsTimestamp")
async def get_end_bets_ts():
    return game.start_time.isoformat()


@app.post("/placeBet")
async def place_bet(data: BetSchema):
    bet = Bet(data.walletAddress, data.betAmount)
    game.add_bet(bet)


@app.post("/cashout")
async def cashout(data: CashoutBet):
    return game.cashout(data.walletAddress, data.multiplier)


@app.post("/crashGame")
async def end_game():
    try:
        game.end_game()

        game.__init__()
        game.countdown_bets()
        setattr(game, "state", "play")

    except (psycopg2.InterfaceError, psycopg2.OperationalError):
        game.data.db._connect()
        game.end_game()

        game.__init__()
        game.countdown_bets()
        setattr(game, "state", "play")


@app.post("/newGame")
async def first_run():
    setattr(game, "start_time", datetime.now() + timedelta(seconds=5))
    game.countdown_bets()
    setattr(game, "state", "play")
    print(game.state)

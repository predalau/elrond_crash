import psycopg2
import nest_asyncio
import base58
from typing import Union, Dict, List
from fastapi import FastAPI, WebSocket
from schemas import BetSchema, UserSchema, ResponseSchema, CashoutBet
from helpers import check_player_balance
from objects import Game, Bet
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import asyncio
from time import sleep

nest_asyncio.apply()

# loop.create_task(game.countdown_bets_timer())

# TODO make SCHEMAS for all payloads **in progress**

app = FastAPI()

# global game
game = Game()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(first_run())


@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    global game
    await websocket.accept()
    while True:
        await websocket.send_text("Hi")
        state = await game.get_gamestate_change()

        await websocket.send_text(state)


@app.get(
    "/currentBets",
    tags=["bets"],
    response_model=List[BetSchema],
)
async def get_current_bets() -> List[BetSchema]:
    """
    Get current bets from the SC
    """
    global game
    bets = game.get_current_bets()

    return bets


@app.get(
    "/lastBets",
    tags=["bets"],
    response_model=List[Dict],
)
async def get_last_bets() -> List[Dict]:
    global game
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
    global game
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


@app.get("/getMultiplier", tags=["getters"])
async def get_current_multiplier():
    global game
    mult = bytes(str(game.multiplier), "utf-8")
    print(mult)
    mult = base58.b58encode(mult)
    return {"multiplier": mult}


@app.get("/getCurrentGameState", tags=["dev", "getters"])
async def get_game_state():
    global game
    state = game.state
    return {"state": state}


@app.get("/getGameStateChange", tags=["getters"])
async def change_game_state() -> str:
    global game

    state = await game.get_gamestate_change()
    return state


@app.get("/endBetsTimestamp", tags=["dev", "getters"])
async def get_end_bets_ts():
    return game.start_time.isoformat()


@app.post("/placeBet", tags=["bets"])
async def place_bet(data: BetSchema):
    bet = Bet(data.walletAddress, data.betAmount)
    game.add_bet(bet)


@app.post("/cashout", tags=["bets", "actions"])
async def cashout(data: CashoutBet):
    return game.cashout(data.walletAddress, data.multiplier)


@app.post("/crashGame", tags=["actions"])
async def end_game():
    global game
    try:
        await game.end_game()
        await game.countdown_bets()

    except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
        print("Connection ERROR! attempting to reconnect")
        print(e)
        game.data.db.__init__()
        await game.end_game()
        await game.countdown_bets()


@app.post("/newGame", tags=["dev", "actions"])
async def first_run():
    global game
    setattr(game, "start_time", datetime.now() + timedelta(seconds=5))
    await game.countdown_bets()


@app.post("/toggleGameState", tags=["dev", "actions"])
async def toggle_State():
    global game
    old_state = game.state
    game.toggle_state()
    if game.state != old_state:
        return "Success"
    else:
        return "Fail"

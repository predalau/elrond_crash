import psycopg2
import nest_asyncio
import base58
from typing import Union, Dict, List
from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException
from schemas import BetSchema, UserSchema, ResponseSchema, CashoutBet
from helpers import check_player_balance
from objects import Game, Bet
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import json
import websockets
import asyncio

nest_asyncio.apply()

# loop.create_task(game.countdown_bets_timer())

# TODO make SCHEMAS for all payloads **in progress**

app = FastAPI()

# global game
global game

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def run_game():
    global game
    game = Game()
    print(game.data.game_history.values[-1])
    while True:
        if hasattr(game, "isPaused") and game.isPaused:
            await asyncio.sleep(1)
            continue

        if game.state == "bet":
            if datetime.now() > game.start_time:
                game.toggle_state()
            else:
                await asyncio.sleep(1)

        if game.state == "play":
            game.iterate_game()
            await asyncio.sleep(0.1)
            if game.multiplier_now == -1:
                await game.end_game()


@app.on_event("startup")
async def start_game():
    asyncio.create_task(run_game())
    return {"message": "Game is running!"}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    try:
        global game
        await websocket.accept()
        while True:
            if hasattr(game, "isPaused") and game.isPaused:
                await asyncio.sleep(1)
                payload = {
                    "gameState": "paused",
                    "multiplier": -1,
                    "activeBets": [],
                }
                payload = json.dumps(payload)
                await websocket.send_json(payload)
                continue

            await asyncio.sleep(0.2)
            payload = {
                "gameState": game.state,
                "multiplier": game.multiplier_now,
                "activeBets": game.get_current_bets(),
            }

            await websocket.send_json(payload)
    except (
        websockets.ConnectionClosed,
        websockets.ConnectionClosedOK,
        websockets.exceptions.ConnectionClosedError,
    ):
        pass


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
    if game.state in ["play", "end"]:
        return
        # raise HTTPException(
        #     status_code=403,
        #     detail="Can only place bet during BETTING stage",
        # )

    bet = Bet(data.walletAddress, data.betAmount)
    game.add_bet(bet)
    return {"status": "success"}


@app.post("/cashout", tags=["bets", "actions"])
async def cashout(data: CashoutBet):
    if game.state in ["bet", "end"]:
        raise HTTPException(
            status_code=403,
            detail="Can only cashout bet during PLAYING stage",
        )

    return game.cashout(data.walletAddress, data.multiplier)


@app.post("/crashGame", tags=["actions"])
async def end_game():
    global game
    try:
        await game.end_game()
        game.__init__()

    except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
        print("Connection ERROR! attempting to reconnect")
        print(e)
        game.data.db.__init__()
        await game.end_game()
        game.__init__()


@app.post("/toggleGameState", tags=["dev", "actions"])
async def toggle_State():
    global game
    old_state = game.state
    game.toggle_state()
    if game.state != old_state:
        return "Success"
    else:
        return "Fail"


@app.post("/pauseGame", tags=["dev", "actions"])
async def pause_game():
    global game
    setattr(game, "isPaused", True)


@app.post("/resumeGame", tags=["dev", "actions"])
async def pause_game():
    global game
    setattr(game, "isPaused", False)

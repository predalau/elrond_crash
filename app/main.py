import psycopg2
import nest_asyncio
from typing import Dict, List
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from schemas import BetSchema, CashoutBet
from helpers import check_player_balance
from objects import Game, Bet
from datetime import datetime
import json
import websockets
import asyncio

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


async def run_game():
    global game
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
                "lastBets": game.data.get_last_game_bets(),
                "betTimer": game.get_countdown_as_str(),
            }

            await websocket.send_json(payload)
    except (
            websockets.ConnectionClosed,
            websockets.ConnectionClosedOK,
            websockets.ConnectionClosedError,
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


@app.get("/getCurrentGameState", tags=["dev", "getters"])
async def get_game_state():
    global game
    state = game.state
    return {"state": state}


@app.post("/placeBet", tags=["bets"])
async def place_bet(data: BetSchema):
    if game.state in ["play", "end"]:
        raise HTTPException(
            status_code=403,
            detail="Can only place bet during BETTING stage",
        )

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

    return game.cashout(data.walletAddress)


@app.post("/crashGame", tags=["actions"])
async def end_game():
    try:
        if game.state != "play":
            raise HTTPException(
                status_code=403,
                detail="Can only crash game during PLAY state",
            )

        else:
            setattr(game, "multiplier_now", -1)
            await asyncio.sleep(2)
            if game.state != "play":
                return {"status": "success"}
            else:
                return {"status": "fail"}

    except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
        print("Connection ERROR! attempting to reconnect")
        print(e)
        game.data.db.__init__()
        game.end_game(manual=True)


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
async def resume_game():
    global game
    setattr(game, "isPaused", False)

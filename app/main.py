import asyncio
import json
from datetime import datetime
from typing import Dict, List

import nest_asyncio
import psycopg2
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from elrond import get_all_bets, confirm_transaction
from helpers import check_player_balance
from objects import Game, Bet
from schemas import BetSchema, CashoutBet
from vars import BETTING_DELAY

nest_asyncio.apply()

app = FastAPI()

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
                new_bets = get_all_bets()
                game.bets.update(new_bets)
                await asyncio.sleep(BETTING_DELAY)

        if game.state == "play":
            if game.multiplier_now == -1:
                game.end_game()
                await asyncio.sleep(0.1)
                tx_hash = game.send_profits()
                await confirm_transaction(tx_hash)
                game.save_game_history()
                game.save_bets_history()
                game.__init__()

            game.iterate_game()
            await asyncio.sleep(game.delay)


@app.on_event("startup")
async def start_game():
    asyncio.create_task(run_game())
    return {"message": "Game is running!"}


@app.websocket("/ws")
async def ws(websoc: WebSocket):
    try:
        global game
        await websoc.accept()
        while True:
            if hasattr(game, "isPaused") and game.isPaused:
                await asyncio.sleep(1)
                payload = {
                    "gameState": "paused",
                    "multiplier": -2,
                    "activeBets": [],
                    "lastBets": game.data.get_last_game_bets(),
                    "betTimer": "",
                }
                payload = json.dumps(payload)
                await websoc.send_json(payload)
                continue

            await asyncio.sleep(0.02)
            payload = {
                "gameState": game.state,
                "multiplier": game.multiplier_now,
                "activeBets": game.get_current_bets(),
                "lastBets": game.data.get_last_game_bets(),
                "betTimer": game.get_countdown_as_str(),
            }
            await websoc.send_json(payload)
    except Exception as e:
        print(str(e))


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
        wallet_address: str,
        balance: float,
        signer: str,
) -> bool:
    # user = UserSchema(walletAddress=walletAddress, balance=balance, signer=signer)
    payload = {"status": check_player_balance(wallet_address, balance)}
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
    global game
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
        setattr(game, "multiplier_now", -1)
        await asyncio.sleep(2)
        if game.state != "play":
            return {"status": "success"}
        else:
            return {"status": "fail"}


@app.post("/toggleGameState", tags=["dev", "actions"])
async def toggle_state():
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

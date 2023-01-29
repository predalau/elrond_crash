import asyncio
import json
import traceback
from datetime import datetime
from typing import Dict, List
import logging

import erdpy.errors
import nest_asyncio
import psycopg2
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from elrond import get_all_bets
from helpers import check_player_balance
from objects import Game
from schemas import BetSchema, CashoutAddress
from vars import BETTING_DELAY
from erdpy.accounts import Address

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

logger = logging.getLogger("fastapi")
logger.setLevel(logging.DEBUG)


async def run_game():
    global game
    while True:
        if hasattr(game, "isPaused") and game.isPaused:
            await asyncio.sleep(1)
            continue

        if game.state == "bet":
            if game.afterCrash == "notCrash":
                setattr(game, "afterCrash", "crash")

            if datetime.now() > game.start_time or game.start_game:
                game.toggle_state()
            else:
                new_bets = get_all_bets()
                if new_bets and not game.has_players:
                    setattr(game, "has_players", True)

                game.bets.update(new_bets)
                await asyncio.sleep(BETTING_DELAY)

        if game.state == "play":
            game.iterate_game()
            await asyncio.sleep(game.delay)

            if game.runtime_index == -1:
                await game.end_game()


@app.on_event("startup")
async def start_game():
    try:
        asyncio.create_task(run_game())
        logger.info("Game has been lauched successfully!")
    except Exception:
        logger.exception(traceback.format_exc())
        asyncio.create_task(run_game())
        logger.warning("Game has been restarted!")


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

            if game.state == "bet":
                await asyncio.sleep(0.05)
            elif game.state == "play":
                await asyncio.sleep(0.02)
            else:
                await asyncio.sleep(0.5)

            payload = {
                "gameState": game.state,
                "multiplier": "{:.2f}".format(game.multiplier_now),
                "activeBets": game.get_current_bets(),
                "lastBets": game.data.get_last_game_bets(),
                "betTimer": game.get_countdown_as_str(),
                "afterCrash": game.afterCrash,
            }
            await websoc.send_json(payload)
    except Exception:
        traceback.print_exc()


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
    "/userProfile",
    tags=["bets"],
    response_model=Dict,
)
async def get_user_profile(walletAddress: str, interval: int = 1) -> Dict:
    """
    Get current bets from the SC
    """
    try:
        address = Address(walletAddress)
    except erdpy.errors.BadAddressFormatError:
        raise HTTPException(status_code=422, detail="Bad Address Format")

    global game
    user_profile = game.data.get_user_profile(address.bech32(), interval=interval)
    return user_profile


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
    tags=["getters", "history"],
    response_model=List,
)
async def get_last_ten_multipliers():
    global game
    multipliers = game.data.get_last_multipliers()
    return multipliers


@app.get(
    "/getLatestGames",
    tags=["getters", "history"],
    response_model=List[Dict],
)
async def get_latest_games():
    global game
    latest_games = game.data.get_latest_games()
    return latest_games


@app.get(
    "/getPlayerWeeklyStats",
    tags=["getters", "history"],
    response_model=Dict,
)
async def get_player_stats(address: str):
    global game
    try:
        address = Address(address)
    except (erdpy.errors.BadAddressFormatError, erdpy.errors.EmptyAddressError):
        raise HTTPException(status_code=422, detail="Bad Address Format")
    latest_games = game.data.get_player_weekly_stats(address.bech32())
    return latest_games


@app.post(
    "/getUserLastTenBets",
    tags=["bets", "getters", "history"],
    response_model=List,
)
async def get_last_ten_bets(data):
    global game
    try:
        address = Address(data.walletAddress)
    except (erdpy.errors.BadAddressFormatError, erdpy.errors.EmptyAddressError):
        raise HTTPException(status_code=422, detail="Bad Address Format")

    bets = game.data.get_user_last_bets(address.bech32())
    return bets


@app.get("/checkPlayerBalance/{walletAddress}/{balance}/{signer}")
async def check_balance(
        wallet_address: str,
        balance: float,
) -> bool:
    try:
        address = Address(data.walletAddress)
    except (erdpy.errors.BadAddressFormatError, erdpy.errors.EmptyAddressError):
        raise HTTPException(status_code=422, detail="Bad Address Format")

    # user = UserSchema(walletAddress=walletAddress, balance=balance, signer=signer)
    payload = {"status": check_player_balance(address.bech32(), balance)}
    return payload["status"]


@app.get("/getCurrentGameState", tags=["dev", "getters"])
async def get_game_state():
    global game
    state = game.state
    return {"state": state}


@app.get("/weeklyLeaderboard", tags=["getters"])
async def weekly_leaderboard():
    wlb = game.data.get_weekly_leaderboard()
    return wlb


@app.post("/cashout", tags=["bets", "actions"])
async def cashout(data: CashoutAddress):
    global game
    print(data)
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
            setattr(game, "runtime_index", -1)
            await asyncio.sleep(2)
            if game.state != "play":
                return {"status": "success"}
            else:
                return {"status": "fail"}

    except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
        print("Connection ERROR! attempting to reconnect")
        print(e)
        game.data.db.__init__()
        setattr(game, "runtime_index", -1)
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


@app.get("/discordAuth", tags=["actions", "user"], response_class=HTMLResponse)
async def authenticate_discord(code: str, state: str):
    from discord_auth import exchange_code, get_user_data
    from vars import REDIRECT_HTML

    global game
    token = exchange_code(code)["access_token"]
    user_discord = get_user_data(token)
    user = {
        "address": state,
        "discord_id": user_discord["id"],
        "discord_name": user_discord["username"],
        "avatar_hash": user_discord["avatar"],
    }

    game.data.new_user(user)

    return REDIRECT_HTML


@app.post("/pauseGame", tags=["dev", "actions"])
async def pause_game():
    global game
    setattr(game, "isPaused", True)


@app.post("/resumeGame", tags=["dev", "actions"])
async def resume_game():
    global game
    setattr(game, "isPaused", False)

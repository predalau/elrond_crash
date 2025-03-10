import json
import random
import logging
import traceback

from app.helpers import get_http_request
from database import GameHistory
from vars import STARTING_WALLET_AMT, SALT_HASH, BETTING_STAGE_DURATION, REWARDS_WALLET, ELROND_API
from datetime import datetime, timedelta
from elrond import send_rewards, get_proxy_and_account, confirm_transaction
import hashlib
import hmac
import pandas as pd
import numpy as np
import asyncio

logger = logging.getLogger("fastapi")
logger.setLevel(logging.DEBUG)


class Bets:
    """docstring for Bet"""

    def __init__(self):
        self.to_list = []

    def to_dict(self):
        final = {}
        for bet in self.to_list:
            final.update({bet.address: bet.amount})
        setattr(self, "to_dict", final)
        return self.to_dict

    def update(self, new_bets: dict):
        if not new_bets:
            return

        new_bets = [Bet(addr, amount) for addr, amount in new_bets.items()]
        setattr(self, "to_list", new_bets)

    def to_dataframe(self):
        temp = []
        for elem in self.to_list:
            temp.append(elem.to_dict())

        return pd.DataFrame(temp)

    def to_list_of_dict(self):
        final = []
        for bet in self.to_list:
            final.append(bet.to_dict())
        return final

    def to_list_of_tuples(self, gamehash):
        final = []
        for bet in self.to_list:
            final.append(bet.to_tuple(gamehash))

        return final

    def add_bet(self, bet):
        final = self.to_list
        merged = False

        for old_bet in final:
            if old_bet.address == bet.address:
                old_bet.merge(bet)
                merged = True

        if not merged:
            final.append(bet)
            setattr(self, "to_list", final)


class Bet:
    """docstring for Bet"""

    def __init__(self, address, amount):
        self.address = address
        self.amount = amount
        self.timestamp = datetime.now().isoformat()
        self.multiplier = 0
        self.state = "open"
        self.haswon = False
        self.profit = 0
        self.cols = [
            "timestamp",
            "hash",
            "address",
            "amount",
            "haswon",
            "multiplier",
            "profit",
            "state",
        ]

    def to_dict(self):

        dic = {}
        for col in self.cols:
            if hasattr(self, col):
                dic.update({col: getattr(self, col)})
        return dic

    def to_tuple(self, gamehash):
        final = []
        for col in self.cols:
            if hasattr(self, col):
                final.append(getattr(self, col))
            elif col == "hash":
                final.append(gamehash)
        return tuple(final)

    def merge(self, bet):
        setattr(self, "amount", self.amount + bet.amount)

    def cashout(self, mult):
        if mult <= 0:
            setattr(self, "haswon", False)
            setattr(self, "cashout_mult", 0)
            setattr(self, "profit", -1 * self.amount)
        else:
            setattr(self, "haswon", True)
            setattr(self, "cashout_mult", mult)
            setattr(self, "profit", self.amount * mult)

        setattr(self, "state", "closed")


class Game:
    """docstring for Game"""

    def __init__(self):
        self.data = GameHistory()
        self.identifier = self._get_id()
        self.set_next_hash_and_mult()

        while self.multiplier > 500:
            self.set_next_hash_and_mult(self.hash)

        self.state = "bet"
        self.has_players = False
        self.delay = 0.1
        self.payout = False
        self.afterCrash = "crash"
        self.bets = Bets()
        self.start_time = datetime.now() + timedelta(seconds=BETTING_STAGE_DURATION)
        self.start_game = False
        self.forced_change = False
        self.house_address = REWARDS_WALLET
        self.house_balance = self.get_house_balance()
        self.set_mult_array()

    def _connect_elrond_wallet(self):
        elrond_proxy, elrond_account = get_proxy_and_account()
        setattr(self, "elrond_account", elrond_account)
        setattr(self, "elrond_proxy", elrond_proxy)

    def set_mult_array(self):
        assert hasattr(self, "multiplier")

        if self.multiplier == 1:
            mult_array = [1, 1, -1]
        else:
            mult_array = np.arange(1, self.multiplier + 0.01, 0.01)

        setattr(self, "mult_array", mult_array)
        setattr(self, "runtime_index", 0)
        setattr(self, "multiplier_now", mult_array[0])

    def iterate_game(self):
        delays = [0.07, 0.025, 0.01]

        assert hasattr(self, "runtime_index")
        assert hasattr(self, "multiplier_now")
        assert hasattr(self, "mult_array")

        i = self.runtime_index

        if i < 0:
            return

        bets_closed = all([bet.state == "closed" for bet in self.bets.to_list])
        setattr(self, "bets_closed", bets_closed)

        if self.multiplier > 50 and not self.forced_change:
            if (self.has_players and bets_closed) or (not self.has_players):
                old_mult = self.multiplier
                setattr(self, "multiplier", round(random.uniform(55, 100), 2))
                self.set_mult_array()
                setattr(self, "has_players", True)
                setattr(self, "forced_change", True)
                logger.info(f"Multiplier changed from {old_mult} to {self.multiplier} due to NO active bets")

        mult_now = self.multiplier_now
        player_potential_wins = 0
        total_bets = 0

        for bet in self.bets.to_list:
            total_bets += bet.amount
            if bet.haswon:
                player_potential_wins += bet.profit
            else:
                player_potential_wins += bet.amount * mult_now

        if i >= len(self.mult_array) - 1:
            setattr(self, "runtime_index", -1)
        else:
            setattr(
                self,
                "multiplier_now",
                float(format(self.mult_array[i + 1], ".2f")),
            )
            setattr(self, "runtime_index", i + 1)

        if player_potential_wins > 0.25 * (self.house_balance + total_bets):
            logger.debug(f"Forced CRASH at multiplier:\t{self.multiplier_now}")
            logger.debug(f"Player profits lost:\t{player_potential_wins} EGLD")
            setattr(self, "multiplier", self.multiplier_now)
            setattr(self, "runtime_index", -1)

        if 0 < mult_now < 2:
            setattr(self, "delay", delays[0])
        elif 2 <= mult_now < 3.5:
            setattr(self, "delay", delays[1])
        elif mult_now >= 3.5:
            setattr(self, "delay", delays[2])

    def get_countdown_as_str(self):
        if self.state != "bet":
            return "00:00"
        else:
            cdown = self.start_time - datetime.now()
            if datetime.now() > self.start_time:
                return "00:00"

            s = str(cdown)
            s = s.split(".")
            s = s[0] + "." + s[1][:2]
            s = s.replace("0:00:", "")
            s = s.replace(".", ":")

            if s.startswith("-1 day"):
                s = "00:00"

            return s

    def toggle_state(self):
        curr_state = self.state

        if curr_state == "bet":
            setattr(self, "state", "play")
        elif curr_state == "play":
            setattr(self, "state", "end")
        elif curr_state == "end":
            self.__init__()

        logger.info(f"Game state: \t{self.state}")
        bets = [bet.to_dict() for bet in self.bets.to_list]
        logger.info(str(bets))

    def _get_id(self):
        if self.data.game_history.empty:
            return 0
        else:
            gameid = self.data.game_history["id"].values[-1] + 1
        return gameid

    def get_house_balance(self):
        try:
            if self.data.game_history.empty:
                balance = STARTING_WALLET_AMT
            else:
                req_url = ELROND_API + f"/address/{self.house_address}"
                req = get_http_request(req_url)
                req.raise_for_status()
                req = json.loads(req.text)
                balance = float(req["data"]["account"]["balance"]) / 10 ** 18
            logger.info("New game initiated!")
            logger.info(f"House balance is:\t{balance}")
            logger.info(f"Game state:\t{self.state}")
            return balance
        except Exception:
            balance = self.data.game_history["house_balance"].iloc[-1:, :].values[0]
            traceback.print_exc()
            return balance

    def cashout(self, wallet):
        for bet in self.bets.to_list:
            if bet.address == wallet and bet.state == "open":
                bet.cashout(self.multiplier_now)

    def set_next_hash_and_mult(self, given_hash=''):
        def get_result(game_hash):
            hm = hmac.new(str.encode(game_hash), b"", hashlib.sha256)
            hm.update(game_hash.encode("utf-8"))
            gme_hex = hm.hexdigest()

            if int(gme_hex, 16) % 33 == 0:
                return gme_hex, 1

            h = int(gme_hex[:13], 16)
            e = 2 ** 52
            result = (((100 * e - h) / (e - h)) // 1) / 100.0
            return gme_hex, result

        if given_hash:
            gme_hash, multiplier = get_result(given_hash)
        elif self.data.game_history.empty:
            gme_hash, multiplier = get_result(SALT_HASH)
        else:
            last_hash = self.data.game_history["hash"].values[-1]
            gme_hash, multiplier = get_result(last_hash)

        setattr(self, "hash", gme_hash)
        setattr(self, "multiplier", multiplier)
        return gme_hash, multiplier

    async def countdown_bets_timer(self):
        while True:
            if datetime.now() > self.start_time and self.state == "bet":
                self.toggle_state()
                return
            await asyncio.sleep(1)

    async def countdown_bets(self):
        return await self.countdown_bets_timer()

    async def has_state_changed(self, state):
        while True:
            if self._state != state:
                return self._state

            await asyncio.sleep(0.5)

    async def get_gamestate_change(self):
        state = self._state
        new_state = await self.has_state_changed(state)
        return new_state

    def get_current_bets(self):
        if len(self.bets.to_list) == 0:
            return []
        final = []
        for bet in self.bets.to_list:
            if bet.state == "open":
                profit = float(np.sum(bet.amount) * self.multiplier_now)
            else:
                profit = bet.profit

            bet = {
                "walletAddress": bet.address,
                "betAmount": bet.amount,
                "profit": float(format(profit, ".2f")),
                "state": bet.state,
            }
            final.append(bet)

        final.reverse()
        return final

    def force_cashout(self):
        for bet in self.bets.to_list:
            if bet.state == "open":
                bet.cashout(-1)

    def send_profits(self):
        adds = {}
        for bet in self.bets.to_list:
            adds.update({bet.address: bet.cashout_mult})

        self._connect_elrond_wallet()
        self.elrond_account.sync_nonce(self.elrond_proxy)
        tx_hash = send_rewards(self.elrond_account, adds)
        if tx_hash:
            setattr(self, "tx_hash", tx_hash)
        else:
            setattr(self, "tx_hash", "")
        return tx_hash

    async def confirm_5_seconds(self):
        trigger = datetime.now() + timedelta(seconds=5)

        while datetime.now() < trigger:
            await asyncio.sleep(1)

        setattr(self, "afterCrash", "notCrash")
        return True

    async def end_game(self, manual=False):
        self.toggle_state()
        setattr(self, "afterCrash", "crash")
        pool_size = 0
        player_profits = 0

        for bet in self.bets.to_list:
            pool_size += bet.amount
            if bet.haswon:
                player_profits += bet.profit

        self.force_cashout()

        house_profits = pool_size - player_profits

        setattr(self, "timestamp", datetime.now())
        setattr(self, "house_profit", house_profits)
        setattr(self, "pool_size", pool_size)
        setattr(self, "house_balance", self.house_balance + house_profits)

        if manual:
            logger.warning("MANUALLY crashed the game")

        tx_hash = self.send_profits()
        await self.confirm_5_seconds()
        while not await confirm_transaction(tx_hash):
            logger.info(f"Tx: {tx_hash} Failed to be confirmed. Retrying...")
            tx_hash = self.send_profits()
            logger.info(f"New Tx: {tx_hash}")

        self.save_game_history()
        self.save_bets_history()
        self.__init__()

    async def confirm_payouts(self):
        while True:
            await asyncio.sleep(1)
            if self.payout:
                return

    def save_game_history(self):
        logger.info("Saving history: ")
        self.data.db.add_row("games_2023", self.to_tuple())

    def save_bets_history(self):
        bets = self.bets.to_list_of_tuples(self.hash)
        logger.info(f"Saving bets:\t{bets}")

        for elem in bets:
            self.data.db.add_row("bets", elem)

    def to_dict(self):
        cols = self.data.map["games"].keys()
        dic = {}
        for col in cols:
            if hasattr(self, col):
                dic.update({col: getattr(self, col)})
        return dic

    def to_tuple(
            self,
    ):
        cols = self.data.map["games"].keys()
        dic = []
        for col in cols:
            if hasattr(self, col):
                if col == "timestamp":
                    dic.append(getattr(self, col).isoformat())
                else:
                    dic.append(getattr(self, col))
        return tuple(dic)

    def bets_to_list_of_tuples(
            self,
    ):
        cols = self.data.map["bets"].keys()
        final = []
        for elem in self.bets.to_list:
            dic = []
            for col in cols:
                if col in elem.keys():
                    dic.append(elem[col])

            final.append(tuple(dic))
        return final

    def add_field(self, dic):
        for key in dic.keys:
            setattr(self, key, dic[key])

    def add_bet(self, bet: Bet):
        if self.state in ["play", "end"]:
            return False

        setattr(bet, "hash", self.hash)
        self.bets.add_bet(bet)

        # new_bets = self.bets
        # new_bet = bet.to_dict()
        # new_bet.update({"hash": self.hash})
        # new_bets.append(new_bet)
        # print(new_bets)
        # setattr(self, "bets", new_bets)
        return True

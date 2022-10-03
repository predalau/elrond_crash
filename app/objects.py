from database import GameHistory
from datetime import datetime, timedelta
from time import sleep
from vars import STARTING_WALLET_AMT, SALT_HASH
import hashlib
import random
import hmac
import pandas as pd
import numpy as np
import asyncio
import threading


class Bet:
    """docstring for Bet"""

    def __init__(self, address, amount):
        self.address = address
        self.amount = amount
        self.timestamp = datetime.now().isoformat()
        self.multiplier = 0
        self.status = "open"
        self.haswon = False
        self.profit = 0

    def to_dict(self):
        cols = [
            "timestamp",
            "address",
            "amount",
            "haswon",
            "multiplier",
            "status",
            "profit",
        ]
        dic = {}
        for col in cols:
            if hasattr(self, col):
                dic.update({col: getattr(self, col)})
        return dic


class Game:
    """docstring for Game"""

    def __init__(self):
        self.data = GameHistory()
        self.identifier = self._get_id()
        self.set_next_hash_and_mult()
        self.state = "bet"
        self.house_balance = self.get_house_balance()
        self.bets = []
        self.start_time = datetime.now() + timedelta(seconds=10)
        self.set_mult_array()

    @property
    def _state(self):
        return self.state

    @_state.setter
    def _state(self, a):
        self.state = a

    def set_mult_array(self):
        assert hasattr(self, "multiplier")
        setattr(self, "runtime_index", 0)
        setattr(self, "multiplier_now", 1)

        if self.multiplier == 1:
            mult_array = [-1]
        else:
            mult_array = np.linspace(1, self.multiplier, num=int(self.multiplier * 100))

        setattr(self, "mult_array", mult_array)

    async def get_mult_now(self):
        delays = [0.1, 0.04, 0.02]

        if self.state == "bet":
            await asyncio.sleep(delays[0])
            return -1

        assert hasattr(self, "runtime_index")
        i = self.runtime_index
        if i == -1:
            return -1

        assert hasattr(self, "multiplier_now")
        mult_now = float(format(self.multiplier_now, ".2f"))

        assert hasattr(self, "mult_array")

        if mult_now > 0 and mult_now < 2:
            await asyncio.sleep(delays[0])
        elif mult_now >= 2 and mult_now < 3.5:
            await asyncio.sleep(delays[1])
        elif mult_now >= 3.5:
            await asyncio.sleep(delays[2])

        if i >= len(self.mult_array) - 1:
            setattr(self, "multiplier_now", -1)
            setattr(self, "runtime_index", -1)
        else:
            setattr(self, "multiplier_now", self.mult_array[i + 1])
            setattr(self, "runtime_index", i + 1)

        return mult_now

    def toggle_state(self):
        curr_state = self._state

        if curr_state == "bet":
            self.state = "play"
        elif curr_state == "play":
            self.state = "bet"

    def _get_id(self):
        if self.data.game_history.empty:
            return 0
        else:
            print(self.data.game_history)
            gameid = self.data.game_history["id"].values[-1] + 1
        return gameid

    def start_new_game(self):
        setattr(self, "identifier", self._get_id())
        setattr(self, "data", GameHistory())
        self.set_next_hash_and_mult()
        self._state = "bet"
        setattr(self, "house_balance", self.get_house_balance())
        setattr(self, "bets", [])
        setattr(self, "start_time", datetime.now() + timedelta(seconds=25))

    def change_state(self):
        if self.state == "bet":
            setattr(self, "state", "play")
        elif self.state == "play":
            setattr(self, "state", "bet")

    def get_house_balance(self):
        if self.data.game_history.empty:
            balance = STARTING_WALLET_AMT
        else:
            balance = self.data.game_history["house_balance"].values[-1]
        return balance

    def cashout(self, wallet, mult, lost=False):
        bets = self.bets
        for bet in bets:
            if bet["address"] == wallet:
                if not lost:
                    profit = bet["amount"] * mult
                    bet.update({"haswon": True})
                    bet.update({"profit": profit, "status": "closed"})
                else:
                    profit = -1 * bet["amount"]
                    bet.update({"profit": profit, "status": "closed"})
        setattr(self, "bets", bets)

    def set_next_hash_and_mult(self):
        def get_result(game_hash):
            hm = hmac.new(str.encode(game_hash), b"", hashlib.sha256)
            hm.update(game_hash.encode("utf-8"))
            hashish = hm.hexdigest()

            if int(hashish, 16) % 33 == 0:
                return (hashish, 1)

            h = int(hashish[:13], 16)
            e = 2**52
            result = (((100 * e - h) / (e - h)) // 1) / 100.0
            return (hashish, result)

        if self.data.game_history.empty:
            hashish, multiplier = get_result(SALT_HASH)
        else:
            last_hash = self.data.game_history["hash"].values[-1]
            hashish, multiplier = get_result(last_hash)

        setattr(self, "hash", hashish)
        setattr(self, "multiplier", multiplier)
        return (hashish, multiplier)

    async def countdown_bets_timer(self):
        while True:
            if datetime.now() > self.start_time:
                self.toggle_state()
                print("BETS OFF")
                return
            await asyncio.sleep(1)

    async def countdown_bets(self):
        # thread = threading.Thread(target=self.countdown_bets_timer)
        # thread.start()
        # thread.join()
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        # loop.run_until_complete(self.countdown_bets_timer())
        # loop.close()
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
        bets = pd.DataFrame(self.bets)
        if bets.empty:
            return []

        unique_ads = bets.address.unique()
        final = []
        for address in unique_ads:
            player_bets = bets[bets.address == address]
            total_bets = np.sum(player_bets.amount)
            state = player_bets.status.values[0]
            bet = {
                "walletAddress": address,
                "betAmount": total_bets,
                "state": state,
            }
            final.append(bet)

        final.reverse()
        return final

    async def end_game(self):
        # identifier, timestamp, pool_size, multiplier,
        # bets_won, house_profit, house_balance

        pool_size = 0
        for bet in self.bets:
            pool_size += bet["amount"]

        player_profits = 0
        losers = []
        for bet in self.bets:
            if bet["haswon"]:
                player_profits += bet["amount"]
            else:
                losers.append(bet)

        for bet in losers:
            self.cashout(bet["address"], 0.0, lost=True)

        house_profits = pool_size - player_profits

        setattr(self, "timestamp", datetime.now())
        setattr(self, "house_profit", house_profits)
        setattr(self, "pool_size", pool_size)
        setattr(self, "house_balance", self.house_balance + house_profits)

        self.save_game_history()
        self.save_bets_history()
        await asyncio.sleep(1)
        self.start_new_game()

    def save_game_history(self):
        print("Saving history: ")
        self.data.db.add_row("games", self.to_tuple())

    def save_bets_history(self):
        print("Saving bets: ")
        bets = self.bets_to_list_of_tuples()
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
        for elem in self.bets:
            dic = []
            for col in cols:
                if col in elem.keys():
                    if col == "timestamp":
                        dic.append(elem[col])
                    else:
                        dic.append(elem[col])

            final.append(tuple(dic))
        return final

    def add_field(self, dic):
        for key in dic.keys:
            setattr(self, key, dic[key])

    def add_bet(self, bet: Bet):
        if datetime.now() > self.start_time or self.state == "play":
            self.toggle_state()
            return False

        new_bets = self.bets
        new_bet = bet.to_dict()
        new_bet.update({"hash": self.hash})
        new_bets.append(new_bet)
        print(new_bets)
        setattr(self, "bets", new_bets)
        return True

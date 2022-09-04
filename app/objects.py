from database import GameHistory
from datetime import datetime, timedelta
from vars import STARTING_WALLET_AMT, SALT_HASH
import hashlib
import random
import hmac
import pandas as pd
import asyncio


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
        self.state = "betting"
        self.house_balance = self.get_house_balance()
        self.bets = []
        self.start_time = datetime.now()
        self.end_bets = self.start_time + timedelta(minutes=1)
        self.sec_to_end = int((self.multiplier - 1) * 10)
        self.end_game_ts = self.end_bets + timedelta(seconds=self.sec_to_end)

    def _get_id(self):
        if self.data.game_history.empty:
            return 0
        else:
            print(self.data.game_history)
            gameid = self.data.game_history["id"].values[-1] + 1
        return gameid

    def get_house_balance(self):
        if self.data.game_history.empty:
            balance = STARTING_WALLET_AMT
        else:
            balance = self.data.game_history["house_balance"].values[-1]
        return balance

    def cashout(self, wallet, mult):
        bets = self.bets
        for bet in bets:
            if bet["address"] == wallet:
                if self.state != "ended":
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

    async def is_game_over(self):
        await asyncio.sleep(3)

    def end_game(self):
        # identifier, timestamp, pool_size, multiplier,
        # bets_won, house_profit, house_balance
        setattr(self, "state", "ended")
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
            self.cashout(bet["address"], 0.0)

        house_profits = pool_size - player_profits

        setattr(self, "timestamp", self.end_game_ts)
        setattr(self, "house_profit", house_profits)
        setattr(self, "pool_size", pool_size)
        setattr(self, "house_balance", self.house_balance + house_profits)

        self.save_game_history()
        self.save_bets_history()

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
        new_bets = self.bets
        new_bet = bet.to_dict()
        new_bet.update({"hash": self.hash})
        new_bets.append(new_bet)
        print(new_bets)
        setattr(self, "bets", new_bets)

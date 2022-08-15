from database import GameHistory
from datetime import datetime, timedelta
from vars import STARTING_WALLET_AMT, SALT_HASH
import hashlib
import random
import hmac
import pandas as pd


class Bet:
    """docstring for Bet"""

    def __init__(self, address, amount):
        self.address = address
        self.amount = amount
        self.timestamp = datetime.now().isoformat()
        self.multiplier = 0
        self.status = "open"
        self.hasWon = False
        self.profit = 0

    def cashout(self, multiplier):
        if isinstance(multiplier, float):
            profit = self.amount * multiplier

            setattr(self, "multiplier", multiplier)
            setattr(self, "status", "closed")
            setattr(self, "hasWon", True)
            setattr(self, "profit", profit)

    def to_dict(self):
        cols = [
            "timestamp",
            "address",
            "amount",
            "hasWon",
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
        self.house = STARTING_WALLET_AMT
        self.bets = []
        self.start_time = datetime.now()
        self.end_bets = self.start_time + timedelta(minutes=1)
        self.sec_to_end = int((self.multiplier - 1) * 10)
        self.end_game_ts = self.end_bets + timedelta(seconds=self.sec_to_end)

    def _get_id(self):
        if self.data.game_history.empty:
            return 0
        else:
            gameid = self.data.game_history["identifier"].values[-1] + 1
        return gameid

    def cashout(self, wallet):
        for bet in self.bets:
            if self.state != "ended":
                if bet["address"] == wallet:
                    profit = bet["amount"] * self.multiplier
                    bet.update({"profit": profit})
            else:
                profit = -1 * bet["amount"]
                bet.update({"profit": profit})

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

    def end_game(self):
        # identifier, timestamp, pool_size, multiplier,
        # bets_won, house_profit, house_balance
        pool_size = 0
        for bet in self.bets:
            pool_size += bet["amount"]

        player_profits = 0
        losers = []
        for bet in self.bets:
            if bet["hasWon"]:
                player_profits += bet["amount"]
            else:
                losers.append(bet)

        for bet in losers:
            self.cashout(bet["address"])

        house_profits = pool_size - player_profits

        setattr(self, "timestamp", self.end_game_ts)
        setattr(self, "house_profit", house_profits)
        setattr(self, "house", self.house + house_profits)
        new_col = pd.DataFrame(self.to_dict())
        df = self.data.game_history.append(new_col)
        print(df)
        df.to_csv(self.data.history_path, index=False)

    def to_dict(self):
        cols = self.data.map["game_history"].keys()
        dic = {}
        for col in cols:
            if hasattr(self, col):
                dic.update({col: getattr(self, col)})
        return dic

    def add_field(self, dic):
        for key in dic.keys:
            setattr(self, key, dic[key])

    def add_bet(self, bet: Bet):
        new_bets = self.bets
        new_bets.append(bet.to_dict())
        print(new_bets)
        setattr(self, "bets", new_bets)

from database import GameHistory
from datetime import datetime
from vars import STARTING_WALLET_AMT


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
        cols = ["timestamp", "address", "amount", "multiplier", "status"]
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
        self.house = STARTING_WALLET_AMT
        self.bets = []

    def _get_id(self):
        if self.data.game_history.empty:
            return 0
        else:
            gameid = self.data.game_history.loc[-1]["identifier"] + 1
        return gameid

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

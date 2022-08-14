from database import GameHistory


class Game:
    """docstring for Game"""

    def __init__(self, game={}):
        self.data = GameHistory()
        self.identifier = self._get_id()

    def _get_id(self):
        gameid = self.data.game_history.loc[-1]["identifier"] + 1
        return gameid

    def to_dict(self):
        cols = self.data.map["game_history"].keys()
        dic = {}
        for col in cols:
            if hasattr(self, col):
                dic.update({col: self.col})
        return dic

    def add_field(self, dic):
        for key in dic.keys:
            setattr(self, key, dic[key])


class Bet:
    """docstring for Bet"""

    def __init__(self, address, amount):
        self.arg = arg

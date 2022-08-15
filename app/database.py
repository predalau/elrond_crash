from time import time
from vars import DATABASE_PATH, DATABASE_MAP
import pandas as pd
import os


class GameHistory:
    """docstring for Elrond Crash Database"""

    def __init__(self):
        self.map = DATABASE_MAP
        self.history_path = DATABASE_PATH
        self.game_history = self._import_game_history()
        self.last_ten_multipliers = self.get_last_multipliers()

    def _import_game_history(self):
        if os.path.isfile(self.history_path):
            df = pd.read_csv(self.history_path)
            return df
        else:
            schema = self.map["game_history"]
            df = pd.DataFrame.from_dict(schema)
            df.to_csv(self.history_path)
            return df

    def get_last_multipliers(self):
        if hasattr(self, "game_history") and not self.game_history.empty:
            if len(self.game_history["multiplier"].values) < 10:
                return self.game_history["multiplier"].values
            else:
                return self.df.loc[-10:]["multiplier"].values
        else:
            return []

    def get_last_game_bets(self):
        if self.game_history.empty:
            bets = []
        else:
            bets = self.game_history["bets"].values[-1]

        cols = {
            "address": "walletAddress",
            "amount": "betAmount",
            "profit": "profit",
            "hasWon": "hasWon",
        }
        parsed_bets = []
        print(bets)
        print(type(bets))
        for bet in bets:
            dic = {}
            for col in cols.keys():
                dic.update({col: bet[col]})

            parsed_bets.append(dic)

        return parsed_bets

    def add_new_game(self, game):
        last_game_id = self.game_history.loc[-1].id
        timestamp = time.now()
        game.update(
            {
                "id": last_game_id,
                "timestamp": timestamp,
            }
        )
        new_history = self.game_history.append([game])
        self._update_history(new_history)

    def _update_history(self, new_history):
        setattr("game_history", new_history)
        pd.to_csv(self.history_path)

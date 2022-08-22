from time import time
from vars import DATABASE_PATH, DATABASE_MAP, BETS_PATH
import pandas as pd
import os


class GameHistory:
    """docstring for Elrond Crash Database"""

    def __init__(self):
        self.map = DATABASE_MAP
        self.history_path = DATABASE_PATH
        self.bets_path = BETS_PATH
        self.game_history = self._import_game_history()
        self.bet_history = self._import_bet_history()
        self.last_ten_multipliers = self.get_last_multipliers()

    def _import_game_history(self):
        if os.path.isfile(self.history_path):
            df = pd.read_csv(self.history_path)
            return df
        else:
            schema = self.map["game_history"]
            df = pd.DataFrame.from_dict(schema)
            df.to_csv(self.history_path, index=False)
            return df

    def _import_bet_history(self):
        if os.path.isfile(self.bets_path):
            df = pd.read_csv(self.bets_path)
            return df
        else:
            schema = self.map["bet_history"]
            df = pd.DataFrame.from_dict(schema)
            df.to_csv(self.bets_path, index=False)
            return df

    def get_last_multipliers(self):
        if hasattr(self, "game_history") and not self.game_history.empty:
            if len(self.game_history["multiplier"].values) < 10:
                multipliers = self.game_history["multiplier"].tolist()
            else:
                multipliers = self.game_history["multiplier"].loc[-10:].tolist()
            return multipliers

        else:
            return []

    def get_last_game_bets(self):
        if self.bet_history.empty:
            bets = []
        else:
            hashish = self.game_history.hash.values[-1]
            print(hashish)
            bets = self.bet_history[self.bet_history["hash"] == hashish]

        cols = {
            "address": "walletAddress",
            "amount": "betAmount",
            "profit": "profit",
            "hasWon": "hasWon",
        }
        parsed_bets = []
        print(bets)
        print(type(bets))
        for i, bet in bets.iterrows():
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

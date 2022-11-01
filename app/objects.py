from database import GameHistory
from vars import STARTING_WALLET_AMT, SALT_HASH  # , REWARDS_WALLET
from datetime import datetime, timedelta
import hashlib
import hmac
import pandas as pd
import numpy as np
import asyncio


class Bets:
    """docstring for Bet"""

    def __init__(self):
        self.to_list = []

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

    def to_list_of_tuples(self):
        final = []
        for bet in self.to_list:
            final.append(bet.to_tuple())

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
            setattr(self, "bets", final)


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

    def to_tuple(self):
        final = []
        for col in self.cols:
            if hasattr(self, col):
                final.append(getattr(self, col))
        return tuple(final)

    def merge(self, bet):
        setattr(self, "amount", self.amount + bet.amount)

    def cashout(self, mult):
        if mult <= 0:
            setattr(self, "haswon", False)
            setattr(self, "profit", -1 * self.amount)
        else:
            setattr(self, "haswon", True)
            setattr(self, "profit", self.amount * mult)

        setattr(self, "state", "closed")


class Game:
    """docstring for Game"""

    def __init__(self):
        # todo self.house_address = REWARDS_WALLET
        self.data = GameHistory()
        self.identifier = self._get_id()
        self.set_next_hash_and_mult()
        self.state = "bet"
        self.delay = 0.1
        self.house_balance = self.get_house_balance()
        self.bets = Bets()
        self.start_time = datetime.now() + timedelta(seconds=5)
        self.set_mult_array()

    @property
    def _state(self):
        return self.state

    @_state.setter
    def _state(self, a):
        self.state = a

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
        delays = [0.1, 0.04, 0.02]

        assert hasattr(self, "runtime_index")
        assert hasattr(self, "multiplier_now")
        assert hasattr(self, "mult_array")

        i = self.runtime_index
        if i == -1:
            print("i is -1")
            return

        mult_now = self.multiplier_now
        player_potential_wins = 0

        for bet in self.bets.to_list:
            if bet.haswon:
                player_potential_wins += bet.profit
            else:
                player_potential_wins += bet.amount * mult_now

        if i >= len(self.mult_array) - 1:
            setattr(self, "multiplier_now", -1)
            setattr(self, "runtime_index", -1)
        else:
            setattr(
                self,
                "multiplier_now",
                float(format(self.mult_array[i + 1], ".2f")),
            )
            setattr(self, "runtime_index", i + 1)

        if player_potential_wins > 0.05 * self.house_balance:
            print("FORCED CRASH!")
            setattr(self, "multiplier_now", -1)
            setattr(self, "runtime_index", -1)

        if mult_now > 0 and mult_now < 2:
            setattr(self, "delay", delays[0])
        elif mult_now >= 2 and mult_now < 3.5:
            setattr(self, "delay", delays[1])
        elif mult_now >= 3.5:
            setattr(self, "delay", delays[2])


    def get_countdown_as_str(self):
        if self.state != "bet":
            return "00.0"
        else:
            cdown = self.start_time - datetime.now()
            mm, ss = divmod(cdown.seconds, 60)
            hh, mm = divmod(mm, 60)
            if mm == 0:
                s = "%02d.%2d" % (ss, cdown.microseconds / 10000)
            elif mm == 59:
                return "00.0"
            elif ss == 0:
                return "00." + str(cdown.microseconds/ 10000)
            else:
                s = "%02d:%02d.%2d" % (mm, ss, cdown.microseconds / 10000)

            return s

    def toggle_state(self):
        curr_state = self._state

        if curr_state == "bet":
            self.state = "play"
        elif curr_state == "play":
            self.state = "end"
        elif curr_state == "end":
            self.state = "bet"

        print("Game state: \t", self.state)

    def _get_id(self):
        if self.data.game_history.empty:
            return 0
        else:
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

    def get_house_balance(self):  # todo Change to actual house wallet
        if self.data.game_history.empty:
            balance = STARTING_WALLET_AMT
        else:
            balance = self.data.game_history["house_balance"].values[-1]
            # req_url = f"https://api.elrond.com/accounts/{REWARDS_WALLET}"
            # req = get_http_request(req_url)
            # req = json.loads(req)
            # balance = float(req["balance"]) / 10**18

        return balance

    def cashout(self, wallet, lost=False):
        for bet in self.bets.to_list:
            if not lost and bet.address == wallet:
                bet.cashout(self.multiplier_now)
            elif lost and bet.address == wallet:
                bet.cashout(-1)

    def set_next_hash_and_mult(self):
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

        if self.data.game_history.empty:
            gme_hash, multiplier = get_result(SALT_HASH)
        else:
            last_hash = self.data.game_history["hash"].values[-1]
            gme_hash, multiplier = get_result(last_hash)

        setattr(self, "hash", gme_hash)
        setattr(self, "multiplier", multiplier)
        return gme_hash, multiplier

    async def countdown_bets_timer(self):
        while True:
            if datetime.now() > self.start_time:
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

    async def end_game(self, manual=False):  # todo add SC call with winning bets
        self.toggle_state()
        await asyncio.sleep(5)
        pool_size = 0
        for bet in self.bets.to_list:
            pool_size += bet.amount

        player_profits = 0

        for bet in self.bets.to_list:
            if bet.haswon:
                player_profits += bet.amount

        self.force_cashout()

        house_profits = pool_size - player_profits

        setattr(self, "timestamp", datetime.now())
        setattr(self, "house_profit", house_profits)
        setattr(self, "pool_size", pool_size)
        setattr(self, "house_balance", self.house_balance + house_profits)

        if manual:
            print("MANUALLY crashed the game")

        self.save_game_history()
        self.save_bets_history()
        self.__init__()
        self.bets.__init__()

    def save_game_history(self):
        print("Saving history: ")
        self.data.db.add_row("games", self.to_tuple())

    def save_bets_history(self):
        print("Saving bets: ")
        bets = self.bets.to_list_of_tuples()
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

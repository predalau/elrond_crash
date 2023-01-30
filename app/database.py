from datetime import datetime, timedelta
from vars import (
    DATABASE_PATH,
    DATABASE_MAP,
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASS,
)
import psycopg2
import pandas as pd
import warnings
import logging

logger = logging.getLogger("fastapi")
logger.setLevel(logging.DEBUG)
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")


class ElrondCrashDatabase:
    """docstring for ElrondDatabase"""

    def __init__(self):
        self.db_name = DATABASE_PATH
        self.map = DATABASE_MAP
        self.conn = self._connect()
        self.cur = self.conn.cursor()

    def _connect(self):
        """
        Function connects to db and returns connection object

        Returns:
        psycopg2 connection obj
        """
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=self.db_name,
                user=DB_USER,
                password=DB_PASS,
            )
            return conn
        except UserWarning:
            pass

    def create_table(self, table: str, cols: list, pkey=False):
        """
        Function that creates a table in the 'elrond.db' Database

        Params:
        table (str): e.x. 'deadrare_coll_stats'
        cols (list of dict): List of dicts containing name and
            dtype of the table's columns

        Returns:
        None
        """
        sql = f"""CREATE TABLE IF NOT EXISTS {table}("""

        if pkey:
            unique_str = "PRIMARY KEY"
        else:
            unique_str = ""

        for i, elem in enumerate(cols):
            if i == 0:
                sql += f"{elem['name']} {elem['dtype']}{unique_str},"
            elif i == len(cols) - 1:
                sql += f"{elem['name']} {elem['dtype']});"
            else:
                sql += f"{elem['name']} {elem['dtype']},"
        print(sql)
        self.cur.execute(sql)
        res = self.conn.commit()
        print(res)

    def execute(self, sql):
        """
        Execute SQL query in the 'elrond.db' Database

        Params:
        sql (str): The SQL query

        Returns:
        list
        """
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()
        return

    def add_row(self, table, data):
        """
        Function add a row in a specified table within
        the 'elrond.db' Database

        Params:
        table (str): the name of the table to append to
        data (tuple): tuple of all the values of the row

        Returns:
        None
        """
        sql = f"""INSERT INTO {table} VALUES {str(data)};"""
        self.cur.execute(sql)
        self.conn.commit()
        logger.info(f"Adding row to '{table}':\t{data}")

    def remove_by(self, table, condition):
        """
        Function removes item/s from a table in 'elrond.db'
        based on a criteria. Ex: DELETE FROM table WHERE id=0;

        Params:
        table (str): the name of the tableto remove from
        condition (str): The contition

        Returns:
        None
        """
        self.cur.execute(f"DELETE FROM {table} where {condition};")
        self.conn.commit()

    def get_by_condition(self, table, condition):
        """
        Function add a row in a specified table within
        the 'elrond.db' Database

        Params:
        table (str): the name of the table to append to
        data (tuple): tuple of all the values of the row

        Returns:
        None
        """
        sql = f"""SELECT * FROM {table} where {condition};"""
        self.cur.execute(sql)
        self.conn.commit()
        return self.cur.fetchall()

    def get_table(self, table, limit=-1):
        """
        Function returns a pandas DataFrame of a table in
        'elrond.db'

        Params:
        table (str): the name of the table

        """
        if limit > 0:
            df = pd.read_sql_query(
                f"SELECT * FROM {table} ORDER BY timestamp DESC LIMIT {limit}",
                self.conn,
            )
        else:
            df = pd.read_sql_query(
                f"SELECT * FROM {table}",
                self.conn,
            )
        return df

    def get_last_rows(self):
        dic = {}
        for table in self.map.keys():
            sql = f"""SELECT * FROM {table} ORDER BY id DESC LIMIT 1;"""
            row = self.execute(sql)

            if row:
                dic.update({table: row[0]})
            else:
                dic.update({table: (-1,)})

        return dic

    def get_column(self, table, column):
        sql = f"""SELECT {column} from {table};"""
        column = self.execute(sql)
        return column

    def update_user(self, schema):
        set_str = ""
        immutable_cols = ["address", "discord_id"]
        for col, val in schema.items():
            if col not in immutable_cols:
                if type(val) == str:
                    set_str = set_str + col + "='" + str(val) + "', "
                else:
                    set_str = set_str + col + "=" + str(val) + ", "

        sql = f"""UPDATE users_dev SET {set_str[:-2]} WHERE address='{schema["address"]}';"""
        print(sql)
        self.execute(sql)
        return


class GameHistory:
    """docstring for Elrond Crash Database"""

    def __init__(self):
        self.map = DATABASE_MAP
        self.history_path = DATABASE_PATH
        self.db = ElrondCrashDatabase()
        self.game_history = self._import_game_history()
        self.bet_history = self._import_bet_history()
        self.user_table = self._import_user_history()
        self.last_ten_multipliers = self.get_last_multipliers()

    def _import_game_history(self):
        df = self.db.get_table("games_2023")
        return df

    def _import_bet_history(self):
        df = self.db.get_table("bets")
        return df

    def _import_user_history(self):
        df = self.db.get_table("users_dev")
        return df

    def get_weekly_leaderboard(self):
        sql_query = "select * from bets where timestamp >= current_date - 7 and timestamp <= current_date"
        df = pd.read_sql_query(
            sql_query,
            self.db.conn,
        )
        unique_bettors = df["address"].unique()
        final = []

        for addr in unique_bettors:
            volume = df[df["address"] == addr]["amount"].sum()
            profit = df[df["address"] == addr]["profit"].sum()
            final.append(
                {"address": addr, "volume": float("{:.2f}".format(volume)), "profit": float("{:.2f}".format(profit))})

        final = pd.DataFrame(final)
        final = final.sort_values(by=["volume"], ascending=[False])
        final_list = []

        for i, elem in final.iterrows():
            final_list.append(elem.to_json())

        return final_list

    def get_user_profile(self, address, interval=1):
        from_ts = datetime.now() - timedelta(days=interval)
        from_ts = from_ts.date()
        user_df = self.user_table[self.user_table["address"] == address]
        print(user_df.to_string())
        user_bets = self.bet_history.loc[
            (self.bet_history["address"] == address) & (self.bet_history["timestamp"] > from_ts)
            ]

        if user_bets.empty:
            final = {"address": address, "top_win": 0, "total_games": 0}
        else:
            top_win = user_bets["profit"].max()
            tot_games = user_bets.shape[0]
            final = {"address": address, "top_win": top_win, "total_games": tot_games}

        if user_df.empty:
            return final
        else:
            user_data = user_df[
                [
                    "discord_name",
                    "discord_id",
                    "avatar_hash",
                    "exp",
                    "raffle_tickets",
                    "title",
                ]
            ].iloc[0].to_dict()
            print(user_data)
            final.update(user_data)

        final.update({"interval_in_days": interval})
        return final

    def get_player_weekly_stats(self, addr: str) -> dict:
        sql_query = f"select * from bets where address='{addr}' and timestamp >= date_trunc('week', current_date) - interval '1 week'"
        df = pd.read_sql_query(
            sql_query,
            self.db.conn,
        )
        final = {"volume": df["amount"].sum(), "profit": df["profit"].sum(), "games_played": df.shape[0]}
        return final

    def get_user_last_bets(self, addr: str):
        sql_query = f"select * from bets where address='{addr}'"
        df = pd.read_sql_query(
            sql_query,
            self.db.conn,
        )
        final = []
        df = df.iloc[-10:]
        if df.empty:
            return final
        cols = ["timestamp", "address", "amount", "profit"]
        for i, row in df.iterrows():
            final.append(row[cols].to_dict())

        final.reverse()

        return final

    def get_last_multipliers(self):
        if hasattr(self, "game_history") and not self.game_history.empty:
            if len(self.game_history["multiplier"].values) < 30:
                multipliers = self.game_history["multiplier"].tolist()
            else:
                multipliers = self.game_history["multiplier"].tolist()[-30:]
            return multipliers

        else:
            return []

    def get_latest_games(self):
        if hasattr(self, "game_history") and not self.game_history.empty:
            if len(self.game_history["multiplier"].values) < 30:
                games = self.game_history[["timestamp", "tx_hash", "multiplier", "pool_size", "house_profit"]]
            else:
                games = self.game_history.iloc[-30:][
                    ["timestamp", "tx_hash", "multiplier", "pool_size", "house_profit"]]

            games["house_profit"] = games["house_profit"].apply(lambda x: x * -1)
            games.rename(columns={"house_profit": "players_total_profits"}, inplace=True)
            games = games.to_dict("records")
            return games
        else:
            return []

    def get_last_game_bets(self):
        if self.bet_history.empty:
            bets = []
            return bets
        else:
            hashish = self.game_history["hash"].values[-1]
            bets = self.bet_history[self.bet_history["hash"] == hashish]

        cols = {
            "address": "walletAddress",
            "amount": "betAmount",
            "profit": "profit",
            "haswon": "haswon",
        }
        parsed_bets = []

        for i, bet in bets.iterrows():
            dic = {}
            for col in cols.keys():
                dic.update({col: bet[col]})

            parsed_bets.append(dic)

        return parsed_bets

    def new_user(self, user: dict):
        users_table = self.user_table
        assert "address" in user.keys()
        user_schema = {
            "id": 1,
            "timestamp": datetime.now().isoformat(),
            "address": "",
            "discord_name": "",
            "discord_id": 0,
            "avatar_hash": "",
            "exp": 0,
            "raffle_tickets": 0,
            "is_private": True,
            "has_title": False,
            "title": "",
        }

        usr_df = users_table[users_table["address"] == user["address"]]
        for col in user.keys():
            if col in user_schema.keys():
                user_schema.update({col: user[col]})

        if usr_df.empty:
            self.db.add_row("users_dev", tuple(user_schema.values()))
        else:
            self.db.update_user(user_schema)

    def add_new_game(self, game):
        last_game_id = self.game_history.loc[-1].id
        timestamp = datetime.now()
        game.update(
            {
                "id": last_game_id + 1,
                "timestamp": timestamp,
            }
        )
        new_history = self.game_history.append([game])
        setattr(self, "game_history", new_history)
        new_row = tuple(game.values())
        self._update_game_history(new_row)

    def _update_game_history(self, new_row):
        self.db.add_row("games", new_row)

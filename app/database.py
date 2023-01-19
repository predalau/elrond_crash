from datetime import datetime
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
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=self.db_name,
            user=DB_USER,
            password=DB_PASS,
        )
        return conn

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
        self.cur.execute(sql)
        self.conn.commit()
        return self.cur.fetchall()

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
        print(f"Adding row to '{table}':\t", data)
        sql = f"""INSERT INTO {table} VALUES {str(data)};"""
        self.cur.execute(sql)
        self.conn.commit()

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


class GameHistory:
    """docstring for Elrond Crash Database"""

    def __init__(self):
        self.map = DATABASE_MAP
        self.history_path = DATABASE_PATH
        self.db = ElrondCrashDatabase()
        self.game_history = self._import_game_history()
        self.bet_history = self._import_bet_history()
        self.last_ten_multipliers = self.get_last_multipliers()

    def _import_game_history(self):
        df = self.db.get_table("games_2023")
        return df

    def _import_bet_history(self):
        df = self.db.get_table("bets")

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
                games = self.game_history[["timestamp", "tx_hash", "multiplier", "pool_size"]].to_dict("records")
            else:
                games = self.game_history.iloc[-30:][["timestamp", "tx_hash", "multiplier", "pool_size"]].to_dict("records")
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

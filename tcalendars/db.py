import sqlite3
import os
from os import path
import pandas as pd
from contextlib import closing

class DatabaseManager:
    def __init__(self, db_dir=None):
        if db_dir is None:
            # 默认路径为 tcalendars/cache/data.dat
            self.db_dir = path.join(path.abspath(path.dirname(__file__)), 'cache')
        else:
            self.db_dir = path.join(path.abspath(db_dir), 'cache')
            
        self.db_path = path.join(self.db_dir, 'data.dat')
        os.makedirs(self.db_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            # 初始化 metadata 表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    table_name TEXT PRIMARY KEY,
                    last_update TEXT
                )
            ''')
            # 初始化 se_calendar 表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS se_calendar (
                    zrxh INTEGER,
                    jybz INTEGER,
                    jyrq TEXT PRIMARY KEY
                )
            ''')
            conn.commit()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_last_update(self, table_name):
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT last_update FROM metadata WHERE table_name = ?', (table_name,))
            row = cursor.fetchone()
            return row[0] if row else None

    def set_last_update(self, table_name, last_update):
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO metadata (table_name, last_update) VALUES (?, ?)', (table_name, last_update))
            conn.commit()

    def save_dataframe(self, table_name, df, if_exists='replace'):
        with closing(self.get_connection()) as conn:
            df.to_sql(table_name, conn, if_exists=if_exists, index=False)
            conn.commit()

    def read_dataframe(self, table_name):
        with closing(self.get_connection()) as conn:
            try:
                return pd.read_sql(f'SELECT * FROM {table_name}', conn)
            except Exception:
                return pd.DataFrame()

    def execute(self, sql, params=None):
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            conn.commit()
            return cursor

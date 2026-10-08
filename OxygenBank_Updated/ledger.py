"""SQLite-backed transaction ledger. State = baseline + replay of all transactions."""
import sqlite3
from contextlib import closing
import pandas as pd
import config as C
from model import apply_transaction


def _conn():
    return sqlite3.connect(C.DB_PATH)


def init_db():
    with closing(_conn()) as c, c:
        c.execute("""CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT DEFAULT CURRENT_TIMESTAMP,
            kind TEXT NOT NULL, category TEXT NOT NULL,
            quantity REAL NOT NULL, note TEXT)""")


def add_transaction(kind, category, quantity, note=""):
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO transactions (kind, category, quantity, note) VALUES (?,?,?,?)",
                  (kind, category, float(quantity), note))


def get_transactions() -> pd.DataFrame:
    with closing(_conn()) as c:
        return pd.read_sql_query("SELECT * FROM transactions ORDER BY id", c)


def reset():
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM transactions")


def replay(baseline, df):
    s = baseline
    for row in df.itertuples():
        s = apply_transaction(s, row.category, row.quantity)
    return s

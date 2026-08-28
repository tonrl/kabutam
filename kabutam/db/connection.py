import os
import sqlite3
from pathlib import Path


# DB_PATH = "jquants.db"
def get_db_path():
    data_dir = (
        Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        / "kabutam"
    )
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "jquants.db"


def require_master_data(conn):
    row = conn.execute("""
        SELECT 1 FROM sqlite_master
        WHERE type = 'table' AND name = 'equities_master'
    """).fetchone()

    if row is None:
        raise SystemExit(
            "銘柄テーブルが存在しません。\n先に `kabutam --init` を実行してください。"
        )


def require_edi_data(conn):
    row = conn.execute("""
        SELECT 1 FROM sqlite_master
        WHERE type = 'table' AND name = 'edinet_corp_data'
    """).fetchone()
    return row is not None


def get_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    return conn

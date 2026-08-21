import jpholiday
from datetime import datetime, timedelta, time
from kabutam.stock.yfinancetool import fetch_prices
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

PRICE_UPDATE_TIME = time(16, 30)
FETCH_DAYS = 14

def create_prices_table(conn):
    """pricesテーブルが存在しない場合に作成する"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            Date TEXT,
            Code TEXT,
            Open REAL,
            High REAL,
            Low REAL,
            Close REAL,
            Volume REAL,
            AdjOpen REAL,
            AdjHigh REAL,
            AdjLow REAL,
            AdjClose REAL,
            AdjVolume REAL,
            PRIMARY KEY (Date, Code)
        )
    """)
    conn.commit()

def ensure_prices_table_exists(conn):
    """pricesテーブルが存在しない場合のみ作成する"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM sqlite_master WHERE type='table' AND name='prices'
    """)
    if not cursor.fetchone():
        print("priceテーブルを作成します")
        create_prices_table(conn)

def get_recent_prices(conn, code, days=3):
    """
    DBに保存されている最新の株価を取得する。
    CloseがNULLのデータは無視する。
    """

    return conn.execute("""
        SELECT
            Date,
            Open,
            High,
            Low,
            Close,
            Volume,
            AdjOpen,
            AdjHigh,
            AdjLow,
            AdjClose,
            AdjVolume
        FROM prices
        WHERE Code = ?
            AND Close IS NOT NULL
        ORDER BY Date DESC
        LIMIT ?
    """, (code, days)).fetchall()


def get_latest_price_date(conn, code):
    """
    最新の確定終値の日付を取得する。

    """
    ensure_prices_table_exists(conn)

    row = conn.execute("""
        SELECT MAX(Date)
        FROM prices
        WHERE Code = ?
            AND Close IS NOT NULL

    """, (code,)).fetchone()

    if row is None or row[0] is None:
        return None

    return datetime.strptime(
        row[0],
        "%Y-%m-%d"
    ).date()


def update_prices(conn, code, days=3, before_today=False):
    """
    yfinanceから株価を取得してDBへ保存する。
    """

    # records = fetch_prices(code, days)
    records = fetch_prices(
        code,
        days,
        before_today=before_today
    )


    if not records:
        return False

    conn.executemany("""
        INSERT OR REPLACE INTO prices (
            Date,
            Code,
            Open,
            High,
            Low,
            Close,
            Volume,
            AdjOpen,
            AdjHigh,
            AdjLow,
            AdjClose,
            AdjVolume
        )
        VALUES (
            :Date,
            :Code,
            :Open,
            :High,
            :Low,
            :Close,
            :Volume,
            :AdjOpen,
            :AdjHigh,
            :AdjLow,
            :AdjClose,
            :AdjVolume
        )
    """, records)

    conn.commit()

    return True

def is_trading_day(date):
    """日本株の営業日かどうか"""
    return date.weekday() < 5 and not jpholiday.is_holiday(date)


def expected_latest_close_date(now=None):
    """
    DBに存在すべき最新の確定終値の日付を返す
    16:30以前は当日の終値が未確定の可能性があるので前日を対象にする。
    """
    now = now or datetime.now()
    target = now.date()

    if now.time() < PRICE_UPDATE_TIME:
        target -= timedelta(days=1)

    # 土日祝日などの非営業日は直前の営業日まで戻る
    while not is_trading_day(target):
        target -= timedelta(days=1)

    return target



def ensure_recent_prices(conn, code, days=3):
    """
    DBの株価が古ければyfinanceから更新する。
    CloseがNULLの当日データは終値として使用しない
    16:30以降:
        当日の確定終値がDBになければ更新を試みる。
    """

    now = datetime.now(JST)
    target = expected_latest_close_date(now)
    latest_date = get_latest_price_date(conn, code)

    if latest_date is None or latest_date < target:
        update_prices(
            conn,
            code,
            days=FETCH_DAYS,
            before_today=now.time() < PRICE_UPDATE_TIME,
        )
    return get_recent_prices(conn, code, days)



from datetime import (datetime, date)
from kabutam.stock.saveprice import (
        create_prices_table,
        ensure_recent_prices,
        expected_latest_close_date,
        is_trading_day,
        get_latest_price_date
)
import sqlite3
from unittest.mock import patch



def test_expected_latest_close_date_before_1630():
    now = datetime(2026, 8, 21, 15, 0)

    result = expected_latest_close_date(now)

    assert result == date(2026, 8, 20)


def test_expected_latest_close_date_saturday():
    """土曜日なら直前の金曜日を返す"""
    now = datetime(2026, 8, 22, 17, 0)

    result = expected_latest_close_date(now)

    assert result == date(2026, 8, 21)

def test_expected_latest_close_date_monday_before_1630():
    """月曜日16:30前なら前週金曜日を返す"""
    now = datetime(2026, 8, 24, 15, 0)

    result = expected_latest_close_date(now)

    assert result == date(2026, 8, 21)

def test_is_trading_day_weekday():
    """通常の平日は営業日"""
    assert is_trading_day(date(2026, 8, 24)) is True  # 月曜日


def test_is_trading_day_saturday():
    """土曜日は非営業日"""
    assert is_trading_day(date(2026, 8, 22)) is False


def test_is_trading_day_sunday():
    """日曜日は非営業日"""
    assert is_trading_day(date(2026, 8, 23)) is False


def test_is_trading_day_holiday():
    """祝日は非営業日"""
    assert is_trading_day(date(2026, 11, 3)) is False  # 文化の日


def test_is_trading_day_weekday_not_holiday():
    """平日かつ祝日ではない日は営業日"""
    assert is_trading_day(date(2026, 11, 4)) is True

def test_get_latest_price_date():
    """最新のCloseが存在する日付を取得できる"""
    conn = sqlite3.connect(":memory:")
    create_prices_table(conn)

    conn.execute("""
        INSERT INTO prices (
            Date, Code, Open, High, Low, Close, Volume,
            AdjOpen, AdjHigh, AdjLow, AdjClose, AdjVolume
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "2026-08-20",
        "7203",
        1000,
        1100,
        990,
        1050,
        100000,
        1000,
        1100,
        990,
        1050,
        100000,
    ))

    conn.execute("""
        INSERT INTO prices (
            Date, Code, Open, High, Low, Close, Volume,
            AdjOpen, AdjHigh, AdjLow, AdjClose, AdjVolume
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "2026-08-21",
        "7203",
        1050,
        1150,
        1040,
        1100,
        120000,
        1050,
        1150,
        1040,
        1100,
        120000,
    ))

    conn.commit()

    result = get_latest_price_date(conn, "7203")

    assert result == date(2026, 8, 21)

    conn.close()


def test_get_latest_price_date_ignores_null_close():
    """CloseがNULLのデータは最新日として扱わない"""
    conn = sqlite3.connect(":memory:")
    create_prices_table(conn)

    conn.execute("""
        INSERT INTO prices (
            Date, Code, Open, High, Low, Close, Volume,
            AdjOpen, AdjHigh, AdjLow, AdjClose, AdjVolume
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "2026-08-21",
        "7203",
        1000,
        1100,
        990,
        1050,
        100000,
        1000,
        1100,
        990,
        1050,
        100000,
    ))

    conn.execute("""
        INSERT INTO prices (
            Date, Code, Open, High, Low, Close, Volume,
            AdjOpen, AdjHigh, AdjLow, AdjClose, AdjVolume
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "2026-08-24",
        "7203",
        1050,
        1150,
        1040,
        None,
        120000,
        1050,
        1150,
        1040,
        None,
        120000,
    ))

    conn.commit()

    result = get_latest_price_date(conn, "7203")

    assert result == date(2026, 8, 21)

    conn.close()

def test_get_latest_price_date_returns_none_when_no_data():
    """株価データが存在しない場合はNoneを返す"""
    conn = sqlite3.connect(":memory:")
    create_prices_table(conn)

    result = get_latest_price_date(conn, "7203")

    assert result is None

    conn.close()

def insert_price(conn, date_str, code="7203", close=1000):
    conn.execute("""
        INSERT INTO prices (
            Date, Code, Open, High, Low, Close, Volume,
            AdjOpen, AdjHigh, AdjLow, AdjClose, AdjVolume
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        date_str,
        code,
        1000,
        1100,
        900,
        close,
        100000,
        1000,
        1100,
        900,
        close,
        100000,
    ))

    conn.commit()

def test_ensure_recent_prices_does_not_update_when_latest():
    """DBが最新なら更新しない"""
    conn = sqlite3.connect(":memory:")
    create_prices_table(conn)

    insert_price(conn, "2026-08-21")

    with patch(
        "kabutam.stock.saveprice.expected_latest_close_date",
        return_value=date(2026, 8, 21),
    ):

        with patch(
            "kabutam.stock.saveprice.update_prices"
        ) as mock_update:

            result = ensure_recent_prices(
                conn,
                "7203",
                days=3,
            )

    mock_update.assert_not_called()

    assert result[0][0] == "2026-08-21"

    conn.close()


def test_ensure_recent_prices_updates_when_old():
    """DBが古ければfetch_prices経由で株価を更新する"""
    conn = sqlite3.connect(":memory:")
    create_prices_table(conn)

    insert_price(conn, "2026-08-21")

    new_record = {
        "Date": "2026-08-24",
        "Code": "7203",
        "Open": 1100,
        "High": 1200,
        "Low": 1080,
        "Close": 1150,
        "Volume": 200000,
        "AdjOpen": 1100,
        "AdjHigh": 1200,
        "AdjLow": 1080,
        "AdjClose": 1150,
        "AdjVolume": 200000,
    }

    with patch(
        "kabutam.stock.saveprice.expected_latest_close_date",
        return_value=date(2026, 8, 24),
    ):

        with patch(
            "kabutam.stock.saveprice.fetch_prices",
            return_value=[new_record],
        ) as mock_fetch:

            result = ensure_recent_prices(
                conn,
                "7203",
                days=3,
            )

    mock_fetch.assert_called_once()

    assert result[0][0] == "2026-08-24"
    assert result[0][4] == 1150

    conn.close()

def test_ensure_recent_prices_updates_when_no_data():
    """DBに株価がなければ更新する"""
    conn = sqlite3.connect(":memory:")
    create_prices_table(conn)

    new_record = {
        "Date": "2026-08-24",
        "Code": "7203",
        "Open": 1100,
        "High": 1200,
        "Low": 1080,
        "Close": 1150,
        "Volume": 200000,
        "AdjOpen": 1100,
        "AdjHigh": 1200,
        "AdjLow": 1080,
        "AdjClose": 1150,
        "AdjVolume": 200000,
    }

    with patch(
        "kabutam.stock.saveprice.expected_latest_close_date",
        return_value=date(2026, 8, 24),
    ):

        with patch(
            "kabutam.stock.saveprice.fetch_prices",
            return_value=[new_record],
        ) as mock_fetch:

            result = ensure_recent_prices(
                conn,
                "7203",
                days=3,
            )

    mock_fetch.assert_called_once()

    assert result[0][0] == "2026-08-24"
    assert result[0][4] == 1150

    conn.close()

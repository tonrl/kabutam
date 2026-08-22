import sqlite3

from kabutam.db.portfolio import (
        add_buy,
        add_sell,
        get_transactions,
        get_holdings,
)


def test_add_buy():
    conn = sqlite3.connect(":memory:")
    try:
        add_buy(
                conn,
                code="7203",
                account_type="tokutei",
                shares=100,
                price=2500,
                date="2026-08-20",
        )

        rows = get_transactions(conn)
        assert len(rows) == 1
        assert rows[0][1] == "7203"
        assert rows[0][2] == "tokutei"
        assert rows[0][3] == "BUY"
        assert rows[0][4] == 100
        assert rows[0][5] == 2500
        assert rows[0][6] == "2026-08-20"
    finally:
        conn.close()


def test_add_sell():
    conn = sqlite3.connect(":memory:")
    try:
        add_buy(
            conn,
            code="7203",
            account_type="tokutei",
            shares=100,
            price=2500,
            date="2026-08-20",
        )

        add_sell(
            conn,
            code="7203",
            account_type="tokutei",
            shares=30,
            price=3000,
            date="2026-08-21",
        )

        rows = get_transactions(conn)

        assert len(rows) == 2
        assert rows[1][3] == "SELL"
        assert rows[1][4] == 30
        assert rows[1][5] == 3000
    finally:
        conn.close()


def test_get_holdings_after_buy():
    conn = sqlite3.connect(":memory:")
    try:
        add_buy(
            conn,
            code="7203",
            account_type="tokutei",
            shares=100,
            price=2500,
            date="2026-08-20",
        )

        holdings = get_holdings(conn)
        assert holdings["7203"]["tokutei"]["shares"] == 100
        assert holdings["7203"]["tokutei"]["cost"] == 250000
        assert holdings["7203"]["tokutei"]["average_price"] == 2500
    finally:
        conn.close()


def test_get_holdings_after_sell():
    conn = sqlite3.connect(":memory:")
    try:
        add_buy(
            conn,
            code="7203",
            account_type="tokutei",
            shares=100,
            price=2500,
            date="2026-08-20",
        )

        add_sell(
            conn,
            code="7203",
            account_type="tokutei",
            shares=40,
            price=3000,
            date="2026-08-21",
        )

        holdings = get_holdings(conn)
        assert holdings["7203"]["tokutei"]["shares"] == 60
        assert holdings["7203"]["tokutei"]["average_price"] == 2500
    finally:
        conn.close()


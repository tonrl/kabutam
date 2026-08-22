import sqlite3
from kabutam.db.portfolio import add_buy, get_holdings

def test_get_holdings_average_price():
    with sqlite3.connect(":memory:") as conn:
        add_buy(
            conn,
            code="7203",
            account_type="tokutei",
            shares=100,
            price=2000,
            date="2026-08-20",
        )

        add_buy(
            conn,
            code="7203",
            account_type="tokutei",
            shares=100,
            price=3000,
            date="2026-08-21",
        )

        holdings = get_holdings(conn)

        holding = holdings["7203"]["tokutei"]

        assert holding["shares"] == 200
        assert holding["cost"] == 500000
        assert holding["average_price"] == 2500

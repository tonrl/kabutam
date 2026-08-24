# db/portfolio.py

def create_table_portfolio(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Code TEXT NOT NULL,
            account_type TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            shares INTEGER NOT NULL,
            price REAL NOT NULL,
            transaction_date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
def get_holding_shares(conn, code, account_type):
    create_table_portfolio(conn)

    rows = conn.execute("""
        SELECT
            transaction_type,
            shares
        FROM portfolio_transactions
        WHERE Code = ?
          AND account_type = ?
        ORDER BY transaction_date, id
    """, (code, account_type)).fetchall()

    holding_shares = 0

    for transaction_type, shares in rows:
        if transaction_type == "BUY":
            holding_shares += shares

        elif transaction_type == "SELL":
            holding_shares -= shares

    return holding_shares

def add_buy(conn, code, account_type, shares, price, date):
    create_table_portfolio(conn)

    conn.execute("""
        INSERT INTO portfolio_transactions (
            Code,
            account_type,
            transaction_type,
            shares,
            price,
            transaction_date
        )
        VALUES (?, ?, 'BUY', ?, ?, ?)
    """, (
        code,
        account_type,
        shares,
        price,
        date
    ))

    conn.commit()


def add_sell(conn, code, account_type, shares, price, date):
    create_table_portfolio(conn)

    holding_shares = get_holding_shares(
        conn,
        code,
        account_type
    )
    if shares > holding_shares:
        raise ValueError(
            f"{code} の保有株数は {holding_shares}株です。"
            f"{shares}株は売却できません。"
        )

    conn.execute("""
        INSERT INTO portfolio_transactions (
            Code,
            account_type,
            transaction_type,
            shares,
            price,
            transaction_date
        )
        VALUES (?, ?, 'SELL', ?, ?, ?)
    """, (
        code,
        account_type,
        shares,
        price,
        date
    ))

    conn.commit()


def get_transactions(conn, code=None):
    create_table_portfolio(conn)

    if code is None:
        return conn.execute("""
            SELECT
                id,
                Code,
                account_type,
                transaction_type,
                shares,
                price,
                transaction_date
            FROM portfolio_transactions
            ORDER BY transaction_date, id
        """).fetchall()

    return conn.execute("""
        SELECT
            id,
            Code,
            account_type,
            transaction_type,
            shares,
            price,
            transaction_date
        FROM portfolio_transactions
        WHERE Code = ?
        ORDER BY transaction_date, id
    """, (code,)).fetchall()

def get_holdings(conn):
    create_table_portfolio(conn)

    rows = conn.execute("""
        SELECT
            Code,
            account_type,
            transaction_type,
            shares,
            price
        FROM portfolio_transactions
        ORDER BY transaction_date, id
    """).fetchall()

    holdings = {}

    for code, account_type, transaction_type, shares, price in rows:

        if code not in holdings:
            holdings[code] = {}
        # 口座を初期化
        if account_type not in holdings[code]:
            holdings[code][account_type] = {
                "shares": 0,
                "cost": 0.0
            }

        holding = holdings[code][account_type]

        if transaction_type == "BUY":
            holding["cost"] += shares * price
            holding["shares"] += shares

        elif transaction_type == "SELL":
            if holding["shares"] <= 0:
                continue

            if shares > holding["shares"]:
                raise ValueError(
                    f"{code} の保有株数 {holding['shares']}株に対して、"
                    f"{shares}株の売却記録があります。"
                )

            sell_shares = min(
                    shares,
                    holding["shares"]
            )
            average_price = (
                    holding["cost"] /
                    holding["shares"]
            )
            holding["cost"] -= (
                    average_price * sell_shares
            )

            holding["shares"] -= sell_shares

    # 0株になった銘柄を削除
    for code in list(holdings.keys()):
        for account_type in list(holdings[code].keys()):
            if holdings[code][account_type]["shares"] <= 0:
                del holdings[code][account_type]
        # 保有口座がなくなった銘柄を削除
        if not holdings[code]:
            del holdings[code]

    # 平均取得単価を追加
    for accounts in holdings.values():
        for data in accounts.values():
            data["average_price"] = (
                    data["cost"] / data["shares"]
            )

    return holdings

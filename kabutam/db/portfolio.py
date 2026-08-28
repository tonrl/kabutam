# db/portfolio.py
from kabutam.db.schema import create_table_portfolio


def get_holding_shares(conn, code, account_type):
    create_table_portfolio(conn)

    transactions = conn.execute(
        """
        SELECT
            transaction_date,
            id,
            transaction_type,
            shares
        FROM portfolio_transactions
        WHERE Code = ?
          AND account_type = ?
        ORDER BY transaction_date, id
    """,
        (code, account_type),
    ).fetchall()

    actions = conn.execute(
        """
        SELECT
            effective_date,
            id,
            action_type,
            ratio
        FROM corporate_actions
        WHERE Code = ?
        ORDER BY effective_date, id
    """,
        (code,),
    ).fetchall()

    events = []

    # BUY / SELL
    for date, event_id, transaction_type, shares in transactions:
        events.append((date, 1, event_id, transaction_type, shares))

    # SPLIT

    for date, event_id, action_type, ratio in actions:
        events.append((date, 0, event_id, action_type, ratio))

    # 日付 -> ID順
    events.sort(key=lambda x: (x[0], x[1], x[2]))

    holding_shares = 0

    for date, event_priority, event_id, event_type, value in events:
        if event_type == "BUY":
            holding_shares += value

        elif event_type == "SELL":
            holding_shares -= value

        elif event_type in ("SPLIT", "REVERSE_SPLIT"):
            new_shares = holding_shares * value
            if new_shares != int(new_shares):
                raise ValueError(f"{code} の株式分割・併合により端数株が発生します。")
            holding_shares = int(new_shares)

    return holding_shares


def add_buy(conn, code, account_type, shares, price, date):
    create_table_portfolio(conn)
    if not code or not isinstance(code, str):
        raise ValueError("銘柄コードが不正です。")

    if not account_type or not isinstance(account_type, str):
        raise ValueError("口座区分が不正です。")

    if not isinstance(shares, int) or shares <= 0:
        raise ValueError("購入株数は1以上の整数を指定してください。")

    if price is None or price <= 0:
        raise ValueError("購入価格は0より大きい値を指定してください。")

    if not date:
        raise ValueError("取引日が指定されていません。")

    conn.execute(
        """
        INSERT INTO portfolio_transactions (
            Code,
            account_type,
            transaction_type,
            shares,
            price,
            transaction_date
        )
        VALUES (?, ?, 'BUY', ?, ?, ?)
    """,
        (code, account_type, shares, price, date),
    )

    conn.commit()


def add_sell(conn, code, account_type, shares, price, date):
    create_table_portfolio(conn)
    if not code or not isinstance(code, str):
        raise ValueError("銘柄コードが不正です。")

    if not account_type or not isinstance(account_type, str):
        raise ValueError("口座区分が不正です。")

    if not isinstance(shares, int) or shares <= 0:
        raise ValueError("売却株数は1以上の整数を指定してください。")

    if price is None or price <= 0:
        raise ValueError("売却価格は0より大きい値を指定してください。")

    if not date:
        raise ValueError("取引日が指定されていません。")

    holding_shares = get_holding_shares(conn, code, account_type)

    if holding_shares < 0:
        raise ValueError(
            f"{code} の保有株数が不正です。現在の保有株数: {holding_shares}株"
        )

    if shares > holding_shares:
        raise ValueError(
            f"{code} の保有株数は {holding_shares}株です。{shares}株は売却できません。"
        )

    conn.execute(
        """
        INSERT INTO portfolio_transactions (
            Code,
            account_type,
            transaction_type,
            shares,
            price,
            transaction_date
        )
        VALUES (?, ?, 'SELL', ?, ?, ?)
    """,
        (code, account_type, shares, price, date),
    )

    conn.commit()


# ------------------------------------------------------------
# 株式分割併合
# ------------------------------------------------------------


def add_split(conn, code, ratio, date):
    create_table_portfolio(conn)

    if not code or not isinstance(code, str):
        raise ValueError("銘柄コードが不正です。")

    if ratio is None:
        raise ValueError("ratioが指定されていません。")

    if ratio <= 0:
        raise ValueError("ratioは0より大きい値を指定してください。")

    if ratio == 1:
        raise ValueError("ratioに1は指定できません。")

    if ratio > 1:
        action_type = "SPLIT"
    else:
        action_type = "REVERSE_SPLIT"

    # --------------------------------------------------------
    # 現在の保有株数に対して端数が発生するか確認
    # --------------------------------------------------------

    account_types = conn.execute(
        """
        SELECT DISTINCT account_type
        FROM portfolio_transactions
        WHERE Code = ?
    """,
        (code,),
    ).fetchall()

    for (account_type,) in account_types:
        shares = get_holding_shares(conn, code, account_type)
        if shares <= 0:
            continue
        new_shares = shares * ratio

        if new_shares != int(new_shares):
            raise ValueError(
                f"{code} の株式分割・併合では端数株が発生します。"
                f" {shares}株 × {ratio} = {new_shares}株"
            )

    conn.execute(
        """
        INSERT INTO corporate_actions (
            Code,
            action_type,
            ratio,
            effective_date
        )
        VALUES (?, ?, ?, ?)
    """,
        (code, action_type, ratio, date),
    )

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

    return conn.execute(
        """
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
    """,
        (code,),
    ).fetchall()


# ------------------------------------------------------------
# 現在の保有状況
# ------------------------------------------------------------


def get_holdings(conn):
    create_table_portfolio(conn)

    transactions = conn.execute("""
        SELECT
            transaction_date,
            id,
            Code,
            account_type,
            transaction_type,
            shares,
            price
        FROM portfolio_transactions
        ORDER BY transaction_date, id
    """).fetchall()

    actions = conn.execute("""
        SELECT
            effective_date,
            id,
            Code,
            action_type,
            ratio
        FROM corporate_actions
        ORDER BY effective_date, id
    """).fetchall()

    events = []

    # --------------------------------------------------------
    # BUY / SELL
    # --------------------------------------------------------

    for (
        date,
        event_id,
        code,
        account_type,
        transaction_type,
        shares,
        price,
    ) in transactions:
        events.append(
            {
                "date": date,
                "priority": 1,
                "id": event_id,
                "type": "TRANSACTION",
                "code": code,
                "account_type": account_type,
                "action": transaction_type,
                "shares": shares,
                "price": price,
            }
        )
    # --------------------------------------------------------
    # SPLIT / REVERSE_SPLIT
    # --------------------------------------------------------

    for date, event_id, code, action_type, ratio in actions:
        events.append(
            {
                "date": date,
                "priority": 0,
                "id": event_id,
                "type": "CORPORATE_ACTION",
                "code": code,
                "account_type": None,
                "action": action_type,
                "shares": None,
                "price": None,
                "ratio": ratio,
            }
        )

    # --------------------------------------------------------
    # 日付順
    # --------------------------------------------------------
    events.sort(key=lambda event: (event["date"], event["priority"], event["id"]))

    holdings = {}

    # 　イベント処理
    # for (date, event_id, event_group, code, account_type, event_type, value, price) in events:
    for event in events:
        code = event["code"]
        # ====================================================
        # 株式分割・併合
        # ====================================================
        if event["type"] == "CORPORATE_ACTION":
            ratio = event["ratio"]

            if ratio <= 0:
                raise ValueError(f"{code} の企業イベントに不正なratioがあります。")

            if code not in holdings:
                continue

            for holding in holdings[code].values():
                new_shares = holding["shares"] * ratio

                if new_shares != int(new_shares):
                    raise ValueError(
                        f"{code} の株式分割・併合で"
                        f"端数株が発生します。"
                        f" {holding['shares']}株 × {ratio}"
                        f" = {new_shares}株"
                    )

                holding["shares"] = int(new_shares)

            continue
        # ====================================================
        # BUY / SELL
        # ====================================================
        account_type = event["account_type"]
        transaction_type = event["action"]
        shares = event["shares"]
        price = event["price"]

        if code not in holdings:
            holdings[code] = {}
        # 口座を初期化
        if account_type not in holdings[code]:
            holdings[code][account_type] = {"shares": 0, "cost": 0.0}

        holding = holdings[code][account_type]

        # ----------------------------------------------------
        # BUY
        # ----------------------------------------------------

        if transaction_type == "BUY":
            holding["cost"] += shares * price
            holding["shares"] += shares
        # ----------------------------------------------------
        # SELL
        # ----------------------------------------------------

        elif transaction_type == "SELL":
            if holding["shares"] <= 0:
                raise ValueError(
                    f"{code} の {account_type} に保有株がない状態で売却記録があります。"
                )
            if shares <= 0:
                raise ValueError(f"{code} の売却株数が不正です。売却株数: {shares}")

            if shares > holding["shares"]:
                raise ValueError(
                    f"{code} の保有株数 {holding['shares']}株に対して、"
                    f"{shares}株の売却記録があります。"
                )
            if price is None or price <= 0:
                raise ValueError(f"{code} の売却価格が不正です。売却価格: {price}")

            average_price = holding["cost"] / holding["shares"]
            holding["cost"] -= average_price * shares

            holding["shares"] -= shares

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
            data["average_price"] = data["cost"] / data["shares"]

    return holdings

from kabutam.db.portfolio import get_holdings
from kabutam.stock.saveprice import ensure_recent_prices
from kabutam.display.terminal import fit_text


def show_portfolio(conn):

    holdings = get_holdings(conn)

    if not holdings:
        print("ポートフォリオは空です。")
        return

    total_value = 0
    total_cost = 0

    WIDTH = 95

    print("=" * WIDTH)
    print("ポートフォリオ")
    print("=" * WIDTH)

    print(
        f"{'Code':<8}"
        f"{fit_text('Company', 25)}"
        f"{fit_text('Account', 8)}"
        f"{'Shares':>10}"
        f"{'Avg Price':>14}"
        f"{'Price':>14}"
        f"{'Value':>16}"
    )

    print("-" * WIDTH)

    for code, accounts in holdings.items():

        # --------------------------------------------------
        # 会社名
        # --------------------------------------------------

        row = conn.execute("""
            SELECT CoName
            FROM equities_master
            WHERE Code = ?
        """, (code,)).fetchone()

        name = row[0] if row else "不明"

        company = fit_text(name, 25)

        # --------------------------------------------------
        # 最新株価
        # 銘柄ごとに1回だけ取得
        # --------------------------------------------------

        prices = ensure_recent_prices(
            conn,
            code,
            1
        )

        if prices:
            latest_price = prices[0][4]
        else:
            latest_price = None

        # --------------------------------------------------
        # 口座ごとに表示
        # --------------------------------------------------

        for account_type, holding in accounts.items():

            shares = holding["shares"]
            average_price = holding["average_price"]

            cost = shares * average_price
            total_cost += cost

            if latest_price is not None:
                value = shares * latest_price
                total_value += value
            else:
                value = None

            if value is not None:

                print(
                    f"{code:<8}"
                    f"{company}"
                    f"{account_type}"
                    f"{shares:>10,}"
                    f"{average_price:>14,.2f}"
                    f"{latest_price:>14,.2f}"
                    f"{value:>16,.0f}"
                )

            else:

                print(
                    f"{code:<8}"
                    f"{company}"
                    f"{account_type}"
                    f"{shares:>10,}"
                    f"{average_price:>14,.2f}"
                    f"{'-':>14}"
                    f"{'-':>16}"
                )

    print("-" * WIDTH)

    # --------------------------------------------------
    # 集計
    # --------------------------------------------------

    profit = total_value - total_cost

    print(f"取得総額       : {total_cost:,.0f} 円")
    print(f"保有資産額     : {total_value:,.0f} 円")
    print(f"評価損益       : {profit:+,.0f} 円")

    if total_cost > 0:
        print(
            f"評価損益率     : "
            f"{profit / total_cost * 100:+.2f}%"
        )

    print("=" * WIDTH)

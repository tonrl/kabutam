from kabutam.db.portfolio import get_holdings

from kabutam.db.schema import create_table_corp_data
from kabutam.edinet.get_corpdata import get_corpdata

from kabutam.stock.saveprice import ensure_recent_prices
from kabutam.display.terminal import fit_text


def show_portfolio(conn):

    holdings = get_holdings(conn)

    if not holdings:
        print("ポートフォリオは空です。")
        return

    total_value = 0
    total_cost = 0
    total_dividend_pre_tax = 0
    total_dividend_post_tax = 0

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
        # 配当情報(EDINETデータから取得)
        # --------------------------------------------------
        edinet_row = conn.execute("""
            SELECT EDINETCode
            FROM edinet_master
            WHERE Code = ?
        """, (code,)).fetchone()

        forecast_dividend = None
        if edinet_row and edinet_row[0]:
            edinetcode = edinet_row[0]
            create_table_corp_data(conn)
            corpdata = get_corpdata(conn, edinetcode)
            if corpdata and len(corpdata) > 13:
                # index 13: forecast_dividend_per_share (予想年間配当)
                forecast_dividend = corpdata[13]

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

            # 配当金・税金計算
            if forecast_dividend is not None:
                div_pre_tax = shares * forecast_dividend
                # NISA口座は非課税(0%)、その他は20.315%
                is_nisa = "NISA" in account_type.upper()
                tax_rate = 0.0 if is_nisa else 0.20315
                div_post_tax = div_pre_tax * (1 - tax_rate)
                total_dividend_pre_tax += div_pre_tax
                total_dividend_post_tax += div_post_tax

            if value is not None:

                print(
                    f"{code:<8}"
                    f"{company}"
                    f"{fit_text(account_type, 8)}"
                    f"{shares:>10,}"
                    f"{average_price:>14,.2f}"
                    f"{latest_price:>14,.2f}"
                    f"{value:>16,.0f}"
                )

            else:

                print(
                    f"{code:<8}"
                    f"{company}"
                    f"{fit_text(account_type, 8)}"
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
    print(f"年間配当金（税引前）: {total_dividend_pre_tax:,.0f} 円")
    print(f"年間配当金（税引後）: {total_dividend_post_tax:,.0f} 円")

    if total_cost > 0:
        yield_on_cost = (total_dividend_pre_tax / total_cost) * 100
        print(f"配当利回り（取得額ベース）: {yield_on_cost:.2f}%")

    if total_value > 0:
        yield_on_value = (total_dividend_pre_tax / total_value) * 100
        print(f"配当利回り（評価額ベース）: {yield_on_value:.2f}%")

    print("=" * WIDTH)

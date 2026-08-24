import sys
import threading
import time
import csv
from kabutam.db.portfolio import get_holdings
from kabutam.db.schema import create_table_corp_data
from kabutam.edinet.get_corpdata import get_corpdata
from kabutam.stock.saveprice import ensure_recent_prices
from kabutam.display.terminal import fit_text
from kabutam.display.colors import (colorise_profit)

def show_spinner(stop_event, current_ref, total):
    symbols = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    i = 0

    while not stop_event.is_set():

        current = current_ref[0]

        print(
            f"\r株価情報を更新しています... "
            f"{symbols[i % len(symbols)]} "
            f"{current} / {total}",
            end="",
            flush=True
        )

        i += 1
        time.sleep(0.1)

    # 行を消す
    print("\r" + " " * 60 + "\r", end="", flush=True)
def show_portfolio_csv(conn):

    holdings = get_holdings(conn)

    if not holdings:
        return

    writer = csv.writer(sys.stdout,
                        lineterminator="\n",
    )

    writer.writerow([
        "Code",
        "Company",
        "Account",
        "Shares",
        "AveragePrice",
        "Price",
        "Profit",
        "Value",
    ])

    # 最新株価を取得
    latest_prices = {}

    for code in holdings:
        prices = ensure_recent_prices(conn, code, 1)

        if prices:
            latest_prices[code] = prices[0][4]
        else:
            latest_prices[code] = None

    for code, accounts in holdings.items():

        row = conn.execute("""
            SELECT CoName
            FROM equities_master
            WHERE Code = ?
        """, (code,)).fetchone()

        name = row[0] if row else "不明"

        latest_price = latest_prices.get(code)

        for account_type, holding in accounts.items():

            shares = holding["shares"]
            average_price = holding["average_price"]

            if latest_price is not None:

                value = shares * latest_price
                profit = (
                    latest_price - average_price
                ) * shares

            else:

                value = None
                profit = None

            writer.writerow([
                code,
                name,
                account_type,
                shares,
                average_price,
                latest_price,
                profit,
                value,
            ])

def show_portfolio(conn, mode="normal"):

    holdings = get_holdings(conn)

    if not holdings:
        print("ポートフォリオは空です。")
        return

    total_value = 0
    total_cost = 0
    total_dividend_pre_tax = 0
    total_dividend_post_tax = 0
    # WIDTH = 95
    WIDTH_CODE = 8
    WIDTH_COMPANY = 25
    WIDTH_ACCOUNT = 8
    WIDTH_SHARES = 10
    WIDTH_AVG_PRICE = 14
    WIDTH_PRICE = 14
    WIDTH_PROFIT = 16
    WIDTH_VALUE = 16

    if (mode=="minimal"):
        WIDTH = (
            WIDTH_CODE
            + WIDTH_COMPANY
            + WIDTH_ACCOUNT
            + WIDTH_SHARES
            + WIDTH_AVG_PRICE
            + WIDTH_PRICE
        )
    else:
        WIDTH = (
            WIDTH_CODE
            + WIDTH_COMPANY
            + WIDTH_ACCOUNT
            + WIDTH_SHARES
            + WIDTH_AVG_PRICE
            + WIDTH_PRICE
            + WIDTH_PROFIT
            + WIDTH_VALUE
        )
    # --------------------------------------------------
    # 表示前に全銘柄の最新株価を取得
    # --------------------------------------------------
    latest_prices = {}

    codes = list(holdings.keys())
    total_codes = len(codes)

    current_ref = [0]
    stop_event = threading.Event()

    spinner = threading.Thread(
        target=show_spinner,
        args=(stop_event, current_ref, total_codes),
    )

    spinner.start()

    try:
        for code in holdings:
            prices = ensure_recent_prices(conn,code,1)
            if prices:
                latest_prices[code] = prices[0][4]
            else:
                latest_prices[code] = None
            current_ref[0] += 1
    finally:
        stop_event.set()
        spinner.join()

    #-----------------------------------------------------


    print("=" * WIDTH)
    print("ポートフォリオ")
    print("=" * WIDTH)
    if (mode=="minimal"):
        print(
            f"{'Code':<{WIDTH_CODE}}"
            f"{fit_text('Company', WIDTH_COMPANY)}"
            f"{fit_text('Account', WIDTH_ACCOUNT)}"
            f"{'Shares':>{WIDTH_SHARES}}"
            f"{'Avg Price':>{WIDTH_AVG_PRICE}}"
            f"{'Price':>{WIDTH_PRICE}}"
        )
    else:
        print(
            f"{'Code':<{WIDTH_CODE}}"
            f"{fit_text('Company', WIDTH_COMPANY)}"
            f"{fit_text('Account', WIDTH_ACCOUNT)}"
            f"{'Shares':>{WIDTH_SHARES}}"
            f"{'Avg Price':>{WIDTH_AVG_PRICE}}"
            f"{'Price':>{WIDTH_PRICE}}"
            f"{'P/L':>{WIDTH_PROFIT}}"
            f"{'Value':>{WIDTH_VALUE}}"
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

        latest_price = latest_prices.get(code)
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

                profit = (latest_price - average_price) * shares
                profit_text = f"{profit:+,.0f}"
                profit_text = f"{profit_text:>16}"
                profit_text = colorise_profit(profit, profit_text)

            else:
                value = None
                profit = None

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
                if (mode == "minimal"):
                    print(
                            f"{code:<{WIDTH_CODE}}"
                            f"{company}"
                            f"{fit_text(account_type, WIDTH_ACCOUNT)}"
                            f"{shares:>{WIDTH_SHARES},}"
                            f"{average_price:>{WIDTH_AVG_PRICE},.2f}"
                            f"{latest_price:>{WIDTH_PRICE},.2f}"
                    )
                else:
                    print(
                            f"{code:<{WIDTH_CODE}}"
                            f"{company}"
                            f"{fit_text(account_type, WIDTH_ACCOUNT)}"
                            f"{shares:>{WIDTH_SHARES},}"
                            f"{average_price:>{WIDTH_AVG_PRICE},.2f}"
                            f"{latest_price:>{WIDTH_PRICE},.2f}"
                            f"{profit_text:>{WIDTH_PROFIT}}"
                            f"{value:>{WIDTH_VALUE},.0f}"
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
                    f"{'-':>16}"
                )

    print("-" * WIDTH)

    # --------------------------------------------------
    # 集計
    # --------------------------------------------------

    profit = total_value - total_cost

    print(f"取得総額       : {total_cost:,.0f} 円")
    print(f"保有資産額     : {total_value:,.0f} 円")
    # print(f"評価損益       : {profit:+,.0f} 円")
    print(
            "評価損益       : "+ colorise_profit(
                profit,
                f"{profit:+,.0f} 円"
            )
    )

    if total_cost > 0:
        profit_rate = profit / total_cost * 100
        print(
                "評価損益率     : "
                + colorise_profit(
                    profit_rate,
                    f"{profit_rate:+.2f}%"
                )
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

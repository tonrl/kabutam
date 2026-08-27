import sys
import threading
import time
import csv
from kabutam.db.portfolio import get_holdings
from kabutam.db.schema import create_table_corp_data
from kabutam.edinet.get_corpdata import get_corpdata
from kabutam.stock.saveprice import ensure_recent_prices
from kabutam.edinet.get_irdoc_list import sync_recent_edinet_doc_list
from kabutam.tdnet.sync_tdnet import sync_recent_tdnet
from kabutam.display.terminal import fit_text
from kabutam.display.colors import (colorise_profit)

DOC_LIMIT=3
TDNET_DOC_LIMIT=6
# スタイルの定義
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
FG_BRIGHT_WHITE = "\033[97m"
FG_CYAN = "\033[36m"
FG_GRAY = "\033[90m"

def show_spinner(stop_event, current_ref, total, status_ref):
    # symbols = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    symbols = ["⠉⠉", "⠈⠙", "⠀⠹", "⠀⢸", "⠀⣰", "⢀⣠", "⣀⣀", "⣄⡀", "⣆⠀", "⡇⠀", "⠏⠀", "⠋⠁"]
    # symbols = ["⠁","⠂","⠄","⡀","⡈","⡐","⡠","⣀","⣁","⣂","⣄","⣌","⣔","⣤","⣥","⣦","⣮","⣶","⣷","⣿","⡿","⠿","⢟","⠟","⡛","⠛","⠫","⢋","⠋","⠍","⡉","⠉","⠑","⠡","⢁"]

    i = 0

    while not stop_event.is_set():

        current = current_ref[0] if current_ref else 0
        status = status_ref[0]
        if status:
            message = status
        else:
            message = " 処理中..."
        if total is not None:
            counter_str = f"({current} / {total}) "
        else:
            counter_str = ""

        print(
                f"\r\033[K "
                f"{symbols[i % len(symbols)]} "
                f"{counter_str}",
                f"{message} ",
                end="",
                flush=True
        )

        i += 1
        time.sleep(0.1)
    print("\r\033[K", end="", flush=True)
    # print("\r" + " " * 80 + "\r", end="", flush=True)

def get_portfolio_recent_edinet_documents(conn, codes, limit=8):
    """
    保有銘柄リストに紐づく直近の開示書類を日時降順で取得する
    """
    if not codes:
        return []

    placeholders = ",".join(["?"] * len(codes))

    query = f"""
        T1.document_id, T1.doc_description, T1.submit_datetime, T2.Code, T3.CoName
        FROM edinet_doc_list T1
        JOIN edinet_master T2 ON T1.EDINETCode = T2.EDINETCode
        LEFT JOIN equities_master T3 ON T2.Code = T3.Code
        WHERE T2.Code IN ({placeholders})
        ORDER BY T1.submit_datetime DESC
        LIMIT ?
    """

    params = list(codes) + [limit]

    cursor = conn.execute(f"SELECT {query}", params)
    return cursor.fetchall()

def get_portfolio_recent_tdnet_documents(conn, codes, limit=3):
    """
    保有銘柄リストに紐づく直近のTDnet開示情報を
    開示日時の降順で取得する。
    """

    if not codes:
        return []

    placeholders = ",".join(["?"] * len(codes))

    query = f"""
        SELECT
            T1.disclosure_id,
            T1.disclosure_date,
            T1.disclosure_time,
            T1.sec_code,
            T1.title,
            T1.pdf_url
        FROM tdnet_disclosure T1
        LEFT JOIN equities_master T3
            ON T1.sec_code = T3.Code
        WHERE T1.sec_code IN ({placeholders})
        ORDER BY
            T1.disclosure_date DESC,
            T1.disclosure_time DESC
        LIMIT ?
    """

    params = list(codes) + [limit]

    cursor = conn.execute(query, params)

    return cursor.fetchall()

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

    def on_price_event(message):
        status_ref[0] = message

    for code in holdings:
        prices = ensure_recent_prices(conn, code, 1, on_event=on_price_event)

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

# Show portfolio in terminal
def show_portfolio(conn, mode="normal", sort_by="shares"):

    holdings = get_holdings(conn)

    if not holdings:
        print("ポートフォリオは空です。")
        return

    total_value = 0
    total_previous_value = 0
    total_cost = 0
    total_dividend_pre_tax = 0
    total_dividend_post_tax = 0

    # カラムの幅の定義
    # WIDTH = 95
    WIDTH_CODE = 8
    WIDTH_COMPANY = 25
    WIDTH_ACCOUNT = 8
    WIDTH_SHARES = 10
    WIDTH_AVG_PRICE = 14
    WIDTH_DAILY_PROFIT = 16
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
            + WIDTH_DAILY_PROFIT
            + WIDTH_PRICE
        )
    else:
        WIDTH = (
            WIDTH_CODE
            + WIDTH_COMPANY
            + WIDTH_ACCOUNT
            + WIDTH_SHARES
            + WIDTH_AVG_PRICE
            + WIDTH_DAILY_PROFIT
            + WIDTH_PRICE
            + WIDTH_PROFIT
            + WIDTH_VALUE
        )
    # 開示情報取得
    status_ref = [" 開示書類情報を同期しています"]
    stop_event = threading.Event()
    spinner = threading.Thread(target=show_spinner, args=(stop_event, None, None, status_ref))
    spinner.start()

    try:
        sync_recent_edinet_doc_list(conn, message_ref=status_ref)
        sync_recent_tdnet(conn, message_ref=status_ref)
    finally:
        stop_event.set()
        spinner.join()

    # --------------------------------------------------
    # 表示前に全銘柄の最新株価を取得
    # --------------------------------------------------
    latest_prices = {}
    previous_prices = {}

    codes = list(holdings.keys())
    total_codes = len(codes)

    current_ref = [0]
    status_ref = [None]
    def on_price_event(message):
        status_ref[0] = message

    stop_event = threading.Event()

    # print(f"保有銘柄 {total_codes}銘柄の株価を確認しています...")
    spinner = threading.Thread(
        target=show_spinner,
        args=(stop_event, current_ref, total_codes, status_ref,),
    )

    spinner.start()

    try:
        for code in holdings:
            # 前のイベント表示をクリア
            status_ref[0] = " 株価情報を更新しています"
            # 株価の取得
            prices = ensure_recent_prices(conn, code, 2, on_event=on_price_event)

            if prices:
                # 最新営業日
                latest_prices[code] = prices[0][4]

                # 前営業日
                if len(prices) >=2:
                    previous_prices[code] = prices[1][4]
                else:
                    previous_prices[code] = None
            else:
                latest_prices[code] = None
                previous_prices[code] = None

            current_ref[0] += 1
    finally:
        stop_event.set()
        spinner.join()

    # --------------------------------------------------
    # 表示前に全銘柄の配当情報（EDINETデータ）を取得
    # --------------------------------------------------
    # print(f"保有銘柄 {total_codes}銘柄の企業情報を確認しています...")
    forecast_dividends = {}
    current_ref[0] = 0
    status_ref[0] = " 企業情報を更新しています"

    stop_event = threading.Event()
    spinner = threading.Thread(
        target=show_spinner,
        args=(stop_event, current_ref, total_codes, status_ref,),
    )

    spinner.start()
    try:
        create_table_corp_data(conn)
        for code in codes:
            edinet_row = conn.execute("""
                SELECT EDINETCode
                FROM edinet_master
                WHERE Code = ?
            """, (code,)).fetchone()

            forecast_dividend = None
            if edinet_row and edinet_row[0]:
                edinetcode = edinet_row[0]
                create_table_corp_data(conn)
                corpdata = get_corpdata(conn, edinetcode, message_ref=status_ref)
                if corpdata and len(corpdata) > 13:
                    # index 13: forecast_dividend_per_share (予想年間配当)
                    forecast_dividend = corpdata[13]

            forecast_dividends[code] = forecast_dividend
            current_ref[0] += 1

    finally:
        stop_event.set()
        spinner.join()

    # ソート処理
    if sort_by == "shares":
        codes = sorted(
            holdings.keys(),
            key=lambda code: (
                -sum(
                    holding["shares"]
                    for holding in holdings[code].values()
                ),
                str(code),
            )
        )
    else:
        codes = sorted(
            holdings.keys(),
            key=lambda code: str(code)
        )

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
            f"{'Daily P/L':>{WIDTH_DAILY_PROFIT}}"
            f"{'Price':>{WIDTH_PRICE}}"
        )
    else:
        print(
            f"{'Code':<{WIDTH_CODE}}"
            f"{fit_text('Company', WIDTH_COMPANY)}"
            f"{fit_text('Account', WIDTH_ACCOUNT)}"
            f"{'Shares':>{WIDTH_SHARES}}"
            f"{'Avg Price':>{WIDTH_AVG_PRICE}}"
            f"{'Daily P/L':>{WIDTH_DAILY_PROFIT}}"
            f"{'Price':>{WIDTH_PRICE}}"
            f"{'P/L':>{WIDTH_PROFIT}}"
            f"{'Value':>{WIDTH_VALUE}}"
        )

    print("-" * WIDTH)

    # for code, accounts in holdings.items():
    for code in codes:
        accounts = holdings[code]

        # --------------------------------------------------
        # 会社名
        # --------------------------------------------------

        row = conn.execute("""
            SELECT CoName
            FROM equities_master
            WHERE Code = ?
        """, (code,)).fetchone()

        name = row[0] if row else "不明"

        company_raw = fit_text(name, 25)
        company = f"{BOLD}{FG_BRIGHT_WHITE}{company_raw}{RESET}"

        # --------------------------------------------------

        latest_price = latest_prices.get(code)
        previous_price = previous_prices.get(code)
        forecast_dividend = forecast_dividends.get(code)

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

                # 前営業日の保有株評価額
                if previous_price is not None:
                    previous_value = shares * previous_price
                    total_previous_value += previous_value

                profit = (latest_price - average_price) * shares
                if previous_price is not None:
                    daily_profit = (latest_price - previous_price) * shares
                else:
                    daily_profit = None

                profit_text = f"{profit:+,.0f}"
                profit_text = f"{profit_text:>16}"
                profit_text = colorise_profit(profit, profit_text)

                if daily_profit is not None:
                    daily_profit_text = f"{daily_profit:+,.0f}"
                    daily_profit_text = f"{daily_profit_text:>{WIDTH_DAILY_PROFIT}}"
                    daily_profit_text = colorise_profit(
                            daily_profit,
                            daily_profit_text
                    )
                else:
                    daily_profit_text = f"{'-':>{WIDTH_DAILY_PROFIT}}"

            else:
                value = None
                profit = None
                daily_profit_text = f"{'-':>{WIDTH_DAILY_PROFIT}}"

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
                            f"{daily_profit_text:>{WIDTH_DAILY_PROFIT}}"
                            f"{latest_price:>{WIDTH_PRICE},.2f}"
                    )
                else:
                    print(
                            f"{code:<{WIDTH_CODE}}"
                            f"{company}"
                            f"{fit_text(account_type, WIDTH_ACCOUNT)}"
                            f"{shares:>{WIDTH_SHARES},}"
                            f"{average_price:>{WIDTH_AVG_PRICE},.2f}"
                            f"{daily_profit_text:>{WIDTH_DAILY_PROFIT}}"
                            f"{latest_price:>{WIDTH_PRICE},.2f}"
                            f"{profit_text:>{WIDTH_PROFIT}}"
                            f"{value:>{WIDTH_VALUE},.0f}"
                    )

            else:

                print(
                    f"{code:<{WIDTH_CODE}}"
                    f"{company}"
                    f"{fit_text(account_type, WIDTH_ACCOUNT)}"
                    f"{shares:>{WIDTH_SHARES},}"
                    f"{average_price:>{WIDTH_AVG_PRICE},.2f}"
                    f"{daily_profit_text:>{WIDTH_DAILY_PROFIT}}"
                    f"{'-':>{WIDTH_PRICE}}"
                    f"{'-':>{WIDTH_PROFIT}}"
                    f"{'-':>{WIDTH_VALUE}}"
                )

    print("-" * WIDTH)

    # --------------------------------------------------
    # 集計
    # --------------------------------------------------

    profit = total_value - total_cost
    daily_profit = total_value - total_previous_value

    print(f"取得総額       : {total_cost:,.0f} 円")
    print(f"保有資産額     : {total_value:,.0f} 円")
    # print(f"評価損益       : {profit:+,.0f} 円")
    print(
        "前営業日比     : "
        + colorise_profit(
            daily_profit,
            f"{daily_profit:+,.0f} 円"
        )
    )

    if total_previous_value > 0:
        daily_profit_rate = (
            daily_profit / total_previous_value
        ) * 100

        print(
            "前営業日比率   : "
            + colorise_profit(
                daily_profit_rate,
                f"{daily_profit_rate:+.2f}%"
            )
        )

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

    # ── 既存の配当金などの表示が終わったあとに追加 ──

    print("=" * WIDTH)
    print(f"   保有銘柄の直近のEDINET開示書類 (上位{DOC_LIMIT}件)")
    print("-" * WIDTH)

    # 保有銘柄全体のコードリストを使って直近10件を取得
    recent_portfolio_edinet_docs = get_portfolio_recent_edinet_documents(conn, codes, limit=DOC_LIMIT)

    if not recent_portfolio_edinet_docs:
        print("  直近の開示書類はありません。")
    else:
        for idx, (doc_id, description, submit_dt, stock_code, company_name) in enumerate(recent_portfolio_edinet_docs, 1):
            url = f"https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?{doc_id}"
            styled_company = f"{BOLD}{FG_BRIGHT_WHITE}{company_name}{RESET}"
            styled_url = f"{FG_CYAN}{url}{RESET}"

            print(f"[{idx:2d}] {stock_code} {styled_company} | {submit_dt}")
            print(f"      {description}")
            print(f"     {styled_url}")


    recent_portfolio_tdnet_docs = get_portfolio_recent_tdnet_documents(conn, codes, limit=TDNET_DOC_LIMIT)
    print("-" * WIDTH)
    print(f"   保有銘柄の直近のTDNET開示書類 (上位{TDNET_DOC_LIMIT}件)")
    print("-" * WIDTH)

    if not recent_portfolio_tdnet_docs:
        print("  直近の開示書類はありません。")
    else:
        for idx, (disclosure_id, disclosure_date, disclosure_time, sec_code, title, pdf_url) in enumerate(recent_portfolio_tdnet_docs, 1):
            row = conn.execute("""
                SELECT CoName
                FROM equities_master
                WHERE Code = ?
            """, (sec_code,)).fetchone()
            company_name = row[0] if row else "不明"

            styled_company = f"{BOLD}{FG_BRIGHT_WHITE}{company_name}{RESET}"
            url = pdf_url
            hyperlink = (
                f"\033]8;;{url}\033\\"
                f"{url}"
                f"\033]8;;\033\\"
            )

            styled_url = f"{FG_CYAN}{hyperlink}{RESET}"

            print(f"[{idx:2d}] {sec_code} {styled_company} | {disclosure_date} {disclosure_time}")
            print(f"      {title}")
            print(f"   {styled_url}")
    print("=" * WIDTH)

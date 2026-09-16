import csv
import sys
import threading
from datetime import date, datetime, timedelta, timezone

from dateutil.relativedelta import relativedelta

from kabutam.ai.portfolio import (
    analyze_portfolio,
    build_portfolio_analysis_input,
)
from kabutam.analysis.portfolio import (
    calculate_portfolio_row,
    calculate_portfolio_summary,
    calculate_sector_allocation,
)
from kabutam.animations.spinners import show_spinner
from kabutam.db.portfolio import get_holdings
from kabutam.db.schema import create_table_corp_data
from kabutam.display.colors import colorise_profit
from kabutam.display.terminal import fit_text
from kabutam.edinet.get_corpdata import get_corpdata
from kabutam.edinet.get_irdoc_list import sync_recent_edinet_doc_list
from kabutam.stock.saveprice import ensure_recent_prices, ensure_recent_prices_bulk
from kabutam.tdnet.sync_tdnet import sync_recent_tdnet

JST = timezone(timedelta(hours=9))

DISPLAY_DAYS = 100
MAX_SECTORS = 6
# スタイルの定義
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
FG_BRIGHT_WHITE = "\033[97m"
FG_CYAN = "\033[36m"
FG_GRAY = "\033[90m"


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
            AND date(T1.submit_datetime) >= datetime('now', '-30 days')
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
            AND date(T1.disclosure_date) >= date('now', '-30 days')
        ORDER BY
            T1.disclosure_date DESC,
            T1.disclosure_time DESC
        LIMIT ?
    """

    params = list(codes) + [limit]

    cursor = conn.execute(query, params)

    return cursor.fetchall()


def print_portfolio_summary(summary):
    total_cost = summary["total_cost"]
    total_value = summary["total_value"]
    unpriced_count = summary["unpriced_count"]
    daily_profit = summary["daily_profit"]
    daily_profit_rate = summary["daily_profit_rate"]
    monthly_profit = summary["monthly_profit"]
    monthly_profit_rate = summary["monthly_profit_rate"]
    three_month_profit = summary["three_month_profit"]
    three_month_profit_rate = summary["three_month_profit_rate"]
    unrealised_profit = summary["unrealised_profit"]
    unrealised_profit_rate = summary["unrealised_profit_rate"]
    total_dividend_pre_tax = summary["total_dividend_pre_tax"]
    total_dividend_post_tax = summary["total_dividend_post_tax"]
    yield_on_cost = summary["yield_on_cost"]
    yield_on_value = summary["yield_on_value"]

    # ------------------------------------------
    # 表示用文字列作成
    # ------------------------------------------

    daily_pl_text = colorise_profit(
        daily_profit,
        f"{daily_profit:+,.0f} 円",
    )

    daily_pl_rate_text = (
        colorise_profit(
            daily_profit_rate,
            f"{daily_profit_rate:+.2f}%",
        )
        if daily_profit_rate is not None
        else "-"
    )
    monthly_pl_text = (
        colorise_profit(
            monthly_profit,
            f"{monthly_profit:+,.0f} 円",
        )
        if monthly_profit is not None
        else "-"
    )

    monthly_pl_rate_text = (
        colorise_profit(
            monthly_profit_rate,
            f"{monthly_profit_rate:+.2f}%",
        )
        if monthly_profit_rate is not None
        else "-"
    )

    three_month_pl_text = (
        colorise_profit(
            three_month_profit,
            f"{three_month_profit:+,.0f} 円",
        )
        if three_month_profit is not None
        else "-"
    )

    three_month_pl_rate_text = (
        colorise_profit(
            three_month_profit_rate,
            f"{three_month_profit_rate:+.2f}%",
        )
        if three_month_profit_rate is not None
        else "-"
    )

    unrealised_pl_text = colorise_profit(
        unrealised_profit,
        f"{unrealised_profit:+,.0f} 円",
    )

    unrealised_pl_rate_text = (
        colorise_profit(
            unrealised_profit_rate,
            f"{unrealised_profit_rate:+.2f}%",
        )
        if unrealised_profit_rate is not None
        else "-"
    )

    yield_on_cost_text = f"{yield_on_cost:.2f}%" if yield_on_cost is not None else "-"

    yield_on_value_text = (
        f"{yield_on_value:.2f}%" if yield_on_value is not None else "-"
    )

    # ------------------------------------------
    # 表示
    # ------------------------------------------

    print(f"取得総額          : {total_cost:,.0f} 円")
    print(f"保有資産額        : {total_value:,.0f} 円")
    if unpriced_count:
        print(f"{FG_GRAY}※ 株価未取得: {unpriced_count} 件 (保有資産から除外){RESET}")
    print(f"前営業日比        : {daily_pl_text} ({daily_pl_rate_text})")
    print(f"前月比            : {monthly_pl_text} ({monthly_pl_rate_text})")
    print(f"3か月前比         : {three_month_pl_text} ({three_month_pl_rate_text})")

    print(f"評価損益          : {unrealised_pl_text} ({unrealised_pl_rate_text})")

    print(
        f"年間配当（税引前）: {total_dividend_pre_tax:,.0f} 円 "
        f"[{yield_on_cost_text} / 取得額"
        f"・{yield_on_value_text} / 評価額]"
    )
    print(f"年間配当（税引後）: {total_dividend_post_tax:,.0f} 円")


def print_sector_allocation(
    holdings, latest_prices, previous_prices, sector_names, width=60
):
    allocation = calculate_sector_allocation(
        holdings,
        latest_prices,
        previous_prices,
        sector_names,
    )

    if not allocation:
        return

    sector_count = len(allocation)
    stock_count = len(holdings)

    if len(allocation) > MAX_SECTORS:
        visible = allocation[:MAX_SECTORS]
        others = allocation[MAX_SECTORS:]

        other_value = sum(item[1] for item in others)
        total_value = sum(item[1] for item in allocation)

        other_profit = sum(item[3] for item in others)
        other_daily_profit = sum(item[4] for item in others)

        other_has_daily_profit = any(item[5] for item in others)

        other_weight = other_value / total_value * 100 if total_value > 0 else 0
        allocation = visible + [
            (
                "その他",
                other_value,
                other_weight,
                other_profit,
                other_daily_profit,
                other_has_daily_profit,
            )
        ]

    SEC_WIDTH = 10
    VALUE_WIDTH = 14
    DAILY_WIDTH = 14
    PROFIT_WIDTH = 14
    SECTOR_WIDTH = 15
    BAR_WIDTH = 32

    print(f"{'セクター構成':<{SECTOR_WIDTH}}[{sector_count}業種 / {stock_count}銘柄]")
    print("-" * width)
    print(
        f"{fit_text('業種', SECTOR_WIDTH)} "
        f"{'構成':<{BAR_WIDTH}}"
        f"{'比率':>{SEC_WIDTH - 3}}"
        f"{'評価額':>{VALUE_WIDTH}}"
        f"{'Daily P/L':>{DAILY_WIDTH}}"
        f"{'P/L':>{PROFIT_WIDTH}}"
    )
    print("-" * width)
    for sector, value, weight, profit, daily_profit, has_daily_profit in allocation:
        bar_length = round(weight / 100 * BAR_WIDTH)

        bar = "█" * bar_length

        profit_raw = f"{profit:+,.0f}"
        profit_padded = f"{profit_raw:>{PROFIT_WIDTH}}"
        profit_text = colorise_profit(profit, profit_padded)

        if has_daily_profit:
            daily_raw = f"{daily_profit:+,.0f}"
            daily_padded = f"{daily_raw:>{DAILY_WIDTH}}"
            daily_profit_text = colorise_profit(
                daily_profit,
                daily_padded,
            )

        else:
            daily_profit_text = f"{'-':>{DAILY_WIDTH}}"

        value_text = f"{value:>{VALUE_WIDTH},.0f}"

        print(
            f"{fit_text(sector, SECTOR_WIDTH)} "
            f"{bar:<{BAR_WIDTH}}"
            f"{weight:>{SEC_WIDTH}.1f}%"
            f"{value_text} 円"
            f"{daily_profit_text} "
            f"{profit_text}"
        )
    print("-" * width)


def show_portfolio_csv(conn):

    holdings = get_holdings(conn)

    if not holdings:
        return

    writer = csv.writer(
        sys.stdout,
        lineterminator="\n",
    )

    writer.writerow(
        [
            "Code",
            "Company",
            "Account",
            "Shares",
            "AveragePrice",
            "Price",
            "Profit",
            "Value",
        ]
    )

    # 最新株価を取得
    latest_prices = {}

    for code in holdings:
        prices = ensure_recent_prices(conn, code, 1, on_event=None)

        if prices:
            latest_prices[code] = prices[0][4]
        else:
            latest_prices[code] = None

    for code, accounts in holdings.items():
        row = conn.execute(
            """
            SELECT CoName
            FROM equities_master
            WHERE Code = ?
        """,
            (code,),
        ).fetchone()

        name = row[0] if row else "不明"

        latest_price = latest_prices.get(code)

        for account_type, holding in accounts.items():
            shares = holding["shares"]
            average_price = holding["average_price"]

            if latest_price is not None:
                value = shares * latest_price
                profit = (latest_price - average_price) * shares

            else:
                value = None
                profit = None

            writer.writerow(
                [
                    code,
                    name,
                    account_type,
                    shares,
                    average_price,
                    latest_price,
                    profit,
                    value,
                ]
            )


# Show portfolio in terminal
def show_portfolio(conn, mode="normal", sort_by="shares"):

    holdings = get_holdings(conn)

    if not holdings:
        print("ポートフォリオは空です。")
        return

    total_value = 0
    total_cost = 0
    total_priced_cost = 0
    total_previous_value = 0
    total_daily_profit = 0
    total_month_previous_value = 0
    total_three_month_previous_value = 0
    unpriced_count = 0
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

    if mode == "minimal":
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
    spinner = threading.Thread(
        target=show_spinner, args=(stop_event, None, None, status_ref)
    )
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
    month_previous_prices = {}
    three_month_previous_prices = {}

    today = datetime.now(JST).date()
    first_day_of_month = today.replace(day=1)
    month_end = first_day_of_month - timedelta(days=1)
    three_month_target = today - relativedelta(months=3)

    codes = list(holdings.keys())
    total_codes = len(codes)

    current_ref = [0]
    status_ref = [None]
    stop_event = threading.Event()

    def on_price_event(message):
        status_ref[0] = message

    # print(f"保有銘柄 {total_codes}銘柄の株価を確認しています...")
    spinner = threading.Thread(
        target=show_spinner,
        args=(
            stop_event,
            current_ref,
            total_codes,
            status_ref,
        ),
    )

    spinner.start()
    try:
        price_data = ensure_recent_prices_bulk(
            conn,
            codes,
            days=DISPLAY_DAYS,
            on_event=on_price_event,
        )
    finally:
        stop_event.set()
        spinner.join()

    for code in codes:
        prices = price_data.get(str(code), [])
        latest_prices[code] = None
        previous_prices[code] = None
        month_previous_prices[code] = None
        three_month_previous_prices[code] = None

        if not prices:
            continue

        # 最新日
        latest_prices[code] = prices[0][4]

        # 前営業日
        if len(prices) >= 2:
            previous_prices[code] = prices[1][4]

        # 前月末・3か月前の株価
        for price_row in prices:
            price_date = date.fromisoformat(price_row[0])
            close = price_row[4]

            # 前月末以前で最も新しい営業日
            if month_previous_prices[code] is None and price_date <= month_end:
                month_previous_prices[code] = close

            # 3か月前以前で最も新しい営業日
            if (
                three_month_previous_prices[code] is None
                and price_date <= three_month_target
            ):
                three_month_previous_prices[code] = close

    # --------------------------------------------------
    # 表示前に全銘柄の配当情報（EDINETデータ）を取得
    # --------------------------------------------------
    # print(f"保有銘柄 {total_codes}銘柄の企業情報を確認しています...")
    forecast_dividends = {}
    current_ref[0] = 0
    status_ref[0] = " 企業情報を更新しています"
    create_table_corp_data(conn)

    stop_event = threading.Event()
    spinner = threading.Thread(
        target=show_spinner,
        args=(
            stop_event,
            current_ref,
            total_codes,
            status_ref,
        ),
    )

    spinner.start()
    try:
        for code in codes:
            edinet_row = conn.execute(
                """
                SELECT EDINETCode
                FROM edinet_master
                WHERE Code = ?
            """,
                (code,),
            ).fetchone()

            forecast_dividend = None
            if edinet_row and edinet_row[0]:
                edinetcode = edinet_row[0]
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
                -sum(holding["shares"] for holding in holdings[code].values()),
                str(code),
            ),
        )
    else:
        codes = sorted(holdings.keys(), key=lambda code: str(code))
    # --------------------------
    # Get Company names
    # --------------------------
    placeholders = ",".join("?" for _ in codes)
    rows = conn.execute(
        f"""
            SELECT Code, CoName, S33Nm
            FROM equities_master
            WHERE Code IN ({placeholders})
            """,
        codes,
    ).fetchall()
    company_names = {code: company_name for code, company_name, _ in rows}
    sector_names = {
        code: sector_name if sector_name else "業種不明"
        for code, _, sector_name in rows
    }

    # -----------------------------------------------------

    if mode == "normal" or mode == "minimal":
        print("=" * WIDTH)
        print("ポートフォリオ")
        print("=" * WIDTH)
        if mode == "minimal":
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

        for code in codes:
            # info
            accounts = holdings[code]
            name = company_names.get(code, "不明")
            company_raw = fit_text(name, 25)
            company = f"{BOLD}{FG_BRIGHT_WHITE}{company_raw}{RESET}"

            # --------------------------------------------------

            latest_price = latest_prices.get(code)
            previous_price = previous_prices.get(code)
            month_previous_price = month_previous_prices.get(code)
            three_month_previous_price = three_month_previous_prices.get(code)
            forecast_dividend = forecast_dividends.get(code)

            # --------------------------------------------------
            # 口座ごとに表示
            # --------------------------------------------------
            for account_type, holding in accounts.items():
                row = calculate_portfolio_row(
                    code=code,
                    account_type=account_type,
                    holding=holding,
                    latest_price=latest_price,
                    previous_price=previous_price,
                    month_previous_price=month_previous_price,
                    three_month_previous_price=three_month_previous_price,
                    forecast_dividend=forecast_dividend,
                )
                # PF全体の合計
                total_cost += row["cost"]

                if row["value"] is not None:
                    total_value += row["value"]
                    total_priced_cost += row["cost"]

                if row["daily_profit"] is not None:
                    total_daily_profit += row["daily_profit"]
                    total_previous_value += row["previous_value"]

                shares = row["shares"]

                if month_previous_price is not None:
                    total_month_previous_value += month_previous_price * shares

                if three_month_previous_price is not None:
                    total_three_month_previous_value += (
                        three_month_previous_price * shares
                    )

                total_dividend_pre_tax += row["dividend_pre_tax"]
                total_dividend_post_tax += row["dividend_post_tax"]

                if not row["priced"]:
                    unpriced_count += 1

                # 表示
                average_price = row["average_price"]
                latest_price = row["latest_price"]
                value = row["value"]

                daily_profit = row["daily_profit"]
                profit = row["profit"]

                if daily_profit is not None:
                    daily_profit_text = f"{daily_profit:+,.0f}"
                    daily_profit_text = f"{daily_profit_text:>{WIDTH_DAILY_PROFIT}}"
                    daily_profit_text = colorise_profit(
                        daily_profit,
                        daily_profit_text,
                    )
                else:
                    daily_profit_text = f"{'-':>{WIDTH_DAILY_PROFIT}}"

                if profit is not None:
                    profit_text = f"{profit:+,.0f}"
                    profit_text = f"{profit_text:>16}"
                    profit_text = colorise_profit(profit, profit_text)
                else:
                    profit_text = f"{'-':>{WIDTH_PROFIT}}"

                if row["value"] is not None:
                    if mode == "minimal":
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
                            f"{latest_price:>{WIDTH_PRICE},.1f}"
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
    if mode in ("normal", "minimal"):
        summary = calculate_portfolio_summary(
            total_cost=total_cost,
            total_value=total_value,
            total_priced_cost=total_priced_cost,
            total_previous_value=total_previous_value,
            total_daily_profit=total_daily_profit,
            total_month_previous_value=total_month_previous_value,
            total_three_month_previous_value=total_three_month_previous_value,
            total_dividend_pre_tax=total_dividend_pre_tax,
            total_dividend_post_tax=total_dividend_post_tax,
            unpriced_count=unpriced_count,
        )
        sector_allocation = calculate_sector_allocation(
            holdings,
            latest_prices,
            previous_prices,
            sector_names,
        )

        if mode != "minimal":
            print_sector_allocation(
                holdings,
                latest_prices,
                previous_prices,
                sector_names,
                width=WIDTH,
            )

        print_portfolio_summary(summary)

        ai_data = build_portfolio_analysis_input(
            holdings=holdings,
            latest_prices=latest_prices,
            previous_prices=previous_prices,
            month_previous_prices=month_previous_prices,
            three_month_previous_prices=three_month_previous_prices,
            forecast_dividends=forecast_dividends,
            company_names=company_names,
            sector_names=sector_names,
            summary=summary,
            sector_allocation=sector_allocation,
        )
        print("-" * WIDTH)
        print("AIポートフォリオ分析")
        print("-" * WIDTH)
        analyze_portfolio(ai_data)
        # print(analysis)

    # ── 既存の配当金などの表示が終わったあとに追加 ──
    if mode == "documents":
        DOC_LIMIT = 10
        TDNET_DOC_LIMIT = 10
    elif mode == "tdnet":
        DOC_LIMIT = 0
        TDNET_DOC_LIMIT = 20
    elif mode == "edinet":
        DOC_LIMIT = 20
        TDNET_DOC_LIMIT = 0
    else:
        DOC_LIMIT = 4
        TDNET_DOC_LIMIT = 4

    if mode in ("normal", "documents", "edinet"):
        # 保有銘柄全体のコードリストを使って直近10件を取得
        recent_portfolio_edinet_docs = get_portfolio_recent_edinet_documents(
            conn, codes, limit=DOC_LIMIT
        )
        total_docs = len(recent_portfolio_edinet_docs)
        print("=" * WIDTH)
        print(f"   保有銘柄の直近のEDINET開示書類 (上位{total_docs}件)")
        print("-" * WIDTH)

        if not recent_portfolio_edinet_docs:
            print("  直近の開示書類はありません。")
        else:
            for idx, (
                doc_id,
                description,
                submit_dt,
                stock_code,
                company_name,
            ) in enumerate(recent_portfolio_edinet_docs, 1):
                url = f"https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?{doc_id}"
                styled_company = f"{BOLD}{FG_BRIGHT_WHITE}{company_name}{RESET}"
                styled_url = f"{FG_CYAN}{url}{RESET}"
                prefix = "  └─" if idx == total_docs else "  ├─"
                indent = "     " if idx == total_docs else "  │  "

                print(f"{prefix} [{stock_code}] {styled_company} | {submit_dt}")
                print(f"{indent} {description}")
                print(f"{indent} {styled_url}")

    if mode in ("normal", "documents", "tdnet"):
        recent_portfolio_tdnet_docs = get_portfolio_recent_tdnet_documents(
            conn, codes, limit=TDNET_DOC_LIMIT
        )
        total_docs = len(recent_portfolio_tdnet_docs)
        print("-" * WIDTH)
        print(f"   保有銘柄の直近のTDNET開示書類 (上位{total_docs}件)")
        print("-" * WIDTH)

        if not recent_portfolio_tdnet_docs:
            print("  直近の開示書類はありません。")
        else:
            for idx, (
                disclosure_id,
                disclosure_date,
                disclosure_time,
                sec_code,
                title,
                pdf_url,
            ) in enumerate(recent_portfolio_tdnet_docs, 1):
                company_name = company_names.get(sec_code, "不明")
                styled_company = f"{BOLD}{FG_BRIGHT_WHITE}{company_name}{RESET}"
                url = pdf_url
                hyperlink = f"\033]8;;{url}\033\\{url}\033]8;;\033\\"
                styled_url = f"{FG_CYAN}{hyperlink}{RESET}"

                prefix = "  └─" if idx == total_docs else "  ├─"
                indent = "     " if idx == total_docs else "  │  "

                print(
                    f"{prefix} [{sec_code}] {styled_company} | {disclosure_date} {disclosure_time}"
                )
                print(f"{indent} {title}")
                print(f"{indent} {styled_url}")
    print("=" * WIDTH)

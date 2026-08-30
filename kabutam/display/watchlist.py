import threading

from kabutam.animations.spinners import show_spinner
from kabutam.db.watchlist import get_watchlist
from kabutam.display.colors import colorise_profit
from kabutam.display.terminal import fit_text
from kabutam.stock.saveprice import ensure_recent_prices

# スタイルの定義
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
FG_BRIGHT_WHITE = "\033[97m"
FG_CYAN = "\033[36m"
FG_GRAY = "\033[90m"


def get_watchlist_recent_edinet_documents(conn, codes, limit=10):
    """
    Watchlistに登録された銘柄に紐づく
    直近のEDINET開示書類を日時降順で取得する。
    """

    if not codes or limit <= 0:
        return []

    placeholders = ",".join(["?"] * len(codes))

    query = f"""
        SELECT
            T1.document_id,
            T1.doc_description,
            T1.submit_datetime,
            T2.Code,
            T3.CoName
        FROM edinet_doc_list T1
        JOIN edinet_master T2
            ON T1.EDINETCode = T2.EDINETCode
        LEFT JOIN equities_master T3
            ON T2.Code = T3.Code
        WHERE T2.Code IN ({placeholders})
            AND date(T1.submit_datetime) >= date('now', '-30 days')
        ORDER BY T1.submit_datetime DESC
        LIMIT ?
    """

    params = list(codes) + [limit]

    cursor = conn.execute(query, params)

    return cursor.fetchall()


def get_watchlist_recent_tdnet_documents(conn, codes, limit=10):
    """
    Watchlistに登録された銘柄に紐づく
    直近のTDnet開示情報を開示日時の降順で取得する。
    """

    if not codes or limit <= 0:
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


def calculate_change_rate(latest_price, base_price):
    if latest_price is None or base_price is None:
        return None

    if base_price == 0:
        return None

    return (latest_price - base_price) / base_price * 100


def format_change_rate(rate, width):
    if rate is None:
        return f"{'-':>{width}}"

    text = f"{rate:+.2f}%"
    return f"{text:>{width}}"


def show_watchlist(conn, mode="normal"):
    """
    Watchlistに登録された銘柄をターミナルに表示する。

    mode:
        normal    : 株価 + EDINET + TDnet
        documents : 株価 + EDINET + TDnet
        edinet    : 株価 + EDINET
        tdnet     : 株価 + TDnet
    """

    codes = get_watchlist(conn)

    if not codes:
        print("登録銘柄はありません。")
        return

    # --------------------------------------------------
    # 表示幅
    # --------------------------------------------------

    WIDTH_CODE = 8
    WIDTH_COMPANY = 25
    WIDTH_CHANGE = 10
    WIDTH_PRICE = 10

    WIDTH = WIDTH_CODE + WIDTH_COMPANY + WIDTH_CHANGE * 5 + WIDTH_PRICE

    # --------------------------------------------------
    # EDINET / TDnet 表示件数
    # --------------------------------------------------
    DOC_LIMIT = 4
    TDNET_DOC_LIMIT = 4

    # --------------------------------------------------
    # 企業名取得
    # --------------------------------------------------

    placeholders = ",".join("?" for _ in codes)

    rows = conn.execute(
        f"""
        SELECT Code, CoName
        FROM equities_master
        WHERE Code IN ({placeholders})
        """,
        codes,
    ).fetchall()

    company_names = dict(rows)

    # --------------------------------------------------
    # 株価取得
    # --------------------------------------------------

    latest_prices = {}
    previous_prices = {}
    week_prices = {}
    month_prices = {}
    three_month_prices = {}

    current_ref = [0]
    status_ref = ["株価情報を更新しています"]
    stop_event = threading.Event()

    def on_price_event(message):
        status_ref[0] = message

    spinner = threading.Thread(
        target=show_spinner,
        args=(
            stop_event,
            current_ref,
            len(codes),
            status_ref,
        ),
    )

    spinner.start()

    try:
        for code in codes:
            prices = ensure_recent_prices(
                conn,
                code,
                60,
                on_event=on_price_event,
            )

            if prices:
                # 最新営業日
                latest_prices[code] = prices[0][4]

                # 前営業日
                # if len(prices) >= 2:
                #     previous_prices[code] = prices[1][4]
                # else:
                #     previous_prices[code] = None
                previous_prices[code] = prices[1][4] if len(prices) >= 2 else None
                week_prices[code] = prices[5][4] if len(prices) >= 6 else None
                month_prices[code] = prices[20][4] if len(prices) >= 21 else None
                three_month_prices[code] = prices[59][4] if len(prices) >= 60 else None

            else:
                latest_prices[code] = None
                previous_prices[code] = None

            current_ref[0] += 1

    finally:
        stop_event.set()
        spinner.join()

    # --------------------------------------------------
    # 株価表示
    # --------------------------------------------------

    print("=" * WIDTH)
    print("登録銘柄（Watchlist）")
    print("=" * WIDTH)

    print(
        f"{'Code':<{WIDTH_CODE}}"
        f"{fit_text('Company', WIDTH_COMPANY)}"
        f"{'3 M':>{WIDTH_CHANGE}}"
        f"{'1 M':>{WIDTH_CHANGE}}"
        f"{'1 W':>{WIDTH_CHANGE}}"
        f"{'1 D':>{WIDTH_CHANGE}}"
        f"{'Change':>{WIDTH_CHANGE}}"
        f"{'Price':>{WIDTH_PRICE}}"
    )

    print("-" * WIDTH)

    for code in codes:
        name = company_names.get(code, "不明")

        company_raw = fit_text(name, WIDTH_COMPANY)
        company = f"{BOLD}{FG_BRIGHT_WHITE}{company_raw}{RESET}"

        latest_price = latest_prices.get(code)
        previous_price = previous_prices.get(code)

        if latest_price is not None:
            if previous_price is not None:
                daily_change = latest_price - previous_price

                daily_change_rate = calculate_change_rate(latest_price, previous_price)

                weekly_change_rate = calculate_change_rate(
                    latest_price, week_prices.get(code)
                )

                monthly_change_rate = calculate_change_rate(
                    latest_price, month_prices.get(code)
                )
                three_month_change_rate = calculate_change_rate(
                    latest_price, three_month_prices.get(code)
                )

                daily_change_text = f"{daily_change:+,.0f}"
                daily_change_text = f"{daily_change_text:>{WIDTH_CHANGE}}"
                # rate
                daily_change_rate_text = format_change_rate(
                    daily_change_rate, WIDTH_CHANGE
                )
                weekly_change_rate_text = format_change_rate(
                    weekly_change_rate, WIDTH_CHANGE
                )
                monthly_change_rate_text = format_change_rate(
                    monthly_change_rate, WIDTH_CHANGE
                )
                three_month_change_rate_text = format_change_rate(
                    three_month_change_rate, WIDTH_CHANGE
                )

                daily_change_text = colorise_profit(
                    daily_change,
                    daily_change_text,
                )
                daily_change_rate_text = colorise_profit(
                    daily_change_rate,
                    daily_change_rate_text,
                )
                weekly_change_rate_text = colorise_profit(
                    weekly_change_rate,
                    weekly_change_rate_text,
                )
                monthly_change_rate_text = colorise_profit(
                    monthly_change_rate,
                    monthly_change_rate_text,
                )
                three_month_change_rate_text = colorise_profit(
                    three_month_change_rate,
                    three_month_change_rate_text,
                )

            else:
                daily_change_text = f"{'-':>{WIDTH_CHANGE}}"

            price_text = f"{latest_price:>{WIDTH_PRICE},.0f}"

        else:
            daily_change_text = f"{'-':>{WIDTH_CHANGE}}"
            price_text = f"{'-':>{WIDTH_PRICE}}"

        print(
            f"{code:<{WIDTH_CODE}}{company}{three_month_change_rate_text}{monthly_change_rate_text}{weekly_change_rate_text}{daily_change_rate_text}{daily_change_text}{price_text}"
        )

    # --------------------------------------------------
    # EDINET
    # --------------------------------------------------

    if mode in ("normal", "documents", "edinet"):
        recent_watchlist_edinet_docs = get_watchlist_recent_edinet_documents(
            conn,
            codes,
            limit=DOC_LIMIT,
        )
        total_docs = len(recent_watchlist_edinet_docs)
        print("=" * WIDTH)
        print(f"   登録銘柄の直近のEDINET開示書類 (上位{total_docs}件)")
        print("-" * WIDTH)

        if not recent_watchlist_edinet_docs:
            print("  直近の開示書類はありません。")

        else:
            for idx, (
                doc_id,
                description,
                submit_dt,
                stock_code,
                company_name,
            ) in enumerate(
                recent_watchlist_edinet_docs,
                1,
            ):
                url = f"https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?{doc_id}"
                styled_company = f"{BOLD}{FG_BRIGHT_WHITE}{company_name}{RESET}"
                styled_url = f"{FG_CYAN}{url}{RESET}"
                prefix = "  └─" if idx == total_docs else "  ├─"
                indent = "     " if idx == total_docs else "  │  "

                print(f"{prefix} [{stock_code}] {styled_company} | {submit_dt}")
                print(f"{indent} {description}")
                print(f"{indent} {styled_url}")

    # --------------------------------------------------
    # TDnet
    # --------------------------------------------------

    if mode in ("normal", "documents", "tdnet"):
        recent_watchlist_tdnet_docs = get_watchlist_recent_tdnet_documents(
            conn,
            codes,
            limit=TDNET_DOC_LIMIT,
        )
        total_docs = len(recent_watchlist_tdnet_docs)
        print("=" * WIDTH)
        print(f"   登録銘柄の直近のTDnet開示書類 (上位{total_docs}件)")
        print("-" * WIDTH)

        if not recent_watchlist_tdnet_docs:
            print("  直近の開示書類はありません。")

        else:
            for idx, (
                disclosure_id,
                disclosure_date,
                disclosure_time,
                sec_code,
                title,
                pdf_url,
            ) in enumerate(
                recent_watchlist_tdnet_docs,
                1,
            ):
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

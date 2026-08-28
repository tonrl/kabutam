import threading

from kabutam.animations.spinners import show_spinner
from kabutam.display.terminal import fit_number
from kabutam.edinet.get_irdoc_list import sync_recent_edinet_doc_list
from kabutam.edinet.show_corpdata import get_stock_info
from kabutam.tdnet.sync_tdnet import sync_recent_tdnet

DATA_GET_LIMIT = 6

# スタイルの定義
RESET = "\033[0m"
FG_GRAY = "\033[90m"
FG_CYAN = "\033[36m"
FG_BRIGHT_WHITE = "\033[97m"
DIM = "\033[2m"
BOLD = "\033[1m"


def get_recent_corp_documents(conn, edinet_code, limit):
    """
    指定したEDINETコードに紐づく直近の開示書類をDBから取得する
    """
    cursor = conn.execute(
        """
        SELECT document_id, doc_description, submit_datetime
        FROM edinet_doc_list
        WHERE EDINETCode = ?
        ORDER BY submit_datetime DESC
        LIMIT ?
    """,
        (edinet_code, limit),
    )

    return cursor.fetchall()


def get_recent_tdnet_documents(conn, sec_code, limit):
    """
    指定した証券コードに紐づく直近のTDnet開示資料をDBから取得する。
    """

    cursor = conn.execute(
        """
        SELECT
            disclosure_id,
            disclosure_date,
            disclosure_time,
            title,
            pdf_url
        FROM tdnet_disclosure
        WHERE sec_code = ?
        ORDER BY disclosure_date DESC, disclosure_time DESC
        LIMIT ?
    """,
        (sec_code, limit),
    )

    return cursor.fetchall()


def calc_stock_info(stock_info):
    corpdata = stock_info["corpdata"]
    # EDINET財務情報が取得出来なかった場合
    if corpdata is None:
        return {
            **stock_info,
            "calculated": None,
        }
    (
        edinet_code,
        disclosure_date,
        fiscal_year,
        quarter,
        per,
        pbr,
        eps,
        bps,
        roe,
        dividend_yield,
        dividend_per_share,
        interim_dividend_per_share,
        yearend_dividend_per_share,
        forecast_dividend_per_share,
        revenue,
        operating_income,
        ordinary_income,
        net_income,
        forecast_revenue,
        forecast_operating_income,
        forecast_net_income,
        forecast_eps,
        equity_ratio,
        cash,
        total_assets,
        total_liabilities,
        shareholders_equity,
        net_assets,
        operating_cf,
        capex,
        depreciation,
        interest_bearing_debt,
        land,
        investment_securities,
        updated_at,
    ) = corpdata

    latest_price = stock_info["latest_price"]
    # calc data
    edinet_per = per
    edinet_pbr = pbr
    current_per = None
    current_pbr = None

    if latest_price is not None:
        if eps is not None and eps > 0:
            current_per = latest_price / eps
        if bps is not None and bps > 0:
            current_pbr = latest_price / bps

    current_dividend_yield = None
    if (
        latest_price is not None
        and forecast_dividend_per_share is not None
        and latest_price > 0
    ):
        current_dividend_yield = forecast_dividend_per_share / latest_price
    return {
        **stock_info,
        "calculated": {
            "edinet_code": edinet_code,
            "disclosure_date": disclosure_date,
            "fiscal_year": fiscal_year,
            "quarter": quarter,
            "per": per,
            "pbr": pbr,
            "eps": eps,
            "bps": bps,
            "roe": roe,
            "dividend_yield": dividend_yield,
            "dividend_per_share": dividend_per_share,
            "interim_dividend_per_share": interim_dividend_per_share,
            "yearend_dividend_per_share": yearend_dividend_per_share,
            "forecast_dividend_per_share": forecast_dividend_per_share,
            "revenue": revenue,
            "operating_income": operating_income,
            "ordinary_income": ordinary_income,
            "net_income": net_income,
            "forecast_revenue": forecast_revenue,
            "forecast_operating_income": forecast_operating_income,
            "forecast_net_income": forecast_net_income,
            "forecast_eps": forecast_eps,
            "equity_ratio": equity_ratio,
            "cash": cash,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "shareholders_equity": shareholders_equity,
            "net_assets": net_assets,
            "operating_cf": operating_cf,
            "capex": capex,
            "depreciation": depreciation,
            "interest_bearing_debt": interest_bearing_debt,
            "land": land,
            "investment_securities": investment_securities,
            "updated_at": updated_at,
            # 計算値
            "edinet_per": edinet_per,
            "edinet_pbr": edinet_pbr,
            "current_per": current_per,
            "current_pbr": current_pbr,
            "current_dividend_yield": current_dividend_yield,
        },
    }


# ------------------------------------------------------------
# Display Info
# ------------------------------------------------------------
def display_stock_info(stock_info, mode="normal"):
    company = stock_info["company"]
    prices = stock_info["prices"]
    calculated = stock_info["calculated"]
    recent_edinet_docs = stock_info.get("recent_edinet_documents", [])
    recent_tdnet_docs = stock_info.get("recent_tdnet_documents", [])

    # 基本情報
    code = company["code"]
    name = company["name"]
    name_en = company["name_en"]
    sector17 = company["sector17"]
    sector33 = company["sector33"]
    scale = company["scale"]
    market = company["market"]
    edinetcode = stock_info["edinet"]["code"]

    print("=" * 67)
    print(f"銘柄コード : {code}")
    print(f"会社名     : {name}")
    print(f"英語名     : {name_en}")
    print(f"17業種     : {sector17}")
    print(f"33業種     : {sector33}")
    print(f"規模区分   : {scale}")
    print(f"市場       : {market}")
    print(f"EDI Code   : {edinetcode}")
    print("=" * 67)

    print("過去3営業日の株価")
    print("-" * 67)
    print(f"{'Date':<12}{'Open':>10}{'High':>10}{'Low':>10}{'Close':>10}{'Volume':>15}")

    for price in prices:
        date, open_, high, low, close, volume, *_ = price
        print(
            f"{date:<12}"
            f"{fit_number(open_, 10)}"
            f"{fit_number(high, 10)}"
            f"{fit_number(low, 10)}"
            f"{fit_number(close, 10)}"
            f"{fit_number(volume, 15, 0)}"
        )
    if calculated is None:
        print("=" * 67)
        print()
        print("EDINET財務情報")
        print("-" * 60)
        print("取得できませんでした。")
        print("-" * 60)
        return

    c = calculated
    if mode == "normal":
        print("-" * 67)
        print()
        print("EDINET財務情報")
        print(f"決算開示日     : {c['disclosure_date']}")
        print(f"会計年度       : {c['fiscal_year']}")
        print(f"四半期         : {c['quarter']}")
        print()
        print("バリュエーション")
        print("-" * 60)

        print(
            f"PER            : {c['current_per']:.2f}倍"
            if c["current_per"] is not None
            else "PER            : -"
        )

        print(
            f"PBR            : {c['current_pbr']:.2f}倍"
            if c["current_pbr"] is not None
            else "PBR            : -"
        )

        print(
            f"EPS            : {c['eps']:.2f}円"
            if c["eps"] is not None
            else "EPS            : -"
        )

        print(
            f"BPS            : {c['bps']:.2f}円"
            if c["bps"] is not None
            else "BPS            : -"
        )

        print(
            f"ROE            : {c['roe'] * 100:.2f}%"
            if c["roe"] is not None
            else "ROE            : -"
        )

        print()
        print("配当")
        print("-" * 60)

        print(
            f"配当利回り     : {c['current_dividend_yield'] * 100:.2f}%"
            if c["current_dividend_yield"] is not None
            else "配当利回り     : -"
        )

        print(
            f"年間配当実績   : {c['dividend_per_share']:.2f} 円"
            if c["dividend_per_share"] is not None
            else "年間配当実績   : -"
        )

        print(
            f"中間配当       : {c['interim_dividend_per_share']:.2f} 円"
            if c["interim_dividend_per_share"] is not None
            else "中間配当       : -"
        )

        print(
            f"期末配当       : {c['yearend_dividend_per_share']:.2f} 円"
            if c["yearend_dividend_per_share"] is not None
            else "期末配当       : -"
        )

        print(
            f"予想年間配当   : {c['forecast_dividend_per_share']:.2f} 円"
            if c["forecast_dividend_per_share"] is not None
            else "予想年間配当   : -"
        )

        # 前年度実績
        print()
        print("通期実績")
        print("-" * 60)

        print(
            f"売上高         : {c['revenue'] / 1e6:,.0f} 百万円"
            if c["revenue"] is not None
            else "売上高         : -"
        )

        print(
            f"営業利益       : {c['operating_income'] / 1e6:,.0f} 百万円"
            if c["operating_income"] is not None
            else "営業利益       : -"
        )

        print(
            f"経常利益       : {c['ordinary_income'] / 1e6:,.0f} 百万円"
            if c["ordinary_income"] is not None
            else "経常利益       : -"
        )

        print(
            f"純利益         : {c['net_income'] / 1e6:,.0f} 百万円"
            if c["net_income"] is not None
            else "純利益         : -"
        )

        # ============================================================
        # 最新決算予想
        # ============================================================

        print()
        print("通期会社予想")
        print("-" * 70)

        print(
            f"売上高予想     : {c['forecast_revenue']:,.0f} 百万円"
            if c["forecast_revenue"] is not None
            else "売上高予想     : -"
        )

        print(
            f"営業利益予想   : {c['forecast_operating_income']:,.0f} 百万円"
            if c["forecast_operating_income"] is not None
            else "営業利益予想   : -"
        )

        print(
            f"純利益予想     : {c['forecast_net_income']:,.0f} 百万円"
            if c["forecast_net_income"] is not None
            else "純利益予想     : -"
        )

        print(
            f"EPS予想        : {c['forecast_eps']:.2f} 円"
            if c["forecast_eps"] is not None
            else "EPS予想        : -"
        )

        print()
        print("財務")
        print("-" * 60)

        print(
            f"自己資本比率   : {c['equity_ratio'] * 100:.2f}%"
            if c["equity_ratio"] is not None
            else "自己資本比率   : -"
        )

        print(
            f"現金           : {c['cash'] / 1e6:,.0f} 百万円"
            if c["cash"] is not None
            else "現金           : -"
        )

        print(
            f"総資産         : {c['total_assets'] / 1e6:,.0f} 百万円"
            if c["total_assets"] is not None
            else "総資産         : -"
        )

        print(
            f"総負債         : {c['total_liabilities'] / 1e6:,.0f} 百万円"
            if c["total_liabilities"] is not None
            else "総負債         : -"
        )

        print(
            f"株主資本       : {c['shareholders_equity'] / 1e6:,.0f} 百万円"
            if c["shareholders_equity"] is not None
            else "株主資本       : -"
        )

        print(
            f"純資産         : {c['net_assets'] / 1e6:,.0f} 百万円"
            if c["net_assets"] is not None
            else "純資産         : -"
        )

        print(
            f"有利子負債     : {c['interest_bearing_debt'] / 1e6:,.0f} 百万円"
            if c["interest_bearing_debt"] is not None
            else "有利子負債     : -"
        )

        print()
        print("キャッシュ・フロー")
        print("-" * 60)

        print(
            f"営業CF         : {c['operating_cf'] / 1e6:,.0f} 百万円"
            if c["operating_cf"] is not None
            else "営業CF         : -"
        )

        print(
            f"設備投資       : {c['capex'] / 1e6:,.0f} 百万円"
            if c["capex"] is not None
            else "設備投資       : -"
        )

        print(
            f"減価償却       : {c['depreciation'] / 1e6:,.0f} 百万円"
            if c["depreciation"] is not None
            else "減価償却       : -"
        )

        print()
        print("その他")
        print("-" * 60)

        print(
            f"土地           : {c['land'] / 1e6:,.0f} 百万円"
            if c["land"] is not None
            else "土地           : -"
        )

        print(
            f"投資有価証券   : {c['investment_securities'] / 1e6:,.0f} 百万円"
            if c["investment_securities"] is not None
            else "投資有価証券   : -"
        )

        print()
        print(f"DB最終確認     : {c['updated_at']}")

    print("-" * 67)
    print("   直近の開示書類 (EDINET)")
    print("-" * 67)

    if not recent_edinet_docs:
        print("  直近の開示書類はありません。")
    else:
        for idx, (doc_id, description, submit_dt) in enumerate(recent_edinet_docs, 1):
            # 閲覧用URLの組み立て
            url = f"https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?{doc_id}"
            hyperlink = f"\033]8;;{url}\033\\{url}\033]8;;\033\\"
            styled_url = f"{FG_CYAN}{hyperlink}{RESET}"

            print(f"[{idx:2d}] {description}")
            print(f"     {submit_dt}")
            print(f"   {styled_url}")

    print()
    print("-" * 67)
    print("   直近の開示情報 (TDnet)")
    print("-" * 67)
    if not recent_tdnet_docs:
        print("  直近の開示情報はありません。")
    else:
        for idx, (
            disclosure_id,
            disclosure_date,
            disclosure_time,
            title,
            pdf_url,
        ) in enumerate(recent_tdnet_docs, 1):
            hyperlink = f"\033]8;;{pdf_url}\033\\{pdf_url}\033]8;;\033\\"

            styled_url = f"{FG_CYAN}{hyperlink}{RESET}"

            print(f"[{idx:2d}] {title}")
            print(f"     {disclosure_date} {disclosure_time}")
            print(f"   {styled_url}")
    print("-" * 67)


# ------------------------------------------------------------
def show_stock(conn, code, mode="normal"):

    stop_event = threading.Event()
    # message_ref = ["銘柄情報を取得しています"]
    message_ref = ["銘柄情報を取得しています"]

    spinner = threading.Thread(
        target=show_spinner, args=(stop_event, None, None, message_ref)
    )

    spinner.start()

    try:
        sync_recent_edinet_doc_list(conn, message_ref=message_ref)
        sync_recent_tdnet(conn, message_ref=message_ref)
        message_ref[0] = "銘柄情報を取得しています"
        stock_info = get_stock_info(
            conn,
            code,
            message_ref=message_ref,
        )

        if stock_info is None:
            return

        stock_info = calc_stock_info(stock_info)
        edinet_code = stock_info["edinet"]["code"]
        # EDINET CODE
        recent_edinet_docs = (
            get_recent_corp_documents(conn, edinet_code, limit=DATA_GET_LIMIT)
            if edinet_code
            else []
        )

        # TDInet
        recent_tdnet_docs = get_recent_tdnet_documents(conn, code, limit=DATA_GET_LIMIT)

        stock_info["recent_edinet_documents"] = recent_edinet_docs
        stock_info["recent_tdnet_documents"] = recent_tdnet_docs

    finally:
        stop_event.set()
        spinner.join()

    display_stock_info(stock_info, mode=mode)

from datetime import datetime, timedelta
from kabutam.edinet.client import search_edinet_data
import requests
CHECK_INTERVAL = timedelta(days=7)

# -----------------------------------------------------------
# Corp Data
# -----------------------------------------------------------

def get_corpdata(conn, edinet_code, message_ref=None):

    row = conn.execute("""
        SELECT *
        FROM edinet_corp_data
        WHERE EDINETCode = ?
    """, (edinet_code,)).fetchone()

    # DBに存在しない
    if row is None:
        if message_ref is not None:
            message_ref[0] = "EDINET DBから財務データを取得しています..."

        return fetch_and_save_corpdata(
            conn,
            edinet_code,
            message_ref
        )

    # 最終確認日時
    updated_at = datetime.fromisoformat(row[-1])

    # 7日以内ならDBをそのまま使用
    if datetime.now() - updated_at < CHECK_INTERVAL:
        return row

    # 7日以上経過
    # EDINET DBに新しい決算があるか確認
    return refresh_corpdata_if_needed(
        conn,
        edinet_code,
        message_ref
    )


def fetch_and_save_corpdata(conn, edinet_code, message_ref=None):
    if message_ref is not None:
        message_ref[0] = "EDINET DB APIから財務データを取得しています..."

    result = search_edinet_data(edinet_code) 
    if result is None:
        print("\n財務データの取得に失敗しました")
        return None

    try: 
        return save_corpdata(
                conn,
                edinet_code,
                result,
                message_ref
        )
    except (KeyError, TypeError, ValueError) as e: 
        print(f"\nエラー: EDINET DBデータの処理に失敗しました: {e}") 
        return None

def refresh_corpdata_if_needed(conn, edinet_code, message_ref=None):
    if message_ref is not None:
            message_ref[0] = "EDINET DBの更新状況を確認しています..."

    try:

        old = conn.execute("""
            SELECT DisclosureDate
            FROM edinet_corp_data
            WHERE EDINETCode = ?
        """, (
            edinet_code,
        )).fetchone()

        if old is None:
            return fetch_and_save_corpdata(
                conn,
                edinet_code,
                message_ref
            )

        old_disclosure_date = old[0]
        if message_ref is not None:
            message_ref[0] = "EDINET DB APIの更新状況を確認しています..."

        result = search_edinet_data(edinet_code)
        if result is None:
            print("\nEDINET DB APIに接続出来ませんでした")
            return conn.execute(
                    "SELECT * FROM edinet_corp_data WHERE EDINETCode = ?", (edinet_code,)
            ).fetchone()

        data = result["data"]



        earnings = data.get("latest_earnings", {})

        new_disclosure_date = earnings.get(
            "disclosure_date"
        )

        # ----------------------------------------
        # 新しい決算情報なし
        # ----------------------------------------
        if new_disclosure_date == old_disclosure_date:

            conn.execute("""
                UPDATE edinet_corp_data
                SET UpdatedAt = ?
                WHERE EDINETCode = ?
            """, (
                datetime.now().isoformat(
                    timespec="seconds"
                ),
                edinet_code
            ))

            conn.commit()

            print("\n財務データに変更はありません。")

            return conn.execute("""
                SELECT *
                FROM edinet_corp_data
                WHERE EDINETCode = ?
            """, (edinet_code,)).fetchone()

        # ----------------------------------------
        # 新しい決算情報あり
        # ----------------------------------------
        if message_ref is not None:
            message_ref[0] = "新しい決算情報を検出しました。"

        print(
            f"{old_disclosure_date} "
            f"→ {new_disclosure_date}"
        )

        return save_corpdata(
            conn,
            edinet_code,
            result,
            message_ref
        )

    except requests.RequestException as e:

        print(f"EDINET DB API error: {e}")

        # APIが失敗したら古いデータを返す
        return conn.execute("""
            SELECT *
            FROM edinet_corp_data
            WHERE EDINETCode = ?
        """, (edinet_code,)).fetchone()


def save_corpdata(conn, edinet_code, result, message_ref=None):
    data = result["data"]
    financials = data.get("latest_financials", {})
    earnings = data.get("latest_earnings", {})

    # 最新決算短信
    disclosure_date = earnings.get("disclosure_date")

    fiscal_year = earnings.get("fiscal_year")

    quarter = earnings.get("quarter")

    # Valuation
    # PBR = PER * ESP / BPS
    per = financials.get("per")
    eps = financials.get("eps")
    bps = financials.get("bps")
    pbr = None
    if ( 
        per is not None
        and eps is not None 
        and bps is not None 
        and bps != 0 ):
        pbr = per * eps / bps
    # ROE
    roe = financials.get("roe_official")
    #================================
    # 配当
    #================================
    dividend_per_share = financials.get("dividend_per_share")
    # EDINET DB の latest_earnings にある # 年間予想配当を優先 
    forecast_dividend_per_share = earnings.get("forecast_dividend_per_share")
    interim_dividend_per_share = earnings.get("interim_dividend_per_share")
    yearend_dividend_per_share = earnings.get("yearend_dividend_per_share")
    # 配当利回り
    dividend_yield = None
    if ( 
        dividend_per_share is not None 
        and per is not None
        and eps is not None 
        and per > 0
        and eps > 0 
        ): 
        implied_price = per * eps 

        if implied_price > 0: 
            dividend_yield = ( dividend_per_share
                              / implied_price 
            )

    #=====================================
    # 実績業績
    # latest_financials は円単位
    #=====================================
    revenue = financials.get("revenue")
    operating_income = financials.get("operating_income")
    ordinary_income = financials.get("ordinary_income")
    net_income = financials.get("net_income")


    #====================================
    #最新決算短信
    #====================================
    forecast_revenue = earnings.get("forecast_revenue")
    forecast_operating_income = earnings.get("forecast_operating_income")
    forecast_net_income = earnings.get("forecast_net_income")
    forecast_eps = earnings.get("forecast_eps")

    #財務
    # Latest finance
    equity_ratio = financials.get("equity_ratio_official")
    cash = financials.get("cash")
    total_assets = financials.get("total_assets")
    total_liabilities = financials.get("total_liabilities")
    shareholders_equity = financials.get("shareholders_equity")
    net_assets = financials.get("net_assets")

    #キャッシュ・フロー
    operating_cf = financials.get("cf_operating")
    capex = financials.get("capex")
    depreciation = financials.get("depreciation")

    #有利子負債
    interest_bearing_debt = financials.get("ibd_current")
    if interest_bearing_debt is None: 
        debt_fields = [
                financials.get("short_term_loans"),
                financials.get("long_term_loans"), 
                financials.get("bonds_payable"), 
        ] 
        if any(
                value is not None 
                for value in debt_fields
        ): 
            interest_bearing_debt = sum(
                    value or 0 
                    for value in debt_fields
            )
        else:
            interest_bearing_debt = None


    #その他
    land = financials.get("land")
    investment_securities = financials.get(
            "investment_securities"
    )
    #更新日時
    updated_at = datetime.now().isoformat(timespec="seconds")
    # -------------------------------------------------------- 
    # 保存 
    #
    # -------------------------------------------------------- 

    values = (
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
            cash, total_assets,
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

    )

    conn.execute("""
        INSERT OR REPLACE INTO edinet_corp_data (
            EDINETCode,
            DisclosureDate,
            FiscalYear,
            Quarter,

            PER,
            PBR,
            EPS,
            BPS,
            ROE,
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

            UpdatedAt
        )
        VALUES (
            ?, ?, ?, ?, 
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ? 
        )
    """, values)

    conn.commit()

    if message_ref is not None:
        message_ref[0] = "財務データを保存しました。"

    return conn.execute("""
        SELECT *
        FROM edinet_corp_data
        WHERE EDINETCode = ?
    """, (edinet_code,)).fetchone()

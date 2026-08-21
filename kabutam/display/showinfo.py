from kabutam.db.connection import (
        get_connection,
        require_master_data
)
from kabutam.db.schema import create_table_corp_data
from kabutam.edinet.get_corpdata import get_corpdata
from kabutam.stock.saveprice import ensure_recent_prices
from kabutam.display.terminal import fit_number

# ------------------------------------------------------------
# 銘柄コード検索
# ------------------------------------------------------------

def show_stock(code):
    conn = get_connection()
    require_master_data(conn)

    company = conn.execute("""
        SELECT
            Code,
            CoName,
            CoNameEn,
            S17Nm,
            S33Nm,
            ScaleCat,
            MktNm
        FROM equities_master
        WHERE Code = ?
    """, (code,)).fetchone()

    if company is None:
        print(f"銘柄コード {code} は見つかりません。")
        conn.close()
        return

    edinetdata = conn.execute("""
        SELECT 
            EDINETCode, 
            ListingStatus 
        FROM edinet_master 
        WHERE Code = ? 
    """, (code,)).fetchone()

    # prices = conn.execute("""
    #     SELECT
    #         Date,
    #         Open,
    #         High,
    #         Low,
    #         Close,
    #         Volume,
    #         AdjOpen,
    #         AdjHigh,
    #         AdjLow,
    #         AdjClose,
    #         AdjVolume
    #     FROM prices
    #     WHERE Code = ?
    #     ORDER BY Date DESC
    #     LIMIT 3
    # """, (code,)).fetchall()

    prices = ensure_recent_prices(conn, code, 3)
    if prices:
        latest_price = prices[0][4]   # Date, Open, High, Low, Close, Volume...
    else:
        latest_price = None
    
    # 基本情報
    (
        code,
        name,
        name_en,
        sector17,
        sector33,
        scale,
        market
    ) = company

    if edinetdata is not None:
        edinetcode, listing_status = edinetdata 
    else: 
        edinetcode = None 
        listing_status = None

    # EDINET 情報
    corpdata = None
    if edinetcode is not None:

        create_table_corp_data(conn)

        corpdata = get_corpdata(
            conn,
            edinetcode
        )


    conn.close()

    print("=" * 60)
    print(f"銘柄コード : {code}")
    print(f"会社名     : {name}")
    print(f"英語名     : {name_en}")
    print(f"業種       : {sector33}")
    print(f"規模区分   : {scale}")
    print(f"市場       : {market}")
    print(f"EDI Code   : {edinetcode}")
    print("=" * 60)

    print("過去3営業日の株価")
    print("-" * 67)

    print(
        f"{'Date':<12}"
        f"{'Open':>10}"
        f"{'High':>10}"
        f"{'Low':>10}"
        f"{'Close':>10}"
        f"{'Volume':>15}"
    )

    print()

    # for price in prices:
    #     date, open_, high, low, close, volume, *_ = price
    #
    #     print(
    #         f"{date:<12}"
    #         f"{open_:>10.1f}"
    #         f"{high:>10.1f}"
    #         f"{low:>10.1f}"
    #         f"{close:>10.1f}"
    #         f"{volume:>15,.0f}"
    #     )
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


    print("-" * 67)
    if corpdata is None:
        print("EDINET財務情報")
        print("-" * 60)
        print("取得できませんでした。")
        return

    print("EDINET財務情報")
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

            updated_at
    ) = corpdata
    # calc data

    edinet_per = per
    edinet_pbr = pbr
    current_per = None
    current_pbr = None
    latest_price = None
    if prices:
        latest_price = prices[0][4]
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
        current_dividend_yield = (
                forecast_dividend_per_share / latest_price
        )


    print(f"決算開示日     : {disclosure_date}")
    print(f"会計年度       : {fiscal_year}")
    print(f"四半期         : {quarter}")

    print()
    print("バリュエーション")
    print("-" * 60)

    print(f"PER            : {current_per:.2f}倍" if per is not None else "PER            : -")
    print(f"PBR            : {current_pbr:.2f}倍" if pbr is not None else "PBR            : -")
    print(f"EPS            : {eps:.2f}円" if eps is not None else "EPS            : -")
    print(f"BPS            : {bps:.2f}円" if bps is not None else "BPS            : -")
    print(f"ROE            : {roe * 100:.2f}%" if roe is not None else "ROE            : -")

    print()
    print("配当")
    print("-" * 60)

    print(
            f"配当利回り     : {current_dividend_yield * 100:.2f}%"
            if current_dividend_yield is not None
            else "配当利回り     : -"
    )

    print(
            f"年間配当実績   : "
            f"{dividend_per_share:.2f} 円"
            if dividend_per_share is not None
            else "年間配当実績   : -"
    )

    print(
            f"中間配当       : "
            f"{interim_dividend_per_share:.2f} 円"
            if interim_dividend_per_share is not None
            else "中間配当       : -"
    )

    print(
            f"期末配当       : "
            f"{yearend_dividend_per_share:.2f} 円"
            if yearend_dividend_per_share is not None
            else "期末配当       : -"
    )
    print(
            f"予想年間配当   : "
            f"{forecast_dividend_per_share:.2f} 円"
            if forecast_dividend_per_share is not None
            else "予想年間配当   : -"
    )

    # 前年度実績
    print()
    print("通期実績")
    print("-" * 60)

    print(
            f"売上高         : {revenue / 1e6:,.0f} 百万円"
            if revenue is not None
            else "売上高         : -"
            )

    print(
            f"営業利益       : {operating_income / 1e6:,.0f} 百万円"
            if operating_income is not None
            else "営業利益       : -"
            )

    print(
            f"経常利益       : {ordinary_income / 1e6:,.0f} 百万円"
            if ordinary_income is not None
            else "経常利益       : -"
            )

    print(
            f"純利益         : {net_income / 1e6:,.0f} 百万円"
            if net_income is not None
            else "純利益         : -"
            )
    # ============================================================
    # 最新決算予想
    # ============================================================

    print()
    print("通期会社予想")
    print("-" * 70)

    print(
            f"売上高予想     : "
            f"{forecast_revenue:,.0f} 百万円"
            if forecast_revenue is not None
            else "売上高予想     : -"
    )

    print(
            f"営業利益予想   : "
            f"{forecast_operating_income:,.0f} 百万円"
            if forecast_operating_income is not None
            else "営業利益予想   : -"
    )

    print(
            f"純利益予想     : "
            f"{forecast_net_income:,.0f} 百万円"
            if forecast_net_income is not None
            else "純利益予想     : -"
    )

    print(
            f"EPS予想        : "
            f"{forecast_eps:.2f} 円"
            if forecast_eps is not None
            else "EPS予想        : -"
    )
    print()
    print("財務")
    print("-" * 60)

    print(
            f"自己資本比率   : {equity_ratio * 100:.2f}%"
            if equity_ratio is not None
            else "自己資本比率   : -"
            )

    print(
            f"現金           : {cash / 1e6:,.0f} 百万円"
            if cash is not None
            else "現金           : -"
            )

    print(
            f"総資産         : {total_assets / 1e6:,.0f} 百万円"
            if total_assets is not None
            else "総資産         : -"
            )

    print(
            f"総負債         : {total_liabilities / 1e6:,.0f} 百万円"
            if total_liabilities is not None
            else "総負債         : -"
            )

    print(
            f"株主資本       : {shareholders_equity / 1e6:,.0f} 百万円"
            if shareholders_equity is not None
            else "株主資本       : -"
            )

    print(
            f"純資産         : {net_assets / 1e6:,.0f} 百万円"
            if net_assets is not None
            else "純資産         : -"
            )

    print(
            f"有利子負債     : {interest_bearing_debt / 1e6:,.0f} 百万円"
            if interest_bearing_debt is not None
            else "有利子負債     : -"
            )

    print()
    print("キャッシュ・フロー")
    print("-" * 60)

    print(
            f"営業CF         : {operating_cf / 1e6:,.0f} 百万円"
            if operating_cf is not None
            else "営業CF         : -"
    )

    print(
            f"設備投資       : {capex / 1e6:,.0f} 百万円"
            if capex is not None
            else "設備投資       : -"
    )

    print(
            f"減価償却       : {depreciation / 1e6:,.0f} 百万円"
            if depreciation is not None
            else "減価償却       : -"
    )

    print()
    print("その他")
    print("-" * 60)

    print(
            f"土地           : {land / 1e6:,.0f} 百万円"
            if land is not None
            else "土地           : -"
            )

    print(
            f"投資有価証券   : {investment_securities / 1e6:,.0f} 百万円"
            if investment_securities is not None
            else "投資有価証券   : -"
            )

    print()
    print(f"DB最終確認     : {updated_at}")




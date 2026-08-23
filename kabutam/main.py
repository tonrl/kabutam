import argparse
from datetime import datetime
from kabutam.display.showinfo import show_stock
from kabutam.display.showlist import show_list
from kabutam.db.portfolio import (
    add_buy,
    add_sell,
)
from kabutam.db.connection import (
        get_connection,
        require_master_data
)
from kabutam.display.portfolio import show_portfolio
from kabutam.setup.fetch_jquants import fetch_and_save_jquants
from kabutam.setup.fetch_edinet import fetch_and_save_edinet
import sys

# CHECK_INTERVAL = timedelta(days=7)

# ------------------------------------------------------------
# TOPIX区分
# ------------------------------------------------------------

INDEX_MAP = {
        "core30": {
            "scale": "TOPIX Core30",
            "label": "TOPIX Core30",
        },

        "large70": {
            "scale": "TOPIX Large70",
            "label": "TOPIX Large70",
        },

        "100": {
            "scale": ["TOPIX Core30", "TOPIX Large70"],
            "label": "TOPIX 100",
        },

        "mid400": {
            "scale": "TOPIX Mid400",
            "label": "TOPIX Mid400",
        },

        "500": {
            "scale": ["TOPIX Core30", "TOPIX Large70", "TOPIX Mid400"],
            "label": "TOPIX 500",
        },

        "small1": {
            "scale": "TOPIX Small 1",
            "label": "TOPIX Small 1",
        },

        "small2": {
            "scale": "TOPIX Small 2",
            "label": "TOPIX Small 2",
        },
}


# ------------------------------------------------------------
# 市場
# ------------------------------------------------------------

MARKET_MAP = {
        "prime": "プライム",
        "standard": "スタンダード",
        "growth": "グロース",
        "pro": "TOKYO PRO MARKET",
}

# ------------------------------------------------------------
# LICENSE
# ------------------------------------------------------------

LICENSE_TEXT = """
Kabutam - 日本株検索 PF管理
Copyright (C) 2026 Tonrl

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
""".strip()
# ------------------------------------------------------------
# 口座種別
# -------------------------------------------------------------
ACCOUNT_MAP = {
        "tokutei": "特定",
        "nisa": "NISA",
        "ippan": "一般",
}

def init_db_data():
    # 対照表作成の処理
    print("=== 初期セットアップを開始します ===")
    try:
        # J-Quantsから銘柄データを取得
        fetch_and_save_jquants()
        
        # EDINETから対照表を作成
        fetch_and_save_edinet()
        
        print("=== すべての初期化が正常に完了しました！ ===")
        return True

    except Exception as e:
        print(f"初期化中にエラーが発生しました: {e}")
        return False


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(description="Kabutam 日本株検索 PF管理")
    trade = parser.add_mutually_exclusive_group()

    parser.add_argument(
            "--license",
            action="store_true",
            help="ライセンス情報を表示して終了する"
    )
    parser.add_argument(
            "--init",
            action="store_true",
            help="DBと初期データのセットアップを行う"
    )

    # --version を追加する
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.7\nCopyright (C) 2026 Tonrl\nLicense GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>"
        )

    parser.add_argument(
            "-C",
            "--code",
            help="銘柄コード"
    )

    parser.add_argument(
            "--index",
            choices=INDEX_MAP.keys(),
            help="TOPIX区分"
    )

    parser.add_argument(
            "--market",
            choices=MARKET_MAP.keys(),
            help="市場"
    )

    parser.add_argument(
            "--sector",
            help="33業種名"
    )

    parser.add_argument(
            "--portfolio",
            action="store_true",
            help="ポートフォリオを表示"
    )
    trade.add_argument(
            "--buy",
            type=str,
            metavar="CODE",
            help="株式を購入"
    )

    trade.add_argument(
            "--sell",
            type=str,
            metavar="CODE",
            help="株式を売却"
    )
    
    parser.add_argument(
            "--shares",
            type=int,
            help="株数"
    )
    
    parser.add_argument(
            "--price",
            type=float,
            help="取得価格"
    )
    
    parser.add_argument(
            "--date",
            type=str,
            help="取引日 YYYY-MM-DD"
    )
    parser.add_argument(
            "--account",

            choices=ACCOUNT_MAP.keys(),
            default="tokutei",
            help="口座区分: tokutei / nisa / ippan"
    )

    args = parser.parse_args()
    if args.license:
        print(LICENSE_TEXT)
        sys.exit(0)

    # initialisation
    if args.init:
        success = init_db_data()
        sys.exit(0 if success else 1)

    conn = get_connection()
    require_master_data(conn)


    # --------------------------------------------------
    # ポートフォリオ表示
    # --------------------------------------------------

    if args.portfolio:

        show_portfolio(conn)

        conn.close()
        return

    # --------------------------------------------------
    # 売買記録
    # --------------------------------------------------


    trade_action = None
    if args.buy is not None:
        trade_action = ("--buy", "購入", add_buy, args.buy)

    elif args.sell is not None:
        trade_action = ("--sell", "売却", add_sell, args.sell)

    if trade_action is not None:
        option, label, register, code = trade_action

        if args.shares is None or args.price is None:
            parser.error(
                     f"{option} には --shares と --price が必要です"
            )

        if conn.execute("SELECT 1 FROM equities_master WHERE Code = ?", (code,)).fetchone() is None:
            parser.error(f"銘柄コード {code}は銘柄リストに存在しません")

        if args.shares <= 0 or args.price < 0:
            parser.error(f"--sharesは正の整数、--priceは0以上を指定してください")

        date = args.date or datetime.now().date().isoformat()
        try:
            datetime.strptime(date, "%Y-%m-%d")

        except ValueError:
            parser.error(f"--dateは YYYY-MM-DD形式で指定してください")

        account_type = ACCOUNT_MAP[args.account]
        register(
            conn,
            code,
            account_type,
            args.shares,
            args.price,
            date
        )
        print(
            f"{code} を "
            f"{args.shares}株 "
            f"{args.price:,.2f}円で{label}として登録しました。"
        )
        print(f"口座       : {account_type}")
        print(f"取引日     : {date}")
        conn.close()
        return

    # --------------------------------------------------------
    # 銘柄コード
    # --------------------------------------------------------

    if args.code:
        show_stock(conn, args.code)
        conn.close()
        return


    # --------------------------------------------------------
    # 検索条件
    # --------------------------------------------------------

    conditions = []
    title_parts = []

    hide_market = False
    hide_scale = False


    # --------------------------------------------------------
    # TOPIX
    # --------------------------------------------------------

    if args.index:

        index_info = INDEX_MAP[args.index]
        scale_list = index_info["scale"]
        index_label = index_info["label"]

        conditions.append(
            ("ScaleCat", scale_list)
        )

        title_parts.append(
                f"指数: {index_label}"
        )
        hide_scale = True


    # --------------------------------------------------------
    # 市場
    # --------------------------------------------------------

    if args.market:

        market_name = MARKET_MAP[args.market]

        conditions.append(
            ("MktNm", market_name)
        )

        title_parts.append(
            f"市場: {market_name}"
        )

        hide_market = True


    # --------------------------------------------------------
    # 業種
    # --------------------------------------------------------

    if args.sector:

        conditions.append(
            ("S33Nm", args.sector)
        )

        title_parts.append(
            f"業種: {args.sector}"
        )


    # --------------------------------------------------------
    # 検索条件がある
    # --------------------------------------------------------

    if conditions:

        title = " / ".join(title_parts)

        show_list(
            title,
            conditions,
            hide_market=hide_market,
            hide_scale=hide_scale
        )
        conn.close()
        return


    # --------------------------------------------------------
    # オプションなし
    # → 日本取引所グループ
    # --------------------------------------------------------

    show_stock(conn, "86970")
    conn.close()



if __name__ == "__main__":
    main()

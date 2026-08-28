# PYTHON_ARGCOMPLETE_OK
import argparse
import sys
from datetime import date, datetime
from importlib.metadata import version
from zoneinfo import ZoneInfo

import argcomplete

from kabutam.db.connection import get_connection, require_master_data
from kabutam.db.portfolio import add_buy, add_sell, add_split
from kabutam.display.portfolio import show_portfolio, show_portfolio_csv
from kabutam.display.showinfo import show_stock
from kabutam.display.showlist import show_list
from kabutam.setup.fetch_edinet import fetch_and_save_edinet
from kabutam.setup.fetch_jquants import fetch_and_save_jquants

# CHECK_INTERVAL = timedelta(days=7)

JST = ZoneInfo("Asia/Tokyo")
# ------------------------------------------------------------
# 業種
# ------------------------------------------------------------
SECTOR_MAP = [
    "水産・農林業",
    "鉱業",
    "建設業",
    "食料品",
    "繊維製品",
    "パルプ・紙",
    "化学",
    "医薬品",
    "石油・石炭製品",
    "ゴム製品",
    "ガラス・土石製品",
    "鉄鋼",
    "非鉄金属",
    "金属製品",
    "機械",
    "電気機器",
    "輸送用機器",
    "精密機器",
    "その他製品",
    "電気・ガス業",
    "陸運業",
    "海運業",
    "空運業",
    "倉庫・運輸関連業",
    "情報・通信業",
    "卸売業",
    "小売業",
    "銀行業",
    "証券、商品先物取引業",
    "保険業",
    "その他金融業",
    "不動産業",
    "サービス業",
]

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

    except Exception as e:  # noqa: BLE001
        print(f"初期化中にエラーが発生しました: {e}")
        return False


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------


def main():

    parser = argparse.ArgumentParser(
        description="Kabutam 日本株検索 PF管理",
        formatter_class=lambda prog: argparse.HelpFormatter(
            prog, max_help_position=35, width=120
        ),
    )
    trade = parser.add_mutually_exclusive_group()
    portfolio_format = parser.add_mutually_exclusive_group()

    parser.add_argument(
        "--license", action="store_true", help="ライセンス情報を表示して終了する"
    )
    parser.add_argument(
        "--init", action="store_true", help="DBと初期データのセットアップを行う"
    )

    # --version を追加する
    parser.add_argument(
        "--version",
        action="version",
        version=(
            f"%(prog)s {version('kabutam')}\n"
            "Copyright (C) 2026 Tonrl\n"
            "License GPLv3+: GNU GPL version 3 or later\n"
            "<https://gnu.org/licenses/gpl.html>"
        ),
    )

    parser.add_argument("-C", "--code", help="銘柄コード")

    parser.add_argument("--full", dest="full", action="store_true", help="詳細情報表示")

    parser.add_argument(
        "--index",
        choices=INDEX_MAP.keys(),
        metavar="{core30, 100, 500,...}",
        help="TOPIX区分",
    )

    parser.add_argument(
        "--market",
        "--mk",
        choices=MARKET_MAP.keys(),
        metavar="{prime,standard,...}",
        help="市場",
    )

    parser.add_argument(
        "--sector",
        "--sec",
        choices=SECTOR_MAP,
        # metavar="{機械...}",
        metavar="SECTOR",
        help="33業種名",
    )

    parser.add_argument(
        "--portfolio", "--pf", action="store_true", help="ポートフォリオを表示"
    )
    parser.add_argument(
        "--sort",
        choices=["shares", "code"],
        default="shares",
        help="ポートフォリオの表示順: code=銘柄コード順 / shares=株数の多い順",
    )

    portfolio_format.add_argument(
        "--min",
        "--minimal",
        dest="minimal",
        action="store_true",
        help="ポートフォリオを簡易表示する",
    )
    portfolio_format.add_argument(
        "--doc",
        "--documents",
        dest="documents",
        action="store_true",
        help="保有銘柄の開示情報のみ表示する",
    )

    parser.add_argument("--td", action="store_true", help="TDnetのみ")

    parser.add_argument("--ed", action="store_true", help="EDINETのみ")

    portfolio_format.add_argument(
        "--csv",
        action="store_true",
        help="ポートフォリオをCSV形式で出力する",
    )

    trade.add_argument("--split", type=str, help="株式分割・併合")
    parser.add_argument("--ratio", type=float, help="株式分割・併合倍率（例: 2、0.5）")

    trade.add_argument("--buy", type=str, metavar="CODE", help="株式を購入")

    trade.add_argument("--sell", type=str, metavar="CODE", help="株式を売却")

    parser.add_argument("--shares", type=int, help="株数")

    parser.add_argument("--price", type=float, help="取得価格")

    parser.add_argument("--date", type=str, help="取引日 YYYY-MM-DD")

    parser.add_argument(
        "--account",
        choices=ACCOUNT_MAP.keys(),
        default="tokutei",
        help="口座区分: tokutei / nisa / ippan",
    )

    argcomplete.autocomplete(parser)
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
    if args.portfolio or args.minimal or args.csv or args.documents:
        if args.minimal:
            show_portfolio(conn, mode="minimal", sort_by=args.sort)
        elif args.documents:
            if args.td:
                show_portfolio(conn, mode="tdnet", sort_by=args.sort)
            elif args.ed:
                show_portfolio(conn, mode="edinet", sort_by=args.sort)
            else:
                show_portfolio(conn, mode="documents", sort_by=args.sort)

        elif args.csv:
            show_portfolio_csv(conn)

        else:
            show_portfolio(conn, mode="normal", sort_by=args.sort)

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
            parser.error(f"{option} には --shares と --price が必要です")

        if (
            conn.execute(
                "SELECT 1 FROM equities_master WHERE Code = ?", (code,)
            ).fetchone()
            is None
        ):
            parser.error(f"銘柄コード {code}は銘柄リストに存在しません")

        if args.shares <= 0 or args.price < 0:
            parser.error("--sharesは正の整数、--priceは0以上を指定してください")

        account_type = ACCOUNT_MAP[args.account]
        trade_date_str = args.date or datetime.now(JST).date().isoformat()

        try:
            trade_date = date.fromisoformat(trade_date_str)

        except ValueError:
            parser.error("--dateは YYYY-MM-DD形式で指定してください")

        if trade_date > datetime.now(JST).date():
            parser.error("--dateに未来の日付は指定できません")

        try:
            register(conn, code, account_type, args.shares, args.price, trade_date_str)
        except ValueError as e:
            conn.close()
            parser.error(str(e))

        print(
            f"{code} を "
            f"{args.shares}株 "
            f"{args.price:,.2f}円で{label}として登録しました。"
        )
        print(f"口座       : {account_type}")
        print(f"取引日     : {trade_date_str}")
        conn.close()
        return
    # --------------------------------------------------
    # 株式分割・併合
    # --------------------------------------------------

    if args.split is not None:
        if args.ratio is None:
            parser.error("--split には --ratio が必要です")

        if args.ratio <= 0:
            parser.error("--ratioは0より大きい値を指定してください")

        if args.ratio == 1:
            parser.error("--ratioに1は指定できません")

        if args.shares is not None or args.price is not None:
            parser.error("--splitでは --shares と --price は指定できません")

        code = args.split

        if (
            conn.execute(
                "SELECT 1 FROM equities_master WHERE Code = ?", (code,)
            ).fetchone()
            is None
        ):
            parser.error(f"銘柄コード {code}は銘柄リストに存在しません")

        trade_date_str = args.date or datetime.now(JST).date().isoformat()

        try:
            trade_date = date.fromisoformat(trade_date_str)

        except ValueError:
            parser.error("--dateは YYYY-MM-DD形式で指定してください")

        if trade_date > datetime.now(JST).date():
            parser.error("--dateに未来の日付は指定できません")

        try:
            add_split(conn, code, args.ratio, trade_date_str)

        except ValueError as e:
            conn.close()
            parser.error(str(e))

        if args.ratio > 1:
            event = f"{args.ratio:g}倍の株式分割"
        elif args.ratio < 1:
            event = f"{1 / args.ratio:g}:1の株式併合"
        else:
            event = "株式分割・併合なし"

        print(f"{code} の {event}を登録しました。")
        print(f"倍率       : {args.ratio:g}")
        print(f"適用日     : {trade_date_str}")

        conn.close()
        return
    # --------------------------------------------------------
    # 銘柄コード
    # --------------------------------------------------------

    if args.code:
        if args.full:
            mode = "normal"
        else:
            mode = "short"

        show_stock(conn, args.code, mode)
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

        conditions.append(("ScaleCat", scale_list))

        title_parts.append(f"指数: {index_label}")
        hide_scale = True

    # --------------------------------------------------------
    # 市場
    # --------------------------------------------------------

    if args.market:
        market_name = MARKET_MAP[args.market]

        conditions.append(("MktNm", market_name))

        title_parts.append(f"市場: {market_name}")

        hide_market = True

    # --------------------------------------------------------
    # 業種
    # --------------------------------------------------------

    if args.sector:
        conditions.append(("S33Nm", args.sector))

        title_parts.append(f"業種: {args.sector}")

    # --------------------------------------------------------
    # 検索条件がある
    # --------------------------------------------------------

    if conditions:
        title = " / ".join(title_parts)

        show_list(
            conn, title, conditions, hide_market=hide_market, hide_scale=hide_scale
        )
        conn.close()
        return

    # --------------------------------------------------------
    # オプションなし
    # → 日本取引所グループ
    # --------------------------------------------------------

    show_stock(conn, "86970", mode="normal")
    conn.close()


if __name__ == "__main__":
    main()

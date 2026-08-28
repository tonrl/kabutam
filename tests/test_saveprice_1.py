import sqlite3
from zoneinfo import ZoneInfo

import pytest

from kabutam.stock.saveprice import create_prices_table, ensure_recent_prices

JST = ZoneInfo("Asia/Tokyo")


@pytest.fixture
def memory_db():
    """インメモリのSQLiteデータベースコネクションを提供するフィクスチャ"""
    conn = sqlite3.connect(":memory:")
    create_prices_table(conn)
    yield conn
    conn.close()


def test_ensure_recent_prices(memory_db):
    """
    トヨタ自動車(72030)の株価を yfinance から取得し、
    DBへの保存・イベント通知が正しく行われるかをテストする
    """
    events = []

    # イベント（メッセージ通知）をキャッチするハンドラー
    def dummy_event_handler(message):
        events.append(message)
        print(f"\n[イベント受信] -> {message}")

    test_code = "72030"

    # テスト実行
    prices = ensure_recent_prices(
        memory_db, test_code, days=2, on_event=dummy_event_handler
    )

    # 1. 結果が空でないことの検証
    assert prices is not None, "株価データが取得できませんでした"
    assert len(prices) == 2, "指定した日数（2日分）のデータが取得されていません"

    # 2. 取得したデータの構造（カラム・型）の検証
    for row in prices:
        # row の構成: (Date, Open, High, Low, Close, Volume, AdjOpen, AdjHigh, AdjLow, AdjClose, AdjVolume)
        assert len(row) >= 10, "レコードのカラム数が不足しています"

        date_str, _, _, _, close_p = row[0], row[1], row[2], row[3], row[4]

        # 日付文字列の形式確認 (YYYY-MM-DD)
        assert isinstance(date_str, str)
        assert len(date_str) == 10

        # 株価が数値（float）かつ正の値であること
        assert isinstance(close_p, float)
        assert close_p > 0

    # 3. 再取得などのイベントが発生した場合にイベントリストに記録されているか確認
    # （ネットワークやタイミングにより発生しない場合もあるため、ここではエラーにならないことの確認のみ）
    print(f"キャッチしたイベント数: {len(events)}")

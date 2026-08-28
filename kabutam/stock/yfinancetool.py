from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

JST = ZoneInfo("Asia/Tokyo")


def make_yahoo_ticker(code):
    code = str(code)

    if len(code) == 5 and code.endswith("0"):
        code = code[:-1]

    return f"{code}.T"


def fetch_prices(code, days=3, before_today=False, on_event=None):

    ticker = make_yahoo_ticker(code)

    stock = yf.Ticker(ticker)

    # 休日を考慮して少し余裕を持たせる
    try:
        df = stock.history(period="14d", interval="1d", auto_adjust=False)
    except Exception as e:  # noqa: BLE001
        if on_event:
            on_event(f" {code}: 株価取得エラー: {e}")
        return []

    if df.empty:
        if on_event:
            on_event(f" {code}: 株価データを取得できませんでした")

        return []
    # --------------------------------------------------
    # 今日のデータを除外
    # --------------------------------------------------

    if before_today:
        today = datetime.now(JST).date()

        df = df[df.index.date < today]

    if not df.empty:
        latest_row = df.iloc[-1]
        if latest_row["Close"] != latest_row["Close"]:
            latest_date = df.index[-1].date()

            # 再取得
            if on_event:
                on_event(f" {code}: {latest_date} の終値を再取得しています...")

            retry = stock.history(
                start=latest_date,
                end=latest_date + timedelta(days=1),
                interval="1d",
                auto_adjust=False,
            )
            # 再取得結果
            if not retry.empty:
                retry_close = retry.iloc[-1]["Close"]

                # 再取得成功
                if pd.notna(retry_close):
                    df.loc[df.index[-1], "Close"] = retry_close
                    df.loc[df.index[-1], "Adj Close"] = retry.iloc[-1]["Adj Close"]

                    if on_event:
                        on_event(f" {code}: {latest_date} の終値を再取得しました")
            else:
                if on_event:
                    on_event(f" {code}: {latest_date} の終値を再取得できませんでした")

    df = df[df["Close"].notna()]
    df = df.sort_index().tail(days)

    records = []

    for index, row in df.iterrows():
        # if row["Close"] is None or row["Close"] != row["Close"]:
        #     continue

        date = index.strftime("%Y-%m-%d")

        records.append(
            {
                "Date": date,
                "Code": str(code),
                "Open": row["Open"],
                "High": row["High"],
                "Low": row["Low"],
                "Close": row["Close"],
                "Volume": row["Volume"],
                "AdjOpen": row["Open"],
                "AdjHigh": row["High"],
                "AdjLow": row["Low"],
                "AdjClose": row["Adj Close"],
                "AdjVolume": row["Volume"],
            }
        )

    return records

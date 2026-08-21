import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

def make_yahoo_ticker(code):
    code = str(code)

    if len(code) == 5 and code.endswith("0"):
        code = code[:-1]

    return f"{code}.T"


def fetch_prices(code, days=3, before_today=False):

    ticker = make_yahoo_ticker(code)

    stock = yf.Ticker(ticker)

    # 休日を考慮して少し余裕を持たせる
    df = stock.history(
        period="14d",
        interval="1d",
        auto_adjust=False
    )


    if df.empty:
        print(f"[yfinance] {ticker}: データが空です")
        return []
    # --------------------------------------------------
    # 今日のデータを除外
    # --------------------------------------------------

    if before_today:
        today = datetime.now(JST).date()

        df = df[
            df.index.date < today
        ]
    df = df[df["Close"].notna()]
    df = df.tail(days)

    records = []

    for index, row in df.iterrows():
        # if row["Close"] is None or row["Close"] != row["Close"]:
        #     continue

        date = index.strftime("%Y-%m-%d")

        records.append({
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
        })

    return records

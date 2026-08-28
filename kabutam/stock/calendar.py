from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from kabutam.stock.saveprice import is_trading_day

JST = ZoneInfo("Asia/Tokyo")
DATA_UPDATE_TIME_MIN = time(9, 00)


def get_recent_trading_days(n, base_date=None):
    """
    今日から遡って、土日祝日（非営業日）をスキップし、
    指定した営業日数分の 'YYYY-MM-DD' 文字列のリストを返す。
    """
    now = datetime.now(JST)
    if base_date is None:
        base_date = datetime.now(JST).date()
        if now.time() < DATA_UPDATE_TIME_MIN:
            base_date -= timedelta(days=1)

    current = base_date
    trading_days = []

    while len(trading_days) < n:
        if is_trading_day(current):
            trading_days.append(current.strftime("%Y-%m-%d"))
        current -= timedelta(days=1)

    return trading_days

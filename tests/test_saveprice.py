from datetime import datetime
from kabutam.stock.saveprice import expected_latest_close_date


def test_expected_latest_close_date_before_1630():
    now = datetime(2026, 8, 21, 15, 0)

    result = expected_latest_close_date(now)

    assert result.isoformat() == "2026-08-20"


def test_expected_latest_close_date_after_1630():
    now = datetime(2026, 8, 21, 17, 0)

    result = expected_latest_close_date(now)

    assert result.isoformat() == "2026-08-21"

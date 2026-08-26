from kabutam.db.schema import create_table_corp_data
from kabutam.db.connection import require_edi_data
from kabutam.stock.saveprice import ensure_recent_prices
from kabutam.edinet.get_corpdata import get_corpdata

# ------------------------------------------------------------
# 銘柄コード検索
# ------------------------------------------------------------
def get_stock_info(conn, code, message_ref=None):
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
        return None

    edinetdata = conn.execute("""
        SELECT 
            EDINETCode,
            ListingStatus 
        FROM edinet_master 
        WHERE Code = ? 
    """, (code,)).fetchone()

    if message_ref:
        message_ref[0] = " 株価情報を取得しています"

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
    if message_ref:
        message_ref[0] = "財務情報を確認しています"

    corpdata = None
    if edinetcode is not None:
        if not require_edi_data(conn):
            create_table_corp_data(conn)

        corpdata = get_corpdata(conn, edinetcode, message_ref)
    
    return {
        "company": {
            "code": code,
            "name": name,
            "name_en": name_en,
            "sector17": sector17,
            "sector33": sector33,
            "scale": scale,
            "market": market,
        },

        "edinet": {
            "code": edinetcode,
            "listing_status": listing_status,
        },

        "prices": prices,
        "latest_price": latest_price,
        "corpdata": corpdata,
    }


from kabutam.db.connection import (
        get_connection,
        require_master_data
)
from kabutam.display.terminal import fit_text

# ------------------------------------------------------------
# 銘柄一覧
# ------------------------------------------------------------

def show_list(
    title,
    conditions,
    hide_market=False,
    hide_scale=False
):
    conn = get_connection()
    require_master_data(conn)


    where = []
    params = []

    # for column, value in conditions:
    #     where.append(f"{column} = ?")
    #     params.append(value)
    for column, value in conditions:
        if isinstance(value, list):
            placeholders = ",".join(["?"] * len(value))
            where.append(f"{column} IN ({placeholders})")
            params.extend(value)
        else:
            where.append(f"{column} = ?")
            params.append(value)

    query = f"""
        SELECT
            Code,
            CoName,
            S33Nm,
            MktNm,
            ScaleCat
        FROM equities_master
        WHERE {" AND ".join(where)}
        ORDER BY Code
    """

    companies = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    if not companies:
        print(f"{title} に該当する銘柄がありません。")
        return

    print("=" * 80)
    print(f"{title} — {len(companies)}銘柄")
    print("=" * 80)

    # ヘッダー
    header = (
        f"{'Code':<8}"
        f"{fit_text('Company', 30)}"
    )

    if not hide_market:
        header += fit_text("Market", 12)

    if not hide_scale:
        header += fit_text("TOPIX", 15)

    header += fit_text("Industry", 20)

    print(header)
    print("-" * 80)

    for code, name, sector, market, scale in companies:

        line = (
            f"{code:<8}"
            f"{fit_text(name, 31)}"
        )

        if not hide_market:
            line += fit_text(market, 12)

        if not hide_scale:
            line += fit_text(scale, 15)

        line += fit_text(sector, 20)

        print(line)



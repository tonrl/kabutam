from kabutam.db.schema import create_table_watchlist


def add_watchlist(conn, code):
    create_table_watchlist(conn)
    code = str(code).strip()

    if not code:
        return False, "銘柄コードが指定されていません。"

    row = conn.execute(
        """
        SELECT Code
        FROM equities_master
        WHERE Code = ?
        """,
        (code,),
    ).fetchone()

    if not row:
        return False

    existing = conn.execute(
        """
        SELECT Code
        FROM watchlist
        WHERE Code = ?
        """,
        (code,),
    ).fetchone()

    if existing:
        return None

    conn.execute(
        """
        INSERT INTO watchlist (Code)
        VALUES (?)
        """,
        (code,),
    )
    conn.commit()

    return True, f"{code} を登録しました。"


def remove_watchlist(conn, code):
    create_table_watchlist(conn)
    code = str(code).strip()

    cursor = conn.execute(
        """
        DELETE FROM watchlist
        WHERE Code = ?
        """,
        (code,),
    )
    conn.commit()

    return cursor.rowcount > 0


def get_watchlist(conn):
    create_table_watchlist(conn)
    rows = conn.execute(
        """
        SELECT Code
        FROM watchlist
        ORDER BY Code
        """
    ).fetchall()

    return [row[0] for row in rows]

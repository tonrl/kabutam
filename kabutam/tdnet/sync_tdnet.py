import time
from datetime import datetime, timedelta

from kabutam.tdnet.client import search_tdnet_doc_list_data
from kabutam.db.schema import create_table_tdnet_disclosure
from kabutam.stock.saveprice import is_trading_day

TDNET_DAYS_TO_CHECK = 15
TDNET_RECENT_DAYS = 2
TDNET_SYNC_INTERVAL_HOURS = 3
TDNET_SYNC_STATUS_RETENTION_DAYS = 30

def get_recent_trading_days(n=TDNET_DAYS_TO_CHECK, base_date=None):
    """
    今日から遡って、土日祝日（非営業日）をスキップし、
    指定した営業日数分の 'YYYY-MM-DD' 文字列のリストを返す。
    """
    if base_date is None:
        base_date = datetime.now().date()

    current = base_date
    trading_days = []

    while len(trading_days) < n:
        if is_trading_day(current):
            trading_days.append(current.strftime("%Y-%m-%d"))
        current -= timedelta(days=1)

    return trading_days

def sync_recent_tdnet(conn, message_ref=None):
    create_table_tdnet_disclosure(conn)

    # 今日・昨日
    target_dates = get_recent_trading_days(n=TDNET_DAYS_TO_CHECK)

    total_inserted = 0

    for index, date_str in enumerate(target_dates):

        # 今日・昨日だけ定期チェック
        if index < TDNET_RECENT_DAYS:

            if not should_sync_tdnet(conn, date_str, interval_hours=TDNET_SYNC_INTERVAL_HOURS):
                continue

            completed = False

        else:

            # 3日以上前なら同期済みなら無視
            row = conn.execute("""
                SELECT completed
                FROM tdnet_sync_status
                WHERE target_date = ?
            """, (date_str,)).fetchone()

            if row is not None and row[0] == 1:
                continue

            completed = True

        # TDNET 取得
        saved_count = sync_tdnet_doc_list(
            conn,
            date_str=date_str,
            message_ref=message_ref,
            completed=completed,
        )

        total_inserted += saved_count

        time.sleep(1)

    # 古い同期情報削除
    cleanup_tdnet_sync_status(
        conn,
        keep_days=TDNET_SYNC_STATUS_RETENTION_DAYS
    )
    return total_inserted

def should_sync_tdnet(conn, date_str, interval_hours=TDNET_SYNC_INTERVAL_HOURS):

    row = conn.execute("""
        SELECT last_checked_at
        FROM tdnet_sync_status
        WHERE target_date = ?
    """, (date_str,)).fetchone()

    if row is None:
        return True

    if row[0] is None:
        return True

    last_checked = datetime.strptime(
        row[0],
        "%Y-%m-%d %H:%M:%S"
    )

    elapsed = datetime.now() - last_checked

    return elapsed >= timedelta(hours=interval_hours)


def update_tdnet_sync_status(conn, date_str, document_count, completed=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    completed_at = now if completed else None

    conn.execute("""
        INSERT INTO tdnet_sync_status (
            target_date,
            document_count,
            last_checked_at,
            completed,
            completed_at
        )
        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(target_date)
        DO UPDATE SET
            document_count = excluded.document_count,
            last_checked_at = excluded.last_checked_at,
            completed = excluded.completed,
            completed_at = excluded.completed_at
    """, (
        date_str,
        document_count,
        now,
        int(completed),
        completed_at,
    ))

    conn.commit()

def sync_tdnet_doc_list(conn, date_str=None, message_ref=None, completed=False):
    # 指定日のTDnet開示情報を取得してDBに保存する。

    create_table_tdnet_disclosure(conn)

    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # TDnetから取得
    if message_ref is not None:
        message_ref[0] = (
            f"TDnet [{date_str}] の開示情報を取得しています..."
        )

    documents = search_tdnet_doc_list_data(date_str)

    if documents is None:
        if message_ref is not None:
            message_ref[0] = (
                f"TDnet [{date_str}] の取得に失敗しました。"
            )
        return 0

    if not documents:
        update_tdnet_sync_status(
                conn=conn,
                date_str=date_str,
                document_count=0,
                completed=completed,
        )
        if message_ref is not None:
            message_ref[0] = (
                f"TDnet [{date_str}] の開示情報はありませんでした。"
            )
        return 0

    # DBへ保存
    saved_count = save_tdnet_doc_list(conn, documents)

    # --------------------------------------------------
    # 同期状態更新
    # --------------------------------------------------

    update_tdnet_sync_status(
        conn=conn,
        date_str=date_str,
        document_count=len(documents),
        completed=completed,
    )

    if message_ref is not None:
        message_ref[0] = (
            f"TDnet [{date_str}] "
            f"{saved_count}件の新規開示を保存しました。"
        )

    return saved_count


def save_tdnet_doc_list(conn, documents):

    if not documents:
        return 0

    inserted_count = 0

    for doc in documents:

        pdf_url = doc["pdf_url"]

        try:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO tdnet_disclosure (
                    disclosure_id,
                    disclosure_date,
                    disclosure_time,
                    sec_code,
                    company_name,
                    title,
                    pdf_url,
                    market
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pdf_url,
                doc["disclosure_date"],
                doc["disclosure_time"],
                doc["sec_code"],
                doc["company_name"],
                doc["title"],
                pdf_url,
                doc["market"],
            ))

            if cursor.rowcount == 1:
                inserted_count += 1

        except Exception as e:
            print(
                f"Error saving TDnet document "
                f"{pdf_url}: {e}"
            )

    conn.commit()

    return inserted_count

def cleanup_tdnet_sync_status(conn, keep_days):
    conn.execute("""
        DELETE FROM tdnet_sync_status
        WHERE target_date < date('now', ?)
    """, (f"-{keep_days} days",))

    conn.commit()

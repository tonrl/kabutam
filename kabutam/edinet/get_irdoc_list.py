import sqlite3
import time as time_tool
from datetime import UTC, datetime, timedelta

from kabutam.db.schema import create_table_edinet_doc_list
from kabutam.edinet.client import search_edinet_doc_list_data
from kabutam.stock.calendar import get_recent_trading_days

EDINET_DAYS_TO_CHECK = 15
EDINET_DOCUMENT_RETENTION_DAYS = 365 * 3
EDINET_SYNC_STATUS_RETENTION_DAYS = 50
EDINET_RECENT_CHECK_INTERVAL_HOURS = 3
REQUEST_INTERVAL = 1.0


def should_sync_edinet_data(conn, target_date, interval_hours=3):

    row = conn.execute(
        """
        SELECT last_checked_at, completed
        FROM edinet_sync_status
        WHERE target_date = ?
    """,
        (target_date,),
    ).fetchone()

    # 一度もチェックしていない
    if row is None:
        return True

    last_checked_at, completed = row

    if completed:
        return False

    if last_checked_at is None:
        return True

    try:
        last_checked = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=UTC
        )
    except ValueError:
        # 日時が壊れていた場合は念のため再チェック
        return True

    elapsed = datetime.now(UTC) - last_checked
    return elapsed >= timedelta(hours=interval_hours)


def sync_recent_edinet_doc_list(
    conn, days_to_check=EDINET_DAYS_TO_CHECK, message_ref=None, on_event=None
):

    create_table_edinet_doc_list(conn)
    if message_ref is not None:
        message_ref[0] = " EDINET書類リストの同期状況を確認しています..."

    target_dates = get_recent_trading_days(n=days_to_check)
    total_inserted = 0

    for index, date_str in enumerate(target_dates):
        # ----------------------------------------

        is_recent = index < 2

        if not should_sync_edinet_data(
            conn, date_str, EDINET_RECENT_CHECK_INTERVAL_HOURS
        ):
            continue

        if message_ref is not None:
            message_ref[0] = f" [{date_str}] の書類リストを取得しています..."

        response_json = search_edinet_doc_list_data(date_str)

        if response_json is None:
            if message_ref is not None:
                message_ref[0] = f" [{date_str}] 取得に失敗しました。スキップします。"
            time_tool.sleep(1.5)
            continue

        documents = response_json.get("results", [])
        if not documents:
            if message_ref is not None:
                message_ref[0] = f" [{date_str}] この日は開示書類がありませんでした。"
            continue

        saved_count = save_edinet_doc_list(conn, response_json)
        if message_ref is not None:
            message_ref[0] = (
                f" [{date_str}] {saved_count}件の書類リストを保存しました。"
            )

        total_inserted += saved_count
        # 最大seqNumber
        seq_numbers = [
            doc.get("seqNumber")
            for doc in documents
            if doc.get("seqNumber") is not None
        ]
        max_seq_number = max(seq_numbers) if seq_numbers else None

        # 同期状態
        update_edinet_sync_status(
            conn=conn,
            target_date=date_str,
            last_seq_number=max_seq_number,
            document_count=len(documents),
            completed=not is_recent,
        )
    if index < len(target_dates) - 1:
        time_tool.sleep(REQUEST_INTERVAL)

    cleanup_edinet_sync_status(conn, keep_days=EDINET_SYNC_STATUS_RETENTION_DAYS)
    if message_ref is not None:
        message_ref[0] = f" (新規{total_inserted}件)書類リストの同期が完了しました。"


def save_edinet_doc_list(conn, api_response_json):
    """
    EDINET APIのレスポンス（json）を受け取り、
    edinet_doc_list テーブルに新規分を保存する
    """
    # レスポンスから resultsを取り出す
    documents = api_response_json.get("results", [])
    if not documents:
        print("保存するドキュメントが見つかりませんでした。")
        return

    inserted_count = 0

    for doc in documents:
        document_id = doc.get("docID")
        edinet_code = doc.get("edinetCode")
        doc_description = doc.get("docDescription")
        submit_datetime = doc.get("submitDateTime")
        pdf_flag = doc.get("pdfFlag")

        if not edinet_code or not document_id:
            continue

        try:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO edinet_doc_list (
                    document_id,
                    EDINETCode,
                    doc_description,
                    submit_datetime,
                    pdf_flag
                ) VALUES (?, ?, ?, ?, ?)
            """,
                (document_id, edinet_code, doc_description, submit_datetime, pdf_flag),
            )
            if cursor.rowcount == 1:
                inserted_count += 1

        except sqlite3.Error as e:
            print(f"Error saving document_id {document_id}: {e}")

    conn.commit()
    return inserted_count


def update_edinet_sync_status(
    conn, target_date, last_seq_number, document_count, completed
):
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    completed_at = now if completed else None

    conn.execute(
        """
        INSERT INTO edinet_sync_status (
            target_date,
            last_seq_number,
            document_count,
            last_checked_at,
            completed,
            completed_at
        )
        VALUES (?, ?, ?, ?, ?, ?)

        ON CONFLICT(target_date)
        DO UPDATE SET
            last_seq_number = excluded.last_seq_number,
            document_count = excluded.document_count,
            last_checked_at = excluded.last_checked_at,
            completed = excluded.completed,
            completed_at = excluded.completed_at
    """,
        (
            target_date,
            last_seq_number,
            document_count,
            now,
            int(completed),
            completed_at,
        ),
    )

    conn.commit()


def cleanup_edinet_sync_status(conn, keep_days):
    # Delete older than 60 days
    conn.execute(
        """
        DELETE FROM edinet_sync_status
        WHERE target_date < date('now', ?)
    """,
        (f"-{keep_days} days",),
    )

    conn.commit()

import subprocess
import requests
from datetime import datetime
from kabutam.db.connection import get_connection

BASE_URL = "https://edinetdb.jp/v1/search"

def create_edinet_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS edinet_master (
            Code TEXT PRIMARY KEY,
            EDINETCode TEXT,
            CompanyName TEXT,
            ListingStatus TEXT,
            UpdatedAt TEXT
        )
    """)

def search_edinet(code):
    params = {"q": code}
    # resp = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()

def fetch_and_save_edinet():
    print("EDINET DB から対照表の作成を開始します...")

    conn = get_connection()
    create_edinet_table(conn)

    codes = conn.execute("""
        SELECT Code
        FROM equities_master
        WHERE MktNm IN (
            'プライム',
            'スタンダード',
            'グロース'
        )
        ORDER BY Code
    """).fetchall()

    print(f"対象銘柄数: {len(codes)} 件")

    for (code,) in codes:
        exists = conn.execute("""
            SELECT 1 FROM edinet_master WHERE Code = ?
        """, (code,)).fetchone()

        if exists:
            continue

        print(f"Searching {code} ...")
        try:
            result = search_edinet(code)
            data = result.get("data", [])

            if not data:
                print("  -> not found")
                conn.execute("""
                    INSERT INTO edinet_master (Code, UpdatedAt)
                    VALUES (?, ?)
                """, (code, datetime.now().isoformat(timespec="seconds")))
                conn.commit()
                continue

            row = data[0]
            conn.execute("""
                INSERT OR REPLACE INTO edinet_master (
                    Code, EDINETCode, CompanyName, ListingStatus, UpdatedAt
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                code,
                row.get("edinet_code"),
                row.get("name"),
                row.get("listing_status"),
                datetime.now().isoformat(timespec="seconds")
            ))
            conn.commit()
            print(f"  -> {row.get('edinet_code')} {row.get('name')}")

        except requests.HTTPError as e:
            if e.response.status_code == 429:
                print("429 Too Many Requests: レートリミットに達しました。")
                break
            print(f"  -> HTTP error: {e}")
            break
        except requests.RequestException as e:
            print(f"  -> request error: {e}")
            break

    conn.close()
    print("EDINET対照表の作成が完了しました。")

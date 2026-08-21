import subprocess
import requests
from kabutam.db.connection import get_connection

def fetch_and_save_jquants():
    print("J-Quants から銘柄マスタを取得しています...")
    
    # passからJ-Quants APIキーを取得
    JPX_API_KEY = subprocess.check_output(
        ["pass", "show", "jpx-jquants.com/api/JPX_JQUANTS_API_KEY"],
        text=True
    ).splitlines()[0]
    print(f"J-Quants: 銘柄データを取得しています。")


    URL = "https://api.jquants.com/v2/equities/master"

    headers = {"x-api-key": JPX_API_KEY}

    resp = requests.get(URL, headers=headers)
    resp.raise_for_status()

    data = resp.json()["data"]

    # XDG対応のパスを利用
    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS equities_master (
        Code TEXT PRIMARY KEY,
        CoName TEXT,
        CoNameEn TEXT,
        S17 TEXT,
        S17Nm TEXT,
        S33 TEXT,
        S33Nm TEXT,
        ScaleCat TEXT,
        Mkt TEXT,
        MktNm TEXT,
        Mrgn TEXT,
        MrgnNm TEXT,
        ProdCat TEXT
    )
    """)

    conn.executemany("""
    INSERT OR REPLACE INTO equities_master (
        Code, CoName, CoNameEn, S17, S17Nm, S33, S33Nm, ScaleCat, Mkt, MktNm, Mrgn, MrgnNm, ProdCat
    )
    VALUES (
        :Code, :CoName, :CoNameEn, :S17, :S17Nm, :S33, :S33Nm, :ScaleCat, :Mkt, :MktNm, :Mrgn, :MrgnNm, :ProdCat
    )
    """, data)

    conn.commit()
    conn.close()

    print(f"J-Quants: {len(data)} 銘柄の保存が完了しました。")

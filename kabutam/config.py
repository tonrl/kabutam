# config.py

import subprocess


def get_edinet_api_key():
    try:
        result = subprocess.run(
            ["pass", "show", "ednetdb/api/EDNET_DB_API_KEY"],
            capture_output=True,
            text=True,
            check=True
        )

        key = result.stdout.splitlines()[0].strip()

        if not key:
            raise RuntimeError("EDINET DB APIキーが空です。")

        return key

    except subprocess.CalledProcessError:
        raise RuntimeError(
            "EDINET DB APIキーを取得できませんでした。"
            "pass/GPGの認証を確認してください。"
        )

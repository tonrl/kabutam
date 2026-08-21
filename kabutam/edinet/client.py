import requests
from kabutam.config import get_edinet_api_key

BASE_URL = "https://edinetdb.jp/v1/companies"


def search_edinet_data(edinet_code):

    # API key 確認
    EDNET_DB_API_KEY = get_edinet_api_key()

    if not EDNET_DB_API_KEY:
        print("Error: EDINET DB API key is empty")
        return None

    HEADERS = {
            "X-API-Key": EDNET_DB_API_KEY
    }

    url = f"{BASE_URL}/{edinet_code}"

    try:
        resp = requests.get(
                url,
                headers=HEADERS,
                timeout=30
        )

        resp.raise_for_status()
        return resp.json()

    except requests.Timeout: 
        print("エラー: EDINET DB APIへの接続がタイムアウトしました。") 
        return None

    except requests.ConnectionError as e:
        print(f"エラー: EDINET DB APIへ接続できませんでした: {e}")
        return None

    except requests.HTTPError as e:
        print(f"エラー: EDINET DB APIがHTTPエラーを返しました: {e}")

        try:
            error_data = resp.json()
            print(f"API response: {error_data}") 
        except ValueError:
            pass
        return None

    except ValueError: 
        print("エラー: EDINET DB APIのレスポンスをJSONとして解析できませんでした。") 
        return None 

    except requests.RequestException as e: 
        print(f"エラー: EDINET DB API通信エラー: {e}") 
        return None


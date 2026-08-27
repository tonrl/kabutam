import requests
from kabutam.config import (get_edinet_api_key, get_edinet_fsa_api_key)

EDINET_DB_BASE_URL = "https://edinetdb.jp/v1"
EDINET_FSA_BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"


def search_edinet_data(edinet_code):

    # API key 確認
    EDINET_DB_API_KEY = get_edinet_api_key()

    if not EDINET_DB_API_KEY:
        print("Error: EDINET DB API key is empty")
        return None

    HEADERS = {
            "X-API-Key": EDINET_DB_API_KEY
    }

    url = f"{EDINET_DB_BASE_URL}/companies/{edinet_code}"

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


def search_edinet_doc_list_data(date_str):

    # API key 確認
    EDINET_FSA_API_KEY = get_edinet_fsa_api_key()

    if not EDINET_FSA_API_KEY:
        print("Error: EDINET FSA API key is empty")
        return None

    HEADERS = {
            "Ocp-Apim-Subscription-Key": EDINET_FSA_API_KEY
    }

    url = f"{EDINET_FSA_BASE_URL}/documents.json"

    params = {
            "date": date_str,
            "type": 2
    }

    try:
        resp = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=30
        )

        resp.raise_for_status()
        return resp.json()

    except requests.Timeout:
        print("エラー: EDINET FSA APIへの接続がタイムアウトしました。")
        return None

    except requests.ConnectionError as e:
        print(f"エラー: EDINET FSA APIへ接続できませんでした: {e}")
        return None

    except requests.HTTPError as e:
        print(f"エラー: EDINET FSA APIがHTTPエラーを返しました: {e}")

        try:
            error_data = resp.json()
            print(f"API response: {error_data}")
        except ValueError:
            pass
        return None

    except ValueError:
        print("エラー: EDINET FSA APIのレスポンスをJSONとして解析できませんでした。")
        return None

    except requests.RequestException as e:
        print(f"エラー: EDINET FSA API通信エラー: {e}")
        return None

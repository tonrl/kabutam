import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


TDNET_BASE_URL = "https://www.release.tdnet.info/inbs/"


def search_tdnet_doc_list_data(date_str):
    """
    指定日のTDnet適時開示一覧を取得する。

    date_str:
        YYYY-MM-DD

    return:
        [
            {
                "disclosure_date": "2026-08-27",
                "disclosure_time": "18:30",
                "sec_code": "14310",
                "company_name": "Ｇ－リブワーク",
                "title": "定款の一部変更に関するお知らせ",
                "pdf_url": "...",
            },
            ...
        ]
    """

    date_compact = date_str.replace("-", "")

    all_documents = []
    page = 1

    while True:

        url = (
            f"{TDNET_BASE_URL}"
            f"I_list_{page:03d}_{date_compact}.html"
        )

        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            break

        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")

        rows = soup.select("#main-list-table tr")

        if not rows:
            break

        for row in rows:

            time_cell = row.select_one(".kjTime")
            code_cell = row.select_one(".kjCode")
            name_cell = row.select_one(".kjName")
            title_cell = row.select_one(".kjTitle")
            place_cell = row.select_one(".kjPlace")

            if not all([
                time_cell,
                code_cell,
                name_cell,
                title_cell,
            ]):
                continue

            link = title_cell.find("a")

            if link is None:
                continue

            disclosure_time = time_cell.get_text(strip=True)
            sec_code = code_cell.get_text(strip=True)
            company_name = name_cell.get_text(strip=True)
            title = title_cell.get_text(strip=True)
            pdf_url = urljoin(url, link.get("href"))

            all_documents.append({
                "disclosure_date": date_str,
                "disclosure_time": disclosure_time,
                "sec_code": sec_code,
                "company_name": company_name,
                "title": title,
                "pdf_url": pdf_url,
                "market": (
                    place_cell.get_text(strip=True)
                    if place_cell else None
                ),
            })

        # 次ページが存在するか
        next_page = soup.select_one(
            f'[onClick*="I_list_{page + 1:03d}_{date_compact}.html"]'
        )

        if next_page is None:
            break

        page += 1

    return all_documents

# kabutam/ai/insights.py

from collections import defaultdict
from typing import Any

from kabutam.ai.schemas import PortfolioAnalysisInput


# SECTOR_CONCENTRATION_THRESHOLD = 50.0
SECTOR_CONCENTRATION_HIGH = 40.0
SECTOR_CONCENTRATION_MEDIUM = 20.0
MAX_HOLDINGS_PER_GROUP = 5


def holding_name(
    holding: dict[str, Any] | None,
) -> str | None:
    """保有銘柄から表示用の銘柄名を取得する。"""

    if holding is None:
        return None

    return holding.get("company_name") or holding.get("code")

def unique_holding_names(
    holdings: list[dict[str, Any]],
    limit: int = MAX_HOLDINGS_PER_GROUP,
) -> list[str]:
    """銘柄名の重複を除去し、最大件数まで返す。"""

    names: list[str] = []
    seen: set[str] = set()

    for holding in holdings:
        name = holding_name(holding)

        if not name or name in seen:
            continue

        names.append(name)
        seen.add(name)

        if len(names) >= limit:
            break

    return names

def direction(value: float | None) -> str:
    """損益や変化量を日本語の方向に変換する。"""

    if value is None:
        return "データなし"

    if value > 0:
        return "増加"

    if value < 0:
        return "減少"

    return "変化なし"


def profit_status(value: float | None) -> str:
    """損益を評価益・評価損などに変換する。"""

    if value is None:
        return "データなし"

    if value > 0:
        return "評価益"

    if value < 0:
        return "評価損"

    return "損益なし"


def dividend_status(value: float | None) -> str:
    """配当収入の有無を判定する。"""

    if value is None:
        return "データなし"

    if value > 0:
        return "配当収入あり"

    return "配当収入なし"


def build_summary_insight(
    summary: dict[str, Any],
) -> dict[str, Any]:
    """ポートフォリオ全体の状態を文章化しやすい情報へ変換する。"""

    return {
        "evaluation_status": profit_status(
            summary.get("unrealised_profit")
        ),
        "daily_change": direction(
            summary.get("daily_profit")
        ),
        "monthly_change": direction(
            summary.get("monthly_profit")
        ),
        "three_month_change": direction(
            summary.get("three_month_profit")
        ),
        "dividend_status": dividend_status(
            summary.get("total_dividend_post_tax")
        ),
        "unpriced_count": summary.get("unpriced_count", 0),
    }


def build_sector_insight(
    sectors: list[dict[str, Any]],
) -> dict[str, Any]:
    """セクター別の特徴を抽出する。"""

    if not sectors:
        return {
            "concentration": "セクターデータなし",
            "largest_by_value": None,
            "positive_sectors": [],
            "negative_sectors": [],
        }

    sorted_sectors = sorted(
        sectors,
        key=lambda sector: sector.get("value") or 0,
        reverse=True,
    )

    largest_sector = sorted_sectors[0]

    positive_sectors = [
        sector["sector_name"]
        for sector in sectors
        if (sector.get("profit") or 0) > 0
    ]

    negative_sectors = [
        sector["sector_name"]
        for sector in sectors
        if (sector.get("profit") or 0) < 0
    ]

    largest_weight = largest_sector.get("weight") or 0

    if largest_weight >= SECTOR_CONCENTRATION_HIGH:
        concentration = "特定セクターへの集中が大きい"
    elif largest_weight >= SECTOR_CONCENTRATION_MEDIUM:
        concentration = "特定セクターへの集中に注意"
    else:
        concentration = "特定セクターへの大きな集中はない"

    return {
        "concentration": concentration,
        "largest_by_value": largest_sector["sector_name"],
        "largest_weight": largest_weight,
        "positive_sectors": positive_sectors,
        "negative_sectors": negative_sectors,
    }


def build_holdings_insight(
    holdings: list[dict[str, Any]],
) -> dict[str, Any]:
    """銘柄別の特徴を抽出する。"""

    priced_holdings = [
        holding
        for holding in holdings
        if holding.get("priced") is True
        and holding.get("value") is not None
    ]

    positive_holdings = sorted(
        [
            holding
            for holding in priced_holdings
            if (holding.get("profit") or 0) > 0
        ],
        key=lambda holding: holding.get("profit") or 0,
        reverse=True,
    )

    negative_holdings = sorted(
        [
            holding
            for holding in priced_holdings
            if (holding.get("profit") or 0) < 0
        ],
        key=lambda holding: holding.get("profit") or 0,
    )

    largest_by_value = max(
        priced_holdings,
        key=lambda holding: holding.get("value") or 0,
        default=None,
    )

    largest_by_profit = max(
        priced_holdings,
        key=lambda holding: holding.get("profit") or 0,
        default=None,
    )

    company_accounts: dict[str, set[str]] = defaultdict(set)

    for holding in holdings:
        company_name = holding.get("company_name")
        account_type = holding.get("account_type")

        if company_name and account_type:
            company_accounts[company_name].add(account_type)

    same_company_multiple_accounts = [
        company_name
        for company_name, accounts in company_accounts.items()
        if len(accounts) >= 2
    ]

    return {
        "positive_holdings": unique_holding_names(
            positive_holdings
        ),
        "negative_holdings": unique_holding_names(
            negative_holdings
        ),
        "largest_by_value": holding_name(
            largest_by_value
        ),
        "largest_by_profit": holding_name(
            largest_by_profit
        ),
        "same_company_multiple_accounts": (
            same_company_multiple_accounts
        ),
        "unpriced_holdings_count": (
            len(holdings) - len(priced_holdings)
        ),
    }


def build_portfolio_insight(
    data: PortfolioAnalysisInput,
) -> dict[str, Any]:
    """LLMへ渡す分析済みデータを作成する。"""

    return {
        "summary": build_summary_insight(
            data["summary"]
        ),
        "sectors": build_sector_insight(
            data["sectors"]
        ),
        "holdings": build_holdings_insight(
            data["holdings"]
        ),
    }

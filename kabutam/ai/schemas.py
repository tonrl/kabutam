# kabutam/ai/schemas.py

from typing import TypedDict


class PortfolioHolding(TypedDict):
    code: str
    company_name: str | None
    sector_name: str | None
    account_type: str
    shares: int
    average_price: float
    cost: float
    latest_price: float | None
    value: float | None
    profit: float | None
    daily_profit: float | None
    previous_value: float | None
    monthly_profit: float | None
    monthly_profit_rate: float | None
    three_month_profit: float | None
    three_month_profit_rate: float | None
    dividend_pre_tax: float | None
    dividend_post_tax: float | None
    priced: bool


class PortfolioSector(TypedDict):
    sector_name: str
    value: float
    weight: float
    profit: float
    daily_profit: float | None
    has_daily_profit: bool


class PortfolioSummary(TypedDict):
    total_cost: float
    total_value: float
    total_priced_cost: float
    total_previous_value: float
    daily_profit: float
    daily_profit_rate: float | None
    total_month_previous_value: float
    monthly_profit: float | None
    monthly_profit_rate: float | None
    total_three_month_previous_value: float
    three_month_profit: float | None
    three_month_profit_rate: float | None
    unrealised_profit: float
    unrealised_profit_rate: float | None
    total_dividend_pre_tax: float
    total_dividend_post_tax: float
    yield_on_cost: float | None
    yield_on_value: float | None
    unpriced_count: int


class PortfolioAnalysisInput(TypedDict):
    summary: PortfolioSummary
    holdings: list[PortfolioHolding]
    sectors: list[PortfolioSector]

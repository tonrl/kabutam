# kabutam/ai/portfolio.py

from kabutam.ai.ollama import OllamaClient
from kabutam.ai.prompts import build_portfolio_analysis_prompt
from kabutam.ai.schemas import PortfolioAnalysisInput
from kabutam.analysis.portfolio import calculate_portfolio_row
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
import json
from kabutam.ai.insights import build_portfolio_insight



def round_money(value):
    if value is None:
        return None
    return round(value)


def round_price(value):
    if value is None:
        return None
    return round(value, 2)


def round_rate(value):
    if value is None:
        return None
    return round(value, 2)

def remove_none_values(value):
    if isinstance(value, dict):
        return {
            key: remove_none_values(item)
            for key, item in value.items()
            if item is not None
        }

    if isinstance(value, list):
        return [
            remove_none_values(item)
            for item in value
        ]

    return value

def build_portfolio_analysis_input(
    holdings,
    latest_prices,
    previous_prices,
    month_previous_prices,
    three_month_previous_prices,
    forecast_dividends,
    company_names,
    sector_names,
    summary,
    sector_allocation,
) -> PortfolioAnalysisInput:
    analysis_holdings = []

    for code, accounts in holdings.items():
        latest_price = latest_prices.get(code)
        previous_price = previous_prices.get(code)
        month_previous_price = month_previous_prices.get(code)
        three_month_previous_price = (
            three_month_previous_prices.get(code)
        )
        forecast_dividend = forecast_dividends.get(code)

        company_name = company_names.get(code)
        sector_name = sector_names.get(code)

        for account_type, holding in accounts.items():
            row = calculate_portfolio_row(
                code=code,
                account_type=account_type,
                holding=holding,
                latest_price=latest_price,
                previous_price=previous_price,
                month_previous_price=month_previous_price,
                three_month_previous_price=three_month_previous_price,
                forecast_dividend=forecast_dividend,
            )

            if company_name is not None:
                row["company_name"] = company_name

            if sector_name is not None:
                row["sector_name"] = sector_name

            row["shares"] = int(row["shares"])
            row["average_price"] = round_price(
                row["average_price"]
            )
            row["cost"] = round_money(row["cost"])
            row["latest_price"] = round_price(
                row["latest_price"]
            )
            row["value"] = round_money(row["value"])
            row["profit"] = round_money(row["profit"])
            row["daily_profit"] = round_money(
                row["daily_profit"]
            )
            row["previous_value"] = round_money(
                row["previous_value"]
            )
            row["monthly_profit"] = round_money(
                row["monthly_profit"]
            )
            row["monthly_profit_rate"] = round_rate(
                row["monthly_profit_rate"]
            )
            row["three_month_profit"] = round_money(
                row["three_month_profit"]
            )
            row["three_month_profit_rate"] = round_rate(
                row["three_month_profit_rate"]
            )
            row["dividend_pre_tax"] = round_money(
                row["dividend_pre_tax"]
            )
            row["dividend_post_tax"] = round_money(
                row["dividend_post_tax"]
            )

            analysis_holdings.append(row)

    analysis_sectors = [
        {
            "sector_name": sector,
            "value": round_money(value),
            "weight": round_rate(weight),
            "profit": round_money(profit),
            "daily_profit": round_money(daily_profit),
            "has_daily_profit": has_daily_profit,
        }
        for (
            sector,
            value,
            weight,
            profit,
            daily_profit,
            has_daily_profit,
        ) in sector_allocation
    ]

    analysis_summary = {
        "total_cost": round_money(summary["total_cost"]),
        "total_value": round_money(summary["total_value"]),
        "total_priced_cost": round_money(
            summary["total_priced_cost"]
        ),
        "total_previous_value": round_money(
            summary["total_previous_value"]
        ),
        "daily_profit": round_money(
            summary["daily_profit"]
        ),
        "daily_profit_rate": round_rate(
            summary.get("daily_profit_rate")
        ),
        "total_month_previous_value": round_money(
            summary["total_month_previous_value"]
        ),
        "monthly_profit": round_money(
            summary.get("monthly_profit")
        ),
        "monthly_profit_rate": round_rate(
            summary.get("monthly_profit_rate")
        ),
        "total_three_month_previous_value": round_money(
            summary["total_three_month_previous_value"]
        ),
        "three_month_profit": round_money(
            summary.get("three_month_profit")
        ),
        "three_month_profit_rate": round_rate(
            summary.get("three_month_profit_rate")
        ),
        "unrealised_profit": round_money(
            summary["unrealised_profit"]
        ),
        "unrealised_profit_rate": round_rate(
            summary.get("unrealised_profit_rate")
        ),
        "total_dividend_pre_tax": round_money(
            summary["total_dividend_pre_tax"]
        ),
        "total_dividend_post_tax": round_money(
            summary["total_dividend_post_tax"]
        ),
        "yield_on_cost": round_rate(
            summary.get("yield_on_cost")
        ),
        "yield_on_value": round_rate(
            summary.get("yield_on_value")
        ),
        "unpriced_count": summary["unpriced_count"],
    }

    result = {
        "summary": analysis_summary,
        "holdings": analysis_holdings,
        "sectors": analysis_sectors,
    }

    # print("\n===== AI DATA SUMMARY =====")
    # print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return result


console = Console()

DISPLAY_WIDTH = 100

THINKING_FRAMES = [
    "⠋",
    "⠙",
    "⠹",
    "⠸",
    "⠼",
    "⠴",
    "⠦",
    "⠧",
    "⠇",
    "⠏",
]


def render_markdown(text):
    return Panel(
        Markdown(text),
        width=DISPLAY_WIDTH,
        border_style="dim",
        padding=(0, 1),
    )


def analyze_portfolio(data: PortfolioAnalysisInput) -> str:
    # print("\n===== DATA RECEIVED BY analyze_portfolio =====")
    # print(json.dumps(data["summary"], ensure_ascii=False, indent=2))
    prompt = build_portfolio_analysis_prompt(data)
    
    # print("\n===== GENERATED PROMPT =====")
    # print(prompt)


    client = OllamaClient(
        # model="qwen3:8b",
        model="gemma4:latest",
    )

    chunks = []
    generated_text = ""

    frame = 0

    with Live(
        console=console,
        refresh_per_second=6,
        transient=False,
    ) as live:
        live.update(
            Text(
                f"{THINKING_FRAMES[frame]} 分析中...",
            )
        )

        for event in client.generate_stream(prompt):
            # if event["type"] == "thinking":
            #     frame = (frame + 1) % len(THINKING_FRAMES)
            #
            #     live.update(
            #         Text(
            #             f"{THINKING_FRAMES[frame]} 分析中...",
            #         )
            #     )
            #
            # elif event["type"] == "content":
            #     text = event["text"]
            #
            #     chunks.append(text)
            #     generated_text += text
            #
            #     live.update(render_markdown(generated_text))
            if event["type"] == "content":
                text = event["text"]
                chunks.append(text)
                generated_text += text
                live.update(render_markdown(generated_text))

    return generated_text

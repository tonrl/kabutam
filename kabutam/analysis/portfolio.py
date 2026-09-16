def calculate_portfolio_row(
    code,
    account_type,
    holding,
    latest_price,
    previous_price,
    month_previous_price,
    three_month_previous_price,
    forecast_dividend,
):
    shares = holding["shares"]
    average_price = holding["average_price"]

    cost = shares * average_price
    monthly_profit = None
    monthly_profit_rate = None
    three_month_profit = None
    three_month_profit_rate = None

    if latest_price is not None:
        value = shares * latest_price
        profit = (latest_price - average_price) * shares

        # 前営業日の保有株評価額
        if previous_price is not None:
            daily_profit = (latest_price - previous_price) * shares
            previous_value = shares * previous_price
        else:
            daily_profit = None
            previous_value = 0

        if month_previous_price is not None:
            monthly_profit = (
                latest_price - month_previous_price
            ) * shares

            monthly_profit_rate = (
                (latest_price - month_previous_price)
                / month_previous_price
                * 100
            )

        if three_month_previous_price is not None:
            three_month_profit = (
                latest_price - three_month_previous_price
            ) * shares

            three_month_profit_rate = (
                (latest_price - three_month_previous_price)
                / three_month_previous_price
                * 100
            )
    else:
        value = None
        profit = None
        daily_profit = None
        previous_value = 0

    if forecast_dividend is not None:
        dividend_pre_tax = shares * forecast_dividend
        # NISA口座は非課税(0%)、その他は20.315%
        is_nisa = "NISA" in account_type.upper()
        tax_rate = 0.0 if is_nisa else 0.20315
        dividend_post_tax = dividend_pre_tax * (1 - tax_rate)
    else:
        dividend_pre_tax = 0
        dividend_post_tax = 0

    return {
        "code": code,
        "account_type": account_type,
        "shares": shares,
        "average_price": average_price,
        "cost": cost,
        "latest_price": latest_price,
        "value": value,
        "profit": profit,
        "daily_profit": daily_profit,
        "monthly_profit": monthly_profit,
        "monthly_profit_rate": monthly_profit_rate,
        "three_month_profit": three_month_profit,
        "three_month_profit_rate": three_month_profit_rate,
        "previous_value": previous_value,
        "dividend_pre_tax": dividend_pre_tax,
        "dividend_post_tax": dividend_post_tax,
        "priced": latest_price is not None,
    }


def calculate_portfolio_summary(
    total_cost,
    total_value,
    total_priced_cost,
    total_previous_value,
    total_daily_profit,
    total_month_previous_value,
    total_three_month_previous_value,
    total_dividend_pre_tax,
    total_dividend_post_tax,
    unpriced_count,
):
    # -------------損益-----------------------
    unrealised_profit = total_value - total_priced_cost
    daily_profit = total_daily_profit

    monthly_profit = (
            total_value - total_month_previous_value
            if total_month_previous_value > 0
            else None
    )
    
    monthly_profit_rate = (
            monthly_profit / total_month_previous_value * 100
            if total_month_previous_value > 0
            else None
    )
    
    three_month_profit = (
            total_value - total_three_month_previous_value
            if total_three_month_previous_value > 0
            else None
    )
    
    three_month_profit_rate = (
            three_month_profit / total_three_month_previous_value * 100
            if total_three_month_previous_value > 0
            else None
    )

    # -------------損益率---------------------
    daily_profit_rate = (
        daily_profit / total_previous_value * 100 if total_previous_value > 0 else None
    )

    unrealised_profit_rate = (
        unrealised_profit / total_priced_cost * 100 if total_priced_cost > 0 else None
    )

    # -------------配当利回り-----------------
    yield_on_cost = (
        total_dividend_pre_tax / total_cost * 100 if total_cost > 0 else None
    )

    yield_on_value = (
        total_dividend_pre_tax / total_value * 100 if total_value > 0 else None
    )

    return {
        "total_cost": total_cost,
        "total_value": total_value,
        "total_priced_cost": total_priced_cost,
        "total_previous_value": total_previous_value,
        "daily_profit": daily_profit,
        "daily_profit_rate": daily_profit_rate,

        "total_month_previous_value": total_month_previous_value,
        "monthly_profit": monthly_profit,
        "monthly_profit_rate": monthly_profit_rate,

        "total_three_month_previous_value": total_three_month_previous_value,
        "three_month_profit": three_month_profit,
        "three_month_profit_rate": three_month_profit_rate,

        "unrealised_profit": unrealised_profit,
        "unrealised_profit_rate": unrealised_profit_rate,
        "total_dividend_pre_tax": total_dividend_pre_tax,
        "total_dividend_post_tax": total_dividend_post_tax,
        "yield_on_cost": yield_on_cost,
        "yield_on_value": yield_on_value,
        "unpriced_count": unpriced_count,
    }


def calculate_sector_allocation(
    holdings,
    latest_prices,
    previous_prices,
    sector_names,
):
    """
    ポートフォリオの33業種別構成比を計算する。
    """
    sector_data = {}

    for code, accounts in holdings.items():
        latest_price = latest_prices.get(code)
        previous_price = previous_prices.get(code)

        if latest_price is None:
            continue

        sector_name = sector_names.get(code, "業種不明")

        shares = sum(holding["shares"] for holding in accounts.values())

        value = shares * latest_price

        profit = sum(
            (latest_price - holding["average_price"]) * holding["shares"]
            for holding in accounts.values()
        )

        daily_profit = None

        if previous_price is not None:
            daily_profit = (latest_price - previous_price) * shares

        if sector_name not in sector_data:
            sector_data[sector_name] = {
                "value": 0,
                "profit": 0,
                "daily_profit": 0,
                "has_daily_profit": False,
            }

        sector_data[sector_name]["value"] += value
        sector_data[sector_name]["profit"] += profit

        if daily_profit is not None:
            sector_data[sector_name]["daily_profit"] += daily_profit
            sector_data[sector_name]["has_daily_profit"] = True

    total_value = sum(data["value"] for data in sector_data.values())

    if total_value <= 0:
        return []

    allocation = []

    for sector, data in sector_data.items():
        weight = data["value"] / total_value * 100

        allocation.append(
            (
                sector,
                data["value"],
                weight,
                data["profit"],
                data["daily_profit"],
                data["has_daily_profit"],
            )
        )

    allocation.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    return allocation

from .connection import get_connection

def create_table_corp_data(conn):
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS edinet_corp_data (
            EDINETCode TEXT PRIMARY KEY,

            DisclosureDate TEXT,
            FiscalYear INTEGER,
            Quarter INTEGER,

            PER REAL,
            PBR REAL,
            EPS REAL,
            BPS REAL,
            ROE REAL,

            dividend_yield REAL,
            dividend_per_share REAL,
            interim_dividend_per_share REAL,
            yearend_dividend_per_share REAL,
            forecast_dividend_per_share REAL,

            revenue REAL,
            operating_income REAL,
            ordinary_income REAL,
            net_income REAL,

            forecast_revenue REAL,
            forecast_operating_income REAL,
            forecast_net_income REAL,
            forecast_eps REAL,

            equity_ratio REAL,
            cash REAL,
            total_assets REAL,
            total_liabilities REAL,
            shareholders_equity REAL,
            net_assets REAL,

            operating_cf REAL,
            capex REAL,
            depreciation REAL,
            interest_bearing_debt REAL,

            land REAL,
            investment_securities REAL,

            UpdatedAt TEXT
        )
    """)


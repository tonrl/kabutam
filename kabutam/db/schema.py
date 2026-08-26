def create_table_corp_data(conn):
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
    conn.commit()

def create_table_portfolio(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Code TEXT NOT NULL,
            account_type TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            shares INTEGER NOT NULL,
            price REAL NOT NULL,
            transaction_date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS corporate_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Code TEXT NOT NULL,
            action_type TEXT NOT NULL,
            ratio REAL NOT NULL,
            effective_date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def create_table_doc_data(conn):
    conn.execute("""
        CREATE TABLE edinet_corp_ir_documents (
            document_id TEXT PRIMARY KEY,
            EDINETCode TEXT,
            document_id TEXT,
            document_label_en TEXT,
            document_label_jp TEXT,
            pdf_link TEXT,
            published_at TEXT,
            UpdatedAt TEXT
        )
    """)
    conn.commit()

def create_table_ir_calender_data(conn):
    conn.execute("""
        CREATE TABLE edinet_corp_ir_calendar (
            EDINETCode TEXT,
            fiscal_year_end TEXT,
            period_type TEXT,
            announcement_date TEXT,
            estimated_announcement_date TEXT,
            date_status TEXT,
            confidence TEXT,
            UpdatedAt TEXT,
            PRIMARY KEY (EDINETCode, fiscal_year_end, period_type)
        )
    """)
    conn.commit()


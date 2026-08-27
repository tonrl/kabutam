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

def create_table_edinet_doc_list(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS edinet_doc_list (
            document_id TEXT PRIMARY KEY,
            EDINETCode TEXT,
            doc_description TEXT,
            submit_datetime TEXT,
            pdf_flag TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS edinet_sync_status (
            target_date TEXT PRIMARY KEY,
            last_seq_number INTEGER,
            document_count INTEGER DEFAULT 0,
            last_checked_at TEXT,
            completed INTEGER DEFAULT 0,
            completed_at TEXT
        )
    """)
    conn.commit()

def create_table_tdnet_disclosure(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tdnet_disclosure (
            disclosure_id TEXT PRIMARY KEY,
            disclosure_date TEXT NOT NULL,
            disclosure_time TEXT,
            sec_code TEXT,
            company_name TEXT,
            title TEXT,
            pdf_url TEXT,
            market TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tdnet_sync_status (
            target_date TEXT PRIMARY KEY,
            document_count INTEGER DEFAULT 0,
            last_checked_at TEXT,
            completed INTEGER DEFAULT 0,
            completed_at TEXT
        )
    """)
    conn.commit()

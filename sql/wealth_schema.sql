-- Legacy Wealth Dashboard - Database Schema
-- Database: wealth (create new database for financial data)

-- ============================================================
-- ACCOUNTS: Track all assets and liabilities
-- ============================================================
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('asset', 'liability')),
    category VARCHAR(50) NOT NULL,
    -- Asset categories: 'checking', 'savings', 'investment', 'retirement', 'real_estate', 'vehicle', 'crypto', 'other'
    -- Liability categories: 'mortgage', 'auto_loan', 'student_loan', 'credit_card', 'personal_loan', 'other'
    
    name VARCHAR(255) NOT NULL,
    institution VARCHAR(255),
    
    -- Financial details
    balance DECIMAL(12,2) NOT NULL DEFAULT 0,
    interest_rate DECIMAL(5,2) DEFAULT 0,
    
    -- Metadata
    notes TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- NET WORTH SNAPSHOTS: Historical tracking
-- ============================================================
CREATE TABLE net_worth_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL UNIQUE,
    total_assets DECIMAL(12,2) NOT NULL,
    total_liabilities DECIMAL(12,2) NOT NULL,
    net_worth DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TRANSACTIONS: Income and expenses
-- ============================================================
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    
    category VARCHAR(100) NOT NULL,
    -- Income: 'salary', 'bonus', 'side_hustle', 'dividends', 'rental_income', 'other_income'
    -- Expense: 'housing', 'transportation', 'food', 'healthcare', 'entertainment', 
    --          'subscriptions', 'debt_payment', 'shopping', 'utilities', 'other'
    
    description TEXT,
    amount DECIMAL(10,2) NOT NULL,
    type VARCHAR(10) NOT NULL CHECK (type IN ('income', 'expense')),
    
    -- Metadata
    recurring BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- INVESTMENTS: Portfolio holdings
-- ============================================================
CREATE TABLE investments (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    name VARCHAR(255) NOT NULL,
    asset_class VARCHAR(50) NOT NULL,
    -- 'stock', 'etf', 'mutual_fund', 'bond', 'crypto', 'real_estate', 'commodity'
    
    -- Position details
    shares DECIMAL(12,6) NOT NULL,
    cost_basis DECIMAL(12,2) NOT NULL,
    current_price DECIMAL(10,2),
    current_value DECIMAL(12,2),
    
    -- Performance
    unrealized_gain_loss DECIMAL(12,2),
    realized_gain_loss DECIMAL(12,2) DEFAULT 0,
    
    -- Metadata
    account_id INTEGER REFERENCES accounts(id),
    purchase_date DATE,
    notes TEXT,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- DEBTS: Liability tracking with payoff planning
-- ============================================================
CREATE TABLE debts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    
    -- Debt details
    original_balance DECIMAL(12,2),
    current_balance DECIMAL(12,2) NOT NULL,
    interest_rate DECIMAL(5,2) NOT NULL,
    minimum_payment DECIMAL(10,2) NOT NULL,
    
    -- Payoff strategy
    payoff_strategy VARCHAR(20) DEFAULT 'avalanche',
    -- 'snowball' (lowest balance first), 'avalanche' (highest rate first), 'custom'
    priority INTEGER DEFAULT 1,
    extra_payment DECIMAL(10,2) DEFAULT 0,
    
    -- Dates
    start_date DATE,
    target_payoff_date DATE,
    
    -- Link to account
    account_id INTEGER REFERENCES accounts(id),
    
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- GOALS: Financial milestones
-- ============================================================
CREATE TABLE goals (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Target
    target_amount DECIMAL(12,2) NOT NULL,
    current_amount DECIMAL(12,2) DEFAULT 0,
    target_date DATE,
    
    category VARCHAR(50),
    -- 'emergency_fund', 'down_payment', 'retirement', 'debt_free', 'net_worth', 'vacation', 'education', 'other'
    
    -- Progress
    progress_percentage DECIMAL(5,2) DEFAULT 0,
    achieved BOOLEAN DEFAULT FALSE,
    achieved_date DATE,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- BUDGET: Monthly budget planning
-- ============================================================
CREATE TABLE budget (
    id SERIAL PRIMARY KEY,
    month DATE NOT NULL, -- Store as first day of month
    category VARCHAR(100) NOT NULL,
    budgeted_amount DECIMAL(10,2) NOT NULL,
    actual_amount DECIMAL(10,2) DEFAULT 0,
    
    UNIQUE(month, category)
);

-- ============================================================
-- INDEXES for performance
-- ============================================================
CREATE INDEX idx_accounts_type ON accounts(account_type);
CREATE INDEX idx_accounts_active ON accounts(active);
CREATE INDEX idx_transactions_date ON transactions(date DESC);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_snapshots_date ON net_worth_snapshots(snapshot_date DESC);
CREATE INDEX idx_investments_symbol ON investments(symbol);
CREATE INDEX idx_debts_active ON debts(active);
CREATE INDEX idx_goals_achieved ON goals(achieved);

-- ============================================================
-- VIEWS for common queries
-- ============================================================

-- Current net worth calculation
CREATE OR REPLACE VIEW current_net_worth AS
SELECT 
    COALESCE(SUM(CASE WHEN account_type = 'asset' THEN balance ELSE 0 END), 0) as total_assets,
    COALESCE(SUM(CASE WHEN account_type = 'liability' THEN balance ELSE 0 END), 0) as total_liabilities,
    COALESCE(SUM(CASE WHEN account_type = 'asset' THEN balance ELSE 0 END), 0) - 
    COALESCE(SUM(CASE WHEN account_type = 'liability' THEN balance ELSE 0 END), 0) as net_worth
FROM accounts
WHERE active = TRUE;

-- Monthly cash flow
CREATE OR REPLACE VIEW monthly_cash_flow AS
SELECT 
    DATE_TRUNC('month', date) as month,
    SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income,
    SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expenses,
    SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END) as net_cash_flow
FROM transactions
GROUP BY DATE_TRUNC('month', date)
ORDER BY month DESC;

-- Asset allocation
CREATE OR REPLACE VIEW asset_allocation AS
SELECT 
    category,
    SUM(balance) as total,
    ROUND(SUM(balance) / NULLIF((SELECT SUM(balance) FROM accounts WHERE account_type = 'asset' AND active = TRUE), 0) * 100, 2) as percentage
FROM accounts
WHERE account_type = 'asset' AND active = TRUE
GROUP BY category
ORDER BY total DESC;

#!/usr/bin/env python3
"""
Legacy Wealth Dashboard
Flask application for tracking net worth, investments, and financial goals

Integrates with existing Casino Dashboard infrastructure
"""

from flask import Flask, render_template_string, jsonify, request, Response
import psycopg2
from datetime import datetime, timedelta
from decimal import Decimal
import json
import fire_calculator

from config import DB_CONFIG

def get_db():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)

def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

# ============================================================
# DATA FUNCTIONS
# ============================================================

def get_current_net_worth():
    """Get current net worth from database view"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM current_net_worth")
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row:
        return {
            'total_assets': float(row[0]),
            'total_liabilities': float(row[1]),
            'net_worth': float(row[2])
        }
    return {'total_assets': 0, 'total_liabilities': 0, 'net_worth': 0}

def get_accounts():
    """Get all active accounts"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, account_type, category, name, institution, balance, interest_rate
        FROM accounts
        WHERE active = TRUE
        ORDER BY account_type, category, name
    """)
    accounts = []
    for row in cur.fetchall():
        accounts.append({
            'id': row[0],
            'type': row[1],
            'category': row[2],
            'name': row[3],
            'institution': row[4],
            'balance': float(row[5]),
            'rate': float(row[6]) if row[6] else 0
        })
    cur.close()
    conn.close()
    return accounts

def get_net_worth_history(days=365):
    """Get net worth snapshots for chart"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT snapshot_date, net_worth
        FROM net_worth_snapshots
        WHERE snapshot_date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY snapshot_date
    """, (days,))
    history = []
    for row in cur.fetchall():
        history.append({
            'date': row[0].isoformat(),
            'net_worth': float(row[1])
        })
    cur.close()
    conn.close()
    return history

def get_asset_allocation():
    """Get asset breakdown from view"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM asset_allocation")
    allocation = []
    for row in cur.fetchall():
        allocation.append({
            'category': row[0],
            'total': float(row[1]),
            'percentage': float(row[2]) if row[2] else 0
        })
    cur.close()
    conn.close()
    return allocation

def get_monthly_cash_flow(months=12):
    """Get cash flow for last N months"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            month,
            total_income,
            total_expenses,
            net_cash_flow
        FROM monthly_cash_flow
        LIMIT %s
    """, (months,))
    cash_flow = []
    for row in cur.fetchall():
        cash_flow.append({
            'month': row[0].strftime('%Y-%m'),
            'income': float(row[1]),
            'expenses': float(row[2]),
            'net': float(row[3])
        })
    cur.close()
    conn.close()
    return cash_flow

def add_account(data):
    """Add new account"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO accounts (account_type, category, name, institution, balance, interest_rate)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        data['account_type'],
        data['category'],
        data['name'],
        data.get('institution', ''),
        data['balance'],
        data.get('interest_rate', 0)
    ))
    account_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return account_id

def create_snapshot():
    """Create net worth snapshot for today"""
    nw = get_current_net_worth()
    conn = get_db()
    cur = conn.cursor()
    
    # Insert or update today's snapshot
    cur.execute("""
        INSERT INTO net_worth_snapshots (snapshot_date, total_assets, total_liabilities, net_worth)
        VALUES (CURRENT_DATE, %s, %s, %s)
        ON CONFLICT (snapshot_date) 
        DO UPDATE SET 
            total_assets = EXCLUDED.total_assets,
            total_liabilities = EXCLUDED.total_liabilities,
            net_worth = EXCLUDED.net_worth
    """, (nw['total_assets'], nw['total_liabilities'], nw['net_worth']))
    
    conn.commit()
    cur.close()
    conn.close()

# ============================================================
# FLASK ROUTES
# ============================================================

app = Flask(__name__)

@app.route('/wealth')
def wealth_dashboard():
    """Main wealth dashboard page"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/wealth/api/overview')
def api_overview():
    """API endpoint for dashboard overview data"""
    nw = get_current_net_worth()
    accounts = get_accounts()
    allocation = get_asset_allocation()
    history = get_net_worth_history(90)  # Last 90 days
    
    # Calculate monthly change
    if len(history) >= 30:
        month_ago_nw = history[-30]['net_worth']
        monthly_change = nw['net_worth'] - month_ago_nw
        monthly_change_pct = (monthly_change / month_ago_nw * 100) if month_ago_nw != 0 else 0
    else:
        monthly_change = 0
        monthly_change_pct = 0
    
    return jsonify({
        'net_worth': nw,
        'accounts': accounts,
        'allocation': allocation,
        'history': history,
        'monthly_change': monthly_change,
        'monthly_change_pct': monthly_change_pct
    })

@app.route('/wealth/api/accounts', methods=['GET', 'POST'])
def api_accounts():
    """Manage accounts"""
    if request.method == 'POST':
        data = request.json
        account_id = add_account(data)
        create_snapshot()  # Update snapshot after adding account
        return jsonify({'success': True, 'id': account_id})
    else:
        return jsonify(get_accounts())

@app.route('/wealth/api/snapshot', methods=['POST'])
def api_snapshot():
    """Create net worth snapshot"""
    create_snapshot()
    return jsonify({'success': True})

@app.route('/wealth/api/export/accounts')
def export_accounts_csv():
    """Export all accounts to CSV"""
    import csv
    from io import StringIO
    
    accounts = get_accounts()
    
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=['type', 'category', 'name', 'institution', 'balance', 'rate'])
    writer.writeheader()
    
    for acc in accounts:
        writer.writerow({
            'type': acc['type'],
            'category': acc['category'],
            'name': acc['name'],
            'institution': acc['institution'],
            'balance': acc['balance'],
            'rate': acc['rate']
        })
    
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=wealth_accounts.csv'}
    )

@app.route('/wealth/api/import/accounts', methods=['POST'])
def import_accounts_csv():
    """Import accounts from CSV file"""
    import csv
    from io import StringIO
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Empty filename'}), 400
    
    try:
        content = file.read().decode('utf-8')
        reader = csv.DictReader(StringIO(content))
        
        imported = 0
        errors = []
        
        for row in reader:
            try:
                add_account({
                    'account_type': row['type'],
                    'category': row['category'],
                    'name': row['name'],
                    'institution': row.get('institution', ''),
                    'balance': float(row['balance']),
                    'interest_rate': float(row.get('rate', 0))
                })
                imported += 1
            except Exception as e:
                errors.append(f"Row error: {str(e)}")
        
        create_snapshot()  # Update snapshot after import
        
        return jsonify({
            'success': True,
            'imported': imported,
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/wealth/api/fire')
def api_fire():
    """FIRE (Financial Independence Retire Early) calculator"""
    # Get current financial data
    nw = get_current_net_worth()
    
    # Get user inputs or use defaults
    annual_expenses = float(request.args.get('annual_expenses', 50000))
    annual_savings = float(request.args.get('annual_savings', 20000))
    current_age = int(request.args.get('current_age', 30))
    retirement_age = int(request.args.get('retirement_age', 65))
    monthly_contribution = float(request.args.get('monthly_contribution', 1500))
    return_rate = float(request.args.get('return_rate', 0.07))
    
    # Calculate FIRE metrics
    fire_number = fire_calculator.calculate_fire_number(annual_expenses)
    years_to_fire = fire_calculator.calculate_years_to_fire(
        nw['net_worth'],
        annual_savings,
        annual_expenses,
        return_rate
    )
    fi_progress = fire_calculator.calculate_fi_progress(nw['net_worth'], annual_expenses)
    
    # Retirement projection
    projection = fire_calculator.calculate_retirement_projections(
        current_age,
        retirement_age,
        nw['net_worth'],
        monthly_contribution,
        return_rate
    )
    
    return jsonify({
        'current_net_worth': nw['net_worth'],
        'fire_number': round(fire_number, 2),
        'years_to_fire': round(years_to_fire, 2) if years_to_fire else None,
        'fi_progress_pct': fi_progress,
        'retirement_projection': projection,
        'inputs': {
            'annual_expenses': annual_expenses,
            'annual_savings': annual_savings,
            'current_age': current_age,
            'retirement_age': retirement_age,
            'monthly_contribution': monthly_contribution,
            'return_rate': return_rate
        }
    })


# ============================================================
# HTML TEMPLATE
# ============================================================

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Legacy Wealth Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        body { background: #1a1a2e; color: #eee; padding: 20px; }
        .card { background: #16213e; border: 1px solid #0f3460; margin-bottom: 20px; }
        .kpi-card { text-align: center; padding: 20px; }
        .kpi-value { font-size: 2.5rem; font-weight: bold; color: #4ecca3; }
        .kpi-label { color: #aaa; font-size: 0.9rem; }
        .kpi-change { font-size: 1rem; margin-top: 5px; }
        .positive { color: #4ecca3; }
        .negative { color: #ee6f57; }
        .account-row { padding: 10px; border-bottom: 1px solid #0f3460; }
        .account-row:hover { background: #0f3460; }
        .asset { color: #4ecca3; }
        .liability { color: #ee6f57; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1>💎 Legacy Wealth Dashboard</h1>
        <p class="text-muted">Building generational wealth</p>
        
        <!-- KPI Cards -->
        <div class="row" id="kpis">
            <div class="col-md-3">
                <div class="card kpi-card">
                    <div class="kpi-label">NET WORTH</div>
                    <div class="kpi-value" id="net-worth">$0</div>
                    <div class="kpi-change" id="nw-change"></div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card kpi-card">
                    <div class="kpi-label">TOTAL ASSETS</div>
                    <div class="kpi-value asset" id="total-assets">$0</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card kpi-card">
                    <div class="kpi-label">TOTAL LIABILITIES</div>
                    <div class="kpi-value liability" id="total-liabilities">$0</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card kpi-card">
                    <div class="kpi-label">ACCOUNTS</div>
                    <div class="kpi-value" id="account-count">0</div>
                </div>
            </div>
        </div>
        
        <!-- Charts Row -->
        <div class="row">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-body">
                        <h5>Net Worth Trend (90 Days)</h5>
                        <canvas id="netWorthChart"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5>Asset Allocation</h5>
                        <canvas id="allocationChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Accounts List -->
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5>Accounts</h5>
                            <div>
                                <button class="btn btn-success btn-sm me-2" onclick="exportCSV()">📥 Export CSV</button>
                                <button class="btn btn-warning btn-sm me-2" onclick="document.getElementById('csvUpload').click()">📤 Import CSV</button>
                                <button class="btn btn-primary btn-sm" onclick="showAddAccount()">+ Add Account</button>
                                <input type="file" id="csvUpload" accept=".csv" style="display:none" onchange="importCSV(this)">
                            </div>
                        </div>
                        <div id="accounts-list"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let netWorthChart, allocationChart;
        
        function formatCurrency(amount) {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(amount);
        }
        
        function loadDashboard() {
            fetch('/wealth/api/overview')
                .then(r => r.json())
                .then(data => {
                    // Update KPIs
                    document.getElementById('net-worth').textContent = formatCurrency(data.net_worth.net_worth);
                    document.getElementById('total-assets').textContent = formatCurrency(data.net_worth.total_assets);
                    document.getElementById('total-liabilities').textContent = formatCurrency(data.net_worth.total_liabilities);
                    document.getElementById('account-count').textContent = data.accounts.length;
                    
                    // Monthly change
                    const changeEl = document.getElementById('nw-change');
                    const change = data.monthly_change;
                    const changePct = data.monthly_change_pct;
                    const arrow = change >= 0 ? '↑' : '↓';
                    const className = change >= 0 ? 'positive' : 'negative';
                    changeEl.innerHTML = `<span class="${className}">${arrow} ${formatCurrency(Math.abs(change))} (${Math.abs(changePct).toFixed(1)}%) this month</span>`;
                    
                    // Render accounts
                    renderAccounts(data.accounts);
                    
                    // Charts
                    renderNetWorthChart(data.history);
                    renderAllocationChart(data.allocation);
                });
        }
        
        function renderAccounts(accounts) {
            const container = document.getElementById('accounts-list');
            const assets = accounts.filter(a => a.type === 'asset');
            const liabilities = accounts.filter(a => a.type === 'liability');
            
            let html = '<h6 class="asset">Assets</h6>';
            assets.forEach(acc => {
                html += `
                    <div class="account-row">
                        <div class="d-flex justify-content-between">
                            <div>
                                <strong>${acc.name}</strong>
                                <small class="text-muted"> (${acc.category})</small><br>
                                <small class="text-muted">${acc.institution || 'No institution'}</small>
                            </div>
                            <div class="text-end">
                                <div class="asset"><strong>${formatCurrency(acc.balance)}</strong></div>
                                ${acc.rate > 0 ? `<small>${acc.rate}% APY</small>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '<h6 class="liability mt-3">Liabilities</h6>';
            if (liabilities.length === 0) {
                html += '<div class="text-muted">No liabilities - you\'re debt free! 🎉</div>';
            } else {
                liabilities.forEach(acc => {
                    html += `
                        <div class="account-row">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <strong>${acc.name}</strong>
                                    <small class="text-muted"> (${acc.category})</small>
                                </div>
                                <div class="text-end">
                                    <div class="liability"><strong>-${formatCurrency(acc.balance)}</strong></div>
                                    ${acc.rate > 0 ? `<small>${acc.rate}% APR</small>` : ''}
                                </div>
                            </div>
                        </div>
                    `;
                });
            }
            
            container.innerHTML = html;
        }
        
        function renderNetWorthChart(history) {
            const ctx = document.getElementById('netWorthChart').getContext('2d');
            
            if (netWorthChart) netWorthChart.destroy();
            
            netWorthChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: history.map(h => h.date),
                    datasets: [{
                        label: 'Net Worth',
                        data: history.map(h => h.net_worth),
                        borderColor: '#4ecca3',
                        backgroundColor: 'rgba(78, 204, 163, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toLocaleString();
                                }
                            }
                        }
                    }
                }
            });
        }
        
        function renderAllocationChart(allocation) {
            const ctx = document.getElementById('allocationChart').getContext('2d');
            
            if (allocationChart) allocationChart.destroy();
            
            const colors = ['#4ecca3', '#ee6f57', '#f9a826', '#5a67d8', '#ed64a6', '#48bb78'];
            
            allocationChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: allocation.map(a => a.category),
                    datasets: [{
                        data: allocation.map(a => a.total),
                        backgroundColor: colors.slice(0, allocation.length)
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = formatCurrency(context.raw);
                                    const pct = allocation[context.dataIndex].percentage.toFixed(1);
                                    return `${label}: ${value} (${pct}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
        
        function showAddAccount() {
            // Simplified - would use a modal in production
            const type = prompt('Account type (asset/liability):');
            if (!type) return;
            
            const category = prompt('Category (checking, savings, mortgage, etc.):');
            const name = prompt('Name:');
            const balance = parseFloat(prompt('Balance:'));
            
            if (!category || !name || isNaN(balance)) {
                alert('Invalid input');
                return;
            }
            
            fetch('/wealth/api/accounts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    account_type: type,
                    category: category,
                    name: name,
                    balance: balance
                })
            })
            .then(r => r.json())
            .then(() => {
                loadDashboard();
            });
        }
        
        
        function exportCSV() {
            window.location.href = '/wealth/api/export/accounts';
        }
        
        function importCSV(input) {
            if (!input.files || input.files.length === 0) return;
            
            const formData = new FormData();
            formData.append('file', input.files[0]);
            
            fetch('/wealth/api/import/accounts', {
                method: 'POST',
                body: formData
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert(`✅ Successfully imported ${data.imported} accounts!${data.errors.length > 0 ? '\n\nErrors:\n' + data.errors.join('\n') : ''}`);
                    loadDashboard();
                } else {
                    alert(`❌ Import failed: ${data.error}`);
                }
                input.value = ''; // Reset file input
            })
            .catch(err => {
                alert(`❌ Import error: ${err.message}`);
                input.value = '';
            });
        }
        
        // Load on page load
        loadDashboard();
        
        // Auto-refresh every 60 seconds
        setInterval(loadDashboard, 60000);
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8005, debug=True)

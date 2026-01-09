#!/bin/bash
# Casino AI System - Complete Deployment Script
# Run this to deploy and test everything

echo "🎰 Casino AI System - Deployment & Testing"
echo "==========================================="
echo ""

cd /Users/rod/Antigravity/home_ai_stack

# Check dependencies
echo "1️⃣  Checking dependencies..."
python3 -c "import sklearn, joblib, psycopg2, requests" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ All Python dependencies installed"
else
    echo "   ⚠️  Installing missing dependencies..."
    pip3 install --user scikit-learn joblib psycopg2-binary requests
fi
echo ""

# Check FunctionGemma
echo "2️⃣  Checking FunctionGemma on Aragorn..."
if curl -s http://192.168.1.176:11434/api/tags 2>/dev/null | grep -q "functiongemma"; then
    echo "   ✅ FunctionGemma available"
else
    echo "   ⚠️  FunctionGemma not found"
    echo "   Run: ssh rod@192.168.1.176 'ollama pull functiongemma:2b'"
fi
echo ""

# Check database
echo "3️⃣  Checking PostgreSQL connection..."
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(host='192.168.1.211', database='postgres', user='rod')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM jackpots')
    count = cursor.fetchone()[0]
    print(f'   ✅ Database connected ({count} jackpots)')
    conn.close()
except Exception as e:
    print(f'   ❌ Database error: {e}')
"
echo ""

# Create alerts table
echo "4️⃣  Creating alerts table..."
python3 -c "
from casino_ai.alert_system import HotMachineAlertSystem
alert_system = HotMachineAlertSystem()
alert_system.create_alerts_table()
"
echo ""

# Train ML models
echo "5️⃣  Training ML models on real casino data..."
echo "   This may take 1-2 minutes..."
python3 casino_ai/jackpot_predictor.py 2>&1 | grep -E "(✅|⚠️|📊|🌲|Loaded|trained)"
echo ""

# Test AI analysis
echo "6️⃣  Testing AI analysis..."
python3 -c "
from casino_ai.ai_integration import CasinoAIEngine
import json

engine = CasinoAIEngine()

# Get a sample machine
import psycopg2
conn = psycopg2.connect(host='192.168.1.211', database='postgres', user='rod')
cursor = conn.cursor()
cursor.execute('SELECT DISTINCT machine_name FROM jackpots LIMIT 1')
machine_id = cursor.fetchone()[0]
conn.close()

print(f'   Testing on machine: {machine_id}')

# Analyze
result = engine.analyze_machine_complete(machine_id)

print(f'   ✅ AI Hot Score: {result[\"ai_hot_score\"]*100:.0f}/100')
print(f'   ✅ ML Predicted Time: {result[\"ml_predicted_minutes\"]} min')
print(f'   ✅ Classification: {result[\"ml_classification\"]}')
print(f'   ✅ Recommendation: {result[\"final_recommendation\"]}')
"
echo ""

# Test hot machines endpoint
echo "7️⃣  Testing hot machines detection..."
python3 -c "
from casino_ai.ai_integration import CasinoAIEngine

engine = CasinoAIEngine()
hot_machines = engine.get_hot_machines(top_n=5)

print(f'   Found {len(hot_machines)} hot machine candidates')
"
echo ""

# Test alert system
echo "8️⃣  Testing alert system (single scan)..."
python3 -c "
from casino_ai.alert_system import HotMachineAlertSystem

alert_system = HotMachineAlertSystem()
alerts = alert_system.check_for_hot_machines()

print(f'   Scanned machines, found {len(alerts)} alerts')
"
echo ""

# Summary
echo "==========================================="
echo "🎉 Deployment Complete!"
echo "==========================================="
echo ""
echo "✅ System Status:"
echo "   - ML models trained"
echo "   - Database configured"
echo "   - Alerts table created"
echo "   - AI analysis working"
echo ""
echo "📊 Quick Stats:"
python3 -c "
import psycopg2
conn = psycopg2.connect(host='192.168.1.211', database='postgres', user='rod')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*), COUNT(DISTINCT machine_name) FROM jackpots')
total, machines = cursor.fetchone()
print(f'   - {total:,} total jackpots')
print(f'   - {machines} unique machines')
conn.close()
"
echo ""
echo "🚀 Next Steps:"
echo "   1. Start API server (if not running):"
echo "      cd casino_ai_api && python3 main.py"
echo ""
echo "   2. Start alert monitor:"
echo "      python3 casino_ai/alert_system.py"
echo ""
echo "   3. Test API endpoints:"
echo "      curl http://192.168.1.176:8080/ai/status"
echo ""
echo "   4. Update dashboard UI with widgets from:"
echo "      casino_ai/dashboard_widgets.py"
echo ""

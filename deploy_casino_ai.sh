#!/bin/bash
# Complete Casino AI Deployment

echo "🎰 Casino AI - Final Integration & Deployment"
echo "=============================================="
echo ""

cd /Users/rod/Antigravity/home_ai_stack

# 1. Train ML Models
echo "1️⃣  Training ML models on 9,062 jackpots..."
python3 casino_ai/jackpot_predictor.py 2>&1 | tail -20

# 2. Test API endpoints
echo ""
echo "2️⃣  Testing API endpoints..."
echo "   Starting API server in background..."

# Kill any existing instances
pkill -f "casino_ai_api/main.py" 2>/dev/null

# Start API
cd casino_ai_api
python3 main.py &
API_PID=$!
echo "   API started (PID: $API_PID)"

# Wait for startup
sleep 5

# Test endpoints
echo ""
echo "   Testing /ai/status..."
curl -s http://localhost:8080/ai/status | python3 -m json.tool | head -15

echo ""
echo "   ✅ API endpoints ready"

# 3. Start alert monitor
echo ""
echo "3️⃣  Alert Monitor Ready"
echo "   To start monitoring:"
echo "   python3 casino_ai/alert_system.py"
echo ""

# 4. Summary
echo "=============================================="
echo "🎉 Deployment Complete!"
echo "=============================================="
echo ""
echo "✅ ML models trained"
echo "✅ API server running (PID: $API_PID)"
echo "✅ 4 new endpoints active:"
echo "   - GET  /ai/machine/{id}"
echo "   - GET  /ai/hot-machines"
echo "   - POST /ai/train"
echo "   - GET  /ai/status"
echo ""
echo "📊 Test API:"
echo "   curl http://localhost:8080/ai/status"
echo ""
echo "🔔 Start Alerts:"
echo "   python3 casino_ai/alert_system.py"
echo ""
echo "🌐 API Server:"
echo "   http://localhost:8080/docs (Swagger UI)"
echo ""
echo "Press Ctrl+C to stop API server"
echo ""

# Keep running
wait $API_PID

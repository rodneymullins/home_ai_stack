# Casino AI API

AI-powered slot machine analysis service for the Casino Dashboard.

## Features

- **Real-time Analysis**: Fast insights using Gemma 3 270M
- **Multiple Analysis Types**:
  - General performance overview
  - Jackpot pattern detection
  - Performance optimization
  - Anomaly detection
- **RESTful API**: Easy integration with any dashboard
- **Lightweight**: ~500MB memory footprint

## Quick Start

### Install Dependencies
```bash
cd ~/casino_ai_api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Server
```bash
python main.py
```

Server runs on `http://0.0.0.0:8080`

## API Endpoints

### Health Check
```bash
GET /health
```

### Analyze Slots
```bash
POST /analyze/slots
Content-Type: application/json

{
  "machines": [
    {
      "machine_id": "A-101",
      "location": "Main Floor",
      "denomination": 0.25,
      "jvi": 45.2,
      "win_rate": 87.5,
      "recent_jackpots": [1250, 980, 1500]
    }
  ],
  "analysis_type": "general"
}
```

**Analysis Types:**
- `general` - Overall performance summary
- `jackpot_pattern` - Jackpot frequency analysis
- `performance` - Efficiency metrics
- `anomaly` - Unusual behavior detection

## Integration with Dashboard

### Python (Flask/FastAPI)
```python
import httpx

async def get_slot_insights(machines):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://192.168.1.18:8080/analyze/slots",
            json={"machines": machines, "analysis_type": "general"}
        )
        return response.json()
```

### JavaScript/Node
```javascript
const insights = await fetch('http://192.168.1.18:8080/analyze/slots', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    machines: slotData,
    analysis_type: 'performance'
  })
}).then(r => r.json());
```

## Production Deployment

Run as systemd service:
```bash
sudo cp casino_ai_api.service /etc/systemd/system/
sudo systemctl enable casino_ai_api
sudo systemctl start casino_ai_api
```

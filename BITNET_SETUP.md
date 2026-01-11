# BitNet XL API Setup Guide

This guide covers the setup and usage of the BitNet XL API server for Open Web UI integration.

## Overview

The BitNet XL API provides an OpenAI-compatible endpoint for the mlx-bitnet 1.58-bit quantized language model. The model runs on Aragorn (M4 Mac) at `192.168.1.18:8083`.

## Quick Start

### Starting the Server

```bash
# Manual start (for testing)
cd ~/mlx-bitnet
python3 /Users/rod/Antigravity/home_ai_stack/bitnet_api_server.py

# Start as systemd service (persistent)
sudo systemctl start bitnet-api

# Enable auto-start on boot
sudo systemctl enable bitnet-api

# Check status
sudo systemctl status bitnet-api
```

### Stopping the Server

```bash
# Stop the service
sudo systemctl stop bitnet-api

# Disable auto-start
sudo systemctl disable bitnet-api
```

## Integrating with Open Web UI

1. **Navigate to Open Web UI** at `http://192.168.1.211:3000`

2. **Open Settings**:
   - Click on your profile icon
   - Select "Settings"
   - Go to "Connections" tab

3. **Add OpenAI API Connection**:
   - API Base URL: `http://192.168.1.18:8083/v1`
   - API Key: (leave empty or use any text - not required)
   - Click "Save"

4. **Verify Model Availability**:
   - Start a new chat
   - Click the model dropdown
   - Look for **mlx-bitnet-xl**

5. **Start Chatting**:
   - Select `mlx-bitnet-xl` as your model
   - Type your message and send
   - Responses will stream in real-time

## Testing the API

### Health Check
```bash
curl http://192.168.1.18:8083/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "model": "mlx-bitnet-xl",
  "mlx_available": true,
  "model_loaded": true,
  "timestamp": 1704598800
}
```

### List Available Models
```bash
curl http://192.168.1.18:8083/v1/models
```

**Expected Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "mlx-bitnet-xl",
      "object": "model",
      "created": 1704598800,
      "owned_by": "mlx-bitnet"
    }
  ]
}
```

### Test Chat Completion (Non-Streaming)
```bash
curl -X POST http://192.168.1.18:8083/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mlx-bitnet-xl",
    "messages": [
      {"role": "user", "content": "What is 2+2?"}
    ],
    "stream": false,
    "max_tokens": 100
  }'
```

### Test Chat Completion (Streaming)
```bash
curl -X POST http://192.168.1.18:8083/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mlx-bitnet-xl",
    "messages": [
      {"role": "user", "content": "Count from 1 to 5"}
    ],
    "stream": true,
    "max_tokens": 100
  }'
```

## Performance Notes

- **Token Speed**: Expect ~30-40 tokens/second on the M4 Mac
- **Memory Usage**: Model uses ~5GB of RAM (out of 16GB available)
- **Cold Start**: First request may take 10-30 seconds as model loads into memory
- **Warm Requests**: Subsequent requests are much faster

## Troubleshooting

### Server Won't Start

**Check Python Path:**
```bash
which python3
# Should show: /Volumes/Phoenix/rod/Library/Python/3.9/bin/python3
```

**Verify MLX Installation:**
```bash
python3 -c "import mlx_lm; print('MLX available')"
```

**Check Model File:**
```bash
ls -lh ~/mlx-bitnet/1bitLLM-bitnet_b1_58-xl.npz
# Should show ~5GB file
```

### Model Not Loading

**Check Logs:**
```bash
sudo journalctl -u bitnet-api -f
```

**Common Issues:**
- Model file missing: Re-run conversion with `python convert.py`
- Path issues: Ensure `export PATH=/Volumes/Phoenix/rod/Library/Python/3.9/bin:$PATH`
- Memory: Ensure at least 6GB RAM available

### Open Web UI Can't Connect

**Test from Gandalf:**
```bash
# SSH to Gandalf
ssh rod@192.168.1.211

# Test connection
curl http://192.168.1.18:8083/health
```

**Check Firewall:**
```bash
# On Aragorn
sudo lsof -i :8083
# Should show uvicorn process
```

### Slow Response Times

**Monitor System Resources:**
```bash
# Check CPU/Memory
top

# Check if model is swapping
vm_stat
```

**Reduce Load:**
- Lower `max_tokens` in requests
- Ensure no other heavy processes running
- Consider using smaller temperature values (0.3-0.5)

## Advanced Configuration

### Adjusting Server Settings

Edit `/Users/rod/Antigravity/home_ai_stack/bitnet_api_server.py`:

```python
# Change port
uvicorn.run(app, host="0.0.0.0", port=8084)  # Change from 8083

# Change default temperature
temperature: Optional[float] = 0.5  # Lower = more deterministic

# Change max tokens
max_tokens: Optional[int] = 4096  # Increase max length
```

After changes:
```bash
sudo systemctl restart bitnet-api
```

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root health check |
| `/health` | GET | Detailed health status |
| `/v1/models` | GET | List available models |
| `/v1/chat/completions` | POST | Chat completions (streaming/non-streaming) |

## Model Information

- **Name**: mlx-bitnet-xl (1bitLLM BitNet XL)
- **Quantization**: 1.58-bit (BitNet)
- **Size**: ~5GB
- **Framework**: MLX (Apple Silicon optimized)
- **Location**: `~/mlx-bitnet/1bitLLM-bitnet_b1_58-xl.npz`

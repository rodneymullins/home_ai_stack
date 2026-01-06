#!/bin/bash
# Pre-warm Qwen2.5-Coder 7B to keep it loaded in Ollama

echo "Pre-warming Qwen2.5-Coder 7B..."
curl -s -X POST http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5-coder:7b","prompt":"Ready","stream":false,"keep_alive":"24h"}' \
  > /dev/null

echo "Model warmed and will stay loaded for 24h"

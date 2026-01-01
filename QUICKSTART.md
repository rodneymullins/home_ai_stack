# Home AI Stack - Quick Reference

## Server: Thor (192.168.1.211)

### Services Running
- **Exo**: Port 8000 (75+ models)
- **Ollama**: Port 11434 (embeddings + llama3.1:8b)

### Start MCP Server
```bash
ssh 192.168.1.211
cd ~/home_ai_stack && source venv/bin/activate
python -m src.mcp_server.server
```

### Check Service Status
```bash
# Exo
curl http://192.168.1.211:8000/v1/models

# Ollama  
curl http://192.168.1.211:11434/api/tags

# System
ssh 192.168.1.211 "systemctl status ollama home-ai-exo"
```

### MCP Tools Available
- `remember(content, user_id)` - Save memory
- `recall(query, user_id)` - Search memory
- `get_all_memories(user_id)` - List all

### Files
- Config: `~/home_ai_stack/src/core/config.py`
- Server: `~/home_ai_stack/src/mcp_server/server.py`
- Test: `~/home_ai_stack/src/test_setup.py`

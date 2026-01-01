# Home AI Stack

This project implements a local-first Home AI ecosystem.

## Technology Stack
- **Interface**: MCP Server (Primary) & Open Web UI (Web Client)
- **Orchestration**: LangChain & LangGraph
- **Memory**: Mem0 (Graph + Vector Auto-Management)
- **Inference**: Exo (External/Remote) & Ollama (Local/Remote)

## Prerequisites
- Python 3.11+ (Recommended for Open Web UI)
- **Note**: The system currently has Python 3.9.6. It is highly recommended to use a virtual environment with a newer Python version if possible, as Open Web UI and modern AI libraries often require 3.10+.

## Setup
1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the MCP Server:
   ```bash
   # Test dependencies first
   python src/test_setup.py
   
   # Run the Server
   mcp run src/mcp_server/server.py
   ```
4. Run Open Web UI (in a separate terminal):
   ```bash
   open-webui serve
   ```

# AGENTS.md - Antigravity Workspace Context

## 1. System Architecture: "The Fellowship"
The infrastructure is distributed across four primary nodes.

### **Gandalf (192.168.1.211)**
*   **Role**: Persistence & Visualization Core.
*   **Databases**: 
    *   `research_papers` (PostgreSQL): Academic research ingestion.
    *   `wealth` (PostgreSQL): Personal finance & net worth.
    *   `casino_ai`: Slot machine analytics.
*   **Services**:
    *   **The One Dashboard**: Port `8004`. Unified view of all services.
    *   **PostgreSQL**: Port `5432`.

### **Aragorn**
*   **Role**: AI Compute & Inference.
*   **Services**:
    *   `Ollama`: Local LLM inference.
    *   `MLX-BitNet`: Specialized 1.58-bit model inference API.

### **Legolas (192.168.1.176)**
*   **Role**: Media, Finance Apps, DNS & Network.
*   **Services**:
    *   **Media Stack**: 
        *   Jellyfin (8096), Jellyseerr (5055), Sonarr (8989), Radarr (7878)
        *   Prowlarr (9696), qBittorrent (8082), FlareSolverr (8191)
    *   **Finance Apps**:
        *   Ghostfolio (3333), Firefly III (3334), Wenfire (3336)
        *   Portainer (3335), TubeArchivist (3337)
    *   **VPN**: Gluetun container with PIA (US Tennessee). qBittorrent routes through VPN.
    *   **DNS**: Pi-hole/Unbound (Watch out for "Self-Referential DNS" loops).
    *   **Home Assistant**: Port 8123.

### **Thor**
*   **Role**: Storage & Heavy Inference.
*   **Hardware**: RAID0 Storage Array.
*   **Services**:
    *   `Exo`: Distributed inference engine (Port `8000`). Used for router agents.
    *   `Tube Archivist`: Tiered video storage (Hot/Cold).

---

## 2. Key Projects & Locations

### **Research Paper Database**
*   **Path**: `/Users/rod/Antigravity/home_ai_stack`
*   **DB Config**: Centralized in `config.py`. Do NOT hardcode credentials.
*   **Schema Constraints**: `papers.source` field is strictly enum-checked.
    *   *Allowed*: `['arxiv', 'biorxiv', 'medrxiv', 'psyarxiv', 'pubmed', 'nber', 'ssrn', 'child_rights_ngo', 'psychology_today', 'web_scrape', 'book_reference', 'other']`
*   **Maintenance**:
    *   `verify_integrity.py`: Run this to check for duplicates/bad metadata.
    *   `cleanup_data.py`: Run this to prune bad data.
    *   `ralph_audit.py`: Run this to scan for codebase violations (Hardcoded IPs, etc.).

### **The One Dashboard**
*   **File**: `google_trends_dashboard.py` (Port 8004).
*   **Pattern**: Uses `psycopg2` Connection Pooling (`DB_POOL`). Do NOT use direct connections.
*   **Config**: Imports from `config.py`.
*   **Design**: Premium "Middle-earth" theme with glassmorphism, animated backgrounds, gold gradients.

### **Kalshi-Polymarket Arbitrage Bot**
*   **Path**: `/Users/rod/Antigravity/kalshi_bot`
*   **Status**: Production-ready V3.

---

## 3. Development Patterns & Gotchas
*   **Ralph Pattern**: We use `ralph.sh` (loop), `prd.json` (tasks), and `progress.txt` (memory).
*   **Database Constraints**: The `research_papers` DB is strict. Always check constraints (`\d papers`) before adding new source types.
*   **Logging Standard**: All ingestion scripts must log to stdout using the prefix `[INGEST]`. Example: `[INGEST] Constraint Violation: ...`.
*   **Config Priority**: Always use `from config import DB_CONFIG`. Never hardcode `192.168.1.211` in python files.
*   **Connection Pooling**: For high-traffic apps (Dashboards), use `psycopg2.pool`.

---

## 4. Completed Work (2026-01-10)
*   ✅ **Media Stack Integration**: Prowlarr (10 indexers) → Sonarr/Radarr → qBittorrent (via VPN)
*   ✅ **VPN Protection**: Gluetun + PIA configured, all torrent traffic protected
*   ✅ **Dashboard 10x Enhancement**: Premium glassmorphism theme with animations
*   ✅ **Codebase Cleanup**: High Priority violations reduced from 68 → 0

## 5. Pending Work
*   **Finance Tab Completion**: Finish embedding Ghostfolio, Firefly III, Wenfire iframes in dashboard.
*   **Firefly III Debug**: Resolve APP_KEY 500 error.
*   **Live Service Status**: Implement real-time health indicators for all services.
*   **Jellyseerr Login**: Configure user authentication for request management.

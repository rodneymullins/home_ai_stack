"""
Centralized Configuration for Home AI Stack

All database and service configurations should be imported from here.
DO NOT hardcode IPs in individual scripts.
"""

# =============================================================================
# Fellowship Server IPs
# =============================================================================
GANDALF_IP = "192.168.1.211"  # Persistence (PostgreSQL, Neo4j)
ARAGORN_IP = "192.168.1.18"   # AI Compute
LEGOLAS_IP = "192.168.1.176"  # Media/DNS/VPN

# =============================================================================
# PostgreSQL Databases (Gandalf)
# =============================================================================
DB_CONFIG = {
    'database': 'postgres',  # Default DB (jackpots, machine_specs, etc.)
    'user': 'rod',
    'host': GANDALF_IP
}

RESEARCH_DB_CONFIG = {
    'database': 'research_papers',
    'user': 'rod',
    'host': GANDALF_IP
}

WEALTH_DB_CONFIG = {
    'database': 'wealth',
    'user': 'rod',
    'host': GANDALF_IP
}

# =============================================================================
# AI Services
# =============================================================================
OLLAMA_HOST = f"http://{GANDALF_IP}:11434"  # Gandalf Ollama
BITNET_HOST = f"http://{ARAGORN_IP}:8083"   # Aragorn BitNet API
NEO4J_URL = f"http://{GANDALF_IP}:7474"     # Neo4j Browser

# =============================================================================
# Dashboard Services (for URL generation)
# =============================================================================
WEALTH_DASHBOARD_URL = f"http://{GANDALF_IP}:8005/wealth"
NETDATA_GANDALF_URL = f"http://{GANDALF_IP}:19999"
NETDATA_LEGOLAS_URL = f"http://{LEGOLAS_IP}:19999"

# Media Stack (Legolas)
SONARR_URL = f"http://{LEGOLAS_IP}:8989"
RADARR_URL = f"http://{LEGOLAS_IP}:7878"
PROWLARR_URL = f"http://{LEGOLAS_IP}:9696"
PIHOLE_URL = f"http://{LEGOLAS_IP}:8081/admin/"
SEARXNG_URL = f"http://{LEGOLAS_IP}:8080"
HOMER_URL = f"http://{LEGOLAS_IP}"
TUBEARCHIVIST_URL = f"http://{LEGOLAS_IP}:3337"

# Finance Apps (Legolas Docker)
FIREFLY_URL = f"http://{LEGOLAS_IP}:3334"
GHOSTFOLIO_URL = f"http://{LEGOLAS_IP}:3333"
WENFIRE_URL = f"http://{LEGOLAS_IP}:3336"
PORTAINER_URL = f"http://{LEGOLAS_IP}:3335"

# AI/Compute (Aragorn)
OPEN_WEBUI_URL = f"http://{ARAGORN_IP}:8080"

# =============================================================================
# Redis (if available)
# =============================================================================
REDIS_URL = "redis://localhost:6379/0"

# Home AI Stack Manual & Playbook

**Version**: 1.2 (Audited & Verified)
**Last Updated**: January 6, 2026
**Status**: Active / Production

---

## 1. System Architecture & Inventory ("The Fellowship")

### Verified Network Map
| Hostname | Role | IP Address | OS | Deployment | Key Services |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Gandalf** | AI Compute / Dashboard | 192.168.1.211 | Debian 12 | Systemd & Docker | Exo (Lead), Open WebUI, Ollama, Home AI Stack (`/home/rod/home_ai_stack`) |
| **Legolas** | Apps / Media / Gateway | 192.168.1.176 | Debian 12 | Docker | Pi-hole, Jellyfin, *Arr, Tube Archivist, Financial Stack, Home Assistant |
| **Aragorn** | AI Inference Worker | 192.168.1.18 | macOS | Native Apps | Exo.app, Ollama.app (Worker Node) |
| **Frodo/Heimdall** | *Inactive / Renamed* | - | - | - | *Not detected in audit (hostnames migrated?)* |

### Core Infrastructure
- **DNS**: Pi-hole + Unbound on **Legolas** (176).
    - *Config*: `/etc/pihole/pihole.toml` (`dns.filter_aaaa = true`).
- **Reverse Proxy**: Nginx on **Legolas** & **Gandalf**.
- **Orchestration**: Portainer on **Legolas** (`:9000`).

---

## 2. AI Service Layer
**Primary Host**: **Gandalf** (211)

### Services
- **Exo**: Distributed inference. `systemctl status exo` on Gandalf.
- **Ollama**:
    - **Gandalf**: Service (`systemctl status ollama`).
    - **Aragorn**: App (`/Applications/Ollama.app`).
- **Open WebUI**:
    - *URL*: `http://192.168.1.211:3000`
    - *Container*: `open-webui` on Gandalf.
- **Codebase**: `/home/rod/home_ai_stack` on Gandalf.

---

## 3. Media Stack ("The Archives")
**Primary Host**: **Legolas** (176)
**Location**: `/home/rod` (Docker Composes found in root)

| Service | Container | Port |
| :--- | :--- | :--- |
| **Jellyfin** | `jellyfin` | 8096 |
| **Tube Archivist** | `tubearchivist` | 8000 |
| **Jellyseerr** | `jellyseerr` | 5055 |
| **Sonarr / Radarr** | `sonarr` / `radarr` | 8989 / 7878 |
| **qBittorrent** | `qbittorrent` | 8082 |

---

## 4. Financial Stack ("The Vault")
**Primary Host**: **Legolas** (176)

| Service | Container | Port | Notes |
| :--- | :--- | :--- | :--- |
| **Ghostfolio** | `ghostfolio` | 3333 | Wealth Tracking |
| **Firefly III** | `...firefly-iii` | 8080 | Budgeting |
| **Wen Fire** | `wenfire` | - | FIRE Calculator |
| **Uptime Kuma** | `uptime-kuma` (Node) | 3001? | *Detected node_modules on host* |

---

## 5. Maintenance & Troubleshooting

### Connecting to Servers
```bash
# AI & Dashboard (Gandalf)
ssh rod@192.168.1.211

# Apps & Media (Legolas)
ssh rod@192.168.1.176

# Mac Worker (Aragorn)
ssh rod@192.168.1.18
```

### Checking Services
**On Gandalf (211):**
```bash
sudo systemctl status exo
sudo systemctl status home-ai-mcp
sudo docker ps
```

**On Legolas (176):**
```bash
sudo docker ps
# Check Pi-hole
sudo systemctl status pihole-FTL
```

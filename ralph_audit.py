import os
import re

# Ralph Audit Tool
# Scans codebase for Fellowship Pattern violations

ROOT_DIR = "."
CONFIG_FILE = "config.py"
HARDCODED_IP = "192.168.1.211"

PATTERNS = {
    "Direct DB Connection": {
        "regex": r"psycopg2\.connect\s*\(",
        "description": "Use DB_CONFIG or Connection Pool instead of direct connect",
        "severity": "HIGH"
    },
    "Hardcoded Host IP": {
        "regex": re.escape(HARDCODED_IP),
        "description": f"Found hardcoded IP {HARDCODED_IP}. Use config.DB_CONFIG",
        "severity": "HIGH"
    },
    "Missing Config Import": {
        "regex": r"import psycopg2", # If importing psycopg2, should likely import config
        "negative_regex": r"from config import",
        "description": "File interacts with DB but imports no config",
        "severity": "MEDIUM"
    },
    "Non-Standard Logging": {
        "regex": r"print\s*\([\"'](?!\[)", # print("... but not print("[...
        "description": "Log messages should start with [TAG]",
        "severity": "LOW"
    }
}

def scan_file(filepath):
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            # Skip this audit script
            if "ralph_audit.py" in filepath:
                return []

            for name, rule in PATTERNS.items():
                # For "Missing Config Import", checks are file-wide
                if name == "Missing Config Import":
                    if re.search(rule['regex'], content) and not re.search(rule['negative_regex'], content):
                        issues.append({
                            "type": name,
                            "file": filepath,
                            "line": 0,
                            "text": "File-wide check",
                            "severity": rule['severity']
                        })
                    continue

                # Line-by-line checks
                for i, line in enumerate(lines):
                    if re.search(rule['regex'], line):
                        # Filter false positives - allowed usage patterns
                        if "DB_CONFIG" in line: continue
                        if "PG_CONFIG" in line: continue  # Often assigned from DB_CONFIG
                        if "WEALTH_CONFIG" in line: continue  # Wealth DB variant
                        if "RESEARCH_DB_CONFIG" in line: continue
                        if "self.db_config" in line: continue  # Class using injected config
                        if "**config" in line.lower(): continue  # Using config dict
                        if "#" in line and "import" not in line: continue # Skip comments
                        
                        issues.append({
                            "type": name,
                            "file": filepath,
                            "line": i + 1,
                            "text": line.strip()[:60] + "...",
                            "severity": rule['severity']
                        })
    except Exception as e:
        print(f"Skipping {filepath}: {e}")
        
    return issues

def run_audit():
    print("🕵️  Ralph Codebase Audit Initiated...")
    all_issues = []
    
    for root, dirs, files in os.walk(ROOT_DIR):
        if "venv" in root or "__pycache__" in root or ".git" in root:
            continue
        if "archive" in root:  # Skip archived backups
            continue
            
        for file in files:
            if file.endswith(".py"):
                # Skip diagnostic/probe tools that intentionally test raw connections
                if file in ["probe_db.py", "test_pg.py", "test_db.py"]:
                    continue
                path = os.path.join(root, file)
                all_issues.extend(scan_file(path))

    # Report
    print(f"\n--- Audit Report ---")
    print(f"Scanned directory: {os.getcwd()}")
    print(f"Total Issues Found: {len(all_issues)}\n")
    
    # Group by Severity
    by_severity = {"HIGH": [], "MEDIUM": [], "LOW": []}
    for i in all_issues:
        by_severity[i['severity']].append(i)
        
    for sev in ["HIGH", "MEDIUM", "LOW"]:
        items = by_severity[sev]
        if items:
            print(f"\n🔴 {sev} PRIORITY ({len(items)})")
            for x in items[:15]: # Limit output
                print(f"  - {x['file']}:{x['line']} -> {x['type']}")
    
    if len(all_issues) == 0:
        print("\n✅ Codebase is CLEAN. Ralph approves.")
    else:
        print("\n⚠️  Ralph detected patterns violations. Refactor needed.")

if __name__ == "__main__":
    run_audit()

#!/bin/bash
# Quick access scripts for The Fellowship

# Add to ~/.zshrc for convenient access
cat >> ~/.zshrc << 'EOF'

# The Fellowship - Quick Access Commands
alias fellowship="~/Antigravity/home_ai_stack/fellowship_cli.sh"
alias f-status="fellowship status"
alias f-models="fellowship models"
alias f-chat="fellowship chat"
alias f-openwebui="open http://192.168.1.18:8080"
alias f-dashboard="open http://192.168.1.211"

# SSH shortcuts
alias ssh-aragorn="ssh rod@192.168.1.18"
alias ssh-gandalf="ssh rod@192.168.1.211"
alias ssh-legolas="ssh rod@192.168.1.176"

# Quick health check
f-health() {
    echo "🏰 The Fellowship Health Check"
    echo "=============================="
    curl -s http://192.168.1.18:8080 > /dev/null && echo "✅ Aragorn Open Web UI" || echo "❌ Aragorn Open Web UI"
    curl -s http://192.168.1.18:11434/api/tags > /dev/null && echo "✅ Aragorn Ollama" || echo "❌ Aragorn Ollama"
    curl -s http://192.168.1.211:8004 > /dev/null && echo " ✅ Gandalf Dashboard" || echo "❌ Gandalf Dashboard"
    curl -s http://192.168.1.211:11434/api/tags > /dev/null && echo "✅ Gandalf Ollama" || echo "❌ Gandalf Ollama"
    curl -s http://192.168.1.176:8083 > /dev/null && echo "✅ Legolas Nextcloud" || echo "❌ Legolas Nextcloud"
}

# View logs on Gandalf
f-logs() {
    local log_type=${1:-health}
    echo "📜 Viewing $log_type logs from Gandalf..."
    ssh rod@192.168.1.211 "tail -50 ~/fellowship_logs/${log_type}.log"
}

# Backup now
f-backup() {
    echo "💾 Running backup on Gandalf..."
    ssh rod@192.168.1.211 "~/fellowship_backup.sh"
}

EOF

echo "✅ Quick access commands added to ~/.zshrc"
echo ""
echo "Available commands:"
echo "  fellowship          - Main CLI"
echo "  f-status           - Quick status check"
echo "  f-health           - Quick health check"
echo "  f-models           - List all models"
echo "  f-openwebui        - Open Web UI in browser"
echo "  f-dashboard        - Open dashboard in browser"
echo "  f-logs [type]      - View logs (health|updates|backup|usage)"
echo "  f-backup           - Run backup now"
echo "  ssh-aragorn        - SSH to Aragorn"
echo "  ssh-gandalf        - SSH to Gandalf"
echo "  ssh-legolas        - SSH to Legolas"
echo ""
echo "Reload shell: source ~/.zshrc"

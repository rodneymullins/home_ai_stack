#!/bin/bash
# The Fellowship CLI - Quick access to AI services

ARAGORN="http://192.168.1.18:11434"
GANDALF="http://192.168.1.211:11434"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_help() {
    echo "🏰 The Fellowship CLI"
    echo ""
    echo "Usage: fellowship [command] [options]"
    echo ""
    echo "Commands:"
    echo "  status          - Show health status of all endpoints"
    echo "  models [node]   - List models (aragorn|gandalf|all)"
    echo "  chat <model>    - Start interactive chat"
    echo "  generate <model> <prompt> - Generate single response"
    echo "  openwebui       - Open Web UI in browser"
    echo "  dashboard       - Open Casino Dashboard"
    echo ""
    echo "Examples:"
    echo "  fellowship status"
    echo "  fellowship models aragorn"
    echo "  fellowship openwebui"
    echo "  fellowship generate llama3.1:8b 'What is AI?'"
}

check_endpoint() {
    local name=$1
    local url=$2
    if curl -s --max-time 3 "$url/api/tags" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $name${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  $name${NC}"
        return 1
    fi
}

show_status() {
    echo "🏰 The Fellowship Status"
    echo "========================"
    check_endpoint "Aragorn (AI King)" "$ARAGORN"
    check_endpoint "Gandalf (Data Keeper)" "$GANDALF"
}

list_models() {
    local node=${1:-all}
    
    case $node in
        aragorn)
            echo "🤴 Aragorn Models:"
            curl -s "$ARAGORN/api/tags" | jq -r '.models[].name' 2>/dev/null || echo "Not accessible"
            ;;
        gandalf)
            echo "🧙 Gandalf Models:"
            curl -s "$GANDALF/api/tags" | jq -r '.models[].name' 2>/dev/null || echo "Not accessible"
            ;;
        all|*)
            echo "🤴 Aragorn Models:"
            curl -s "$ARAGORN/api/tags" | jq -r '.models[].name' 2>/dev/null || echo "Not accessible"
            echo ""
            echo "🧙 Gandalf Models:"
            curl -s "$GANDALF/api/tags" | jq -r '.models[].name' 2>/dev/null || echo "Not accessible"
            ;;
    esac
}

generate_response() {
    local model=$1
    shift
    local prompt="$*"
    
    if [ -z "$model" ] || [ -z "$prompt" ]; then
        echo "Usage: fellowship generate <model> <prompt>"
        return 1
    fi
    
    echo "🤖 Generating with $model..."
    
    # Try Aragorn first
    response=$(curl -s --max-time 60 "$ARAGORN/api/generate" \
        -d "{\"model\": \"$model\", \"prompt\": \"$prompt\", \"stream\": false}" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo "$response" | jq -r '.response' 2>/dev/null || echo "Error parsing response"
    else
        # Failover to Gandalf
        echo "⚠️  Aragorn unavailable, trying Gandalf..."
        response=$(curl -s --max-time 60 "$GANDALF/api/generate" \
            -d "{\"model\": \"$model\", \"prompt\": \"$prompt\", \"stream\": false}" 2>/dev/null)
        
        if [ $? -eq 0 ] && [ -n "$response" ]; then
            echo "$response" | jq -r '.response' 2>/dev/null || echo "Error parsing response"
        else
            echo "❌ Both endpoints unavailable"
            return 1
        fi
    fi
}

# Main command handler
case "$1" in
    status)
        show_status
        ;;
    models)
        list_models "$2"
        ;;
    generate)
        shift
        generate_response "$@"
        ;;
    openwebui)
        open "http://192.168.1.18:8080"
        echo "🤖 Opening Open Web UI..."
        ;;
    dashboard)
        open "http://192.168.1.211"
        echo "📊 Opening Casino Dashboard..."
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac

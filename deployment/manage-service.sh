#!/bin/bash
#
# Service Management Script for Master Agent
#
# Usage:
#   ./manage-service.sh {start|stop|restart|status|reload}
#
# This script manages the systemd service for Master Agent with fail-safe behavior.
#

SERVICE_NAME="master-agent.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="${SCRIPT_DIR}/master-agent.service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}Error: This script must be run as root (use sudo)${NC}" >&2
        exit 1
    fi
}

# Function to install service
install_service() {
    check_root
    
    if [ ! -f "$SERVICE_FILE" ]; then
        echo -e "${RED}Error: Service file not found: $SERVICE_FILE${NC}" >&2
        exit 1
    fi
    
    echo "Installing service..."
    cp "$SERVICE_FILE" /etc/systemd/system/
    systemctl daemon-reload
    
    echo -e "${GREEN}Service installed. Use 'systemctl enable $SERVICE_NAME' to enable on boot.${NC}"
}

# Function to start service
start_service() {
    check_root
    
    echo "Starting $SERVICE_NAME..."
    systemctl start "$SERVICE_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Service started successfully${NC}"
        echo "Checking status..."
        sleep 2
        systemctl status "$SERVICE_NAME" --no-pager
    else
        echo -e "${RED}Failed to start service${NC}" >&2
        exit 1
    fi
}

# Function to stop service (with graceful shutdown)
stop_service() {
    check_root
    
    echo "Stopping $SERVICE_NAME (graceful shutdown - fail-safe mode)..."
    
    # Send SIGTERM for graceful shutdown (fail-safe)
    systemctl stop "$SERVICE_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Service stopped successfully${NC}"
    else
        echo -e "${RED}Failed to stop service${NC}" >&2
        exit 1
    fi
}

# Function to restart service
restart_service() {
    check_root
    
    echo "Restarting $SERVICE_NAME..."
    systemctl restart "$SERVICE_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Service restarted successfully${NC}"
        echo "Checking status..."
        sleep 2
        systemctl status "$SERVICE_NAME" --no-pager
    else
        echo -e "${RED}Failed to restart service${NC}" >&2
        exit 1
    fi
}

# Function to reload service (graceful reload)
reload_service() {
    check_root
    
    echo "Reloading $SERVICE_NAME (graceful reload)..."
    systemctl reload "$SERVICE_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Service reloaded successfully${NC}"
    else
        echo -e "${YELLOW}Reload failed or not supported. Trying restart...${NC}"
        restart_service
    fi
}

# Function to show service status
show_status() {
    echo "Service Status for $SERVICE_NAME:"
    echo "=================================="
    systemctl status "$SERVICE_NAME" --no-pager
    
    echo ""
    echo "Recent logs:"
    echo "=================================="
    journalctl -u "$SERVICE_NAME" -n 20 --no-pager
}

# Function to show help
show_help() {
    echo "Master Agent Service Management"
    echo ""
    echo "Usage: $0 {start|stop|restart|reload|status|install|help}"
    echo ""
    echo "Commands:"
    echo "  start     - Start the service"
    echo "  stop      - Stop the service (graceful shutdown - fail-safe)"
    echo "  restart   - Restart the service"
    echo "  reload    - Reload the service (graceful reload)"
    echo "  status    - Show service status and recent logs"
    echo "  install   - Install the service file (requires root)"
    echo "  help      - Show this help message"
    echo ""
    echo "Fail-Safe Behavior:"
    echo "  - When service stops, new requests are rejected (fail-safe)"
    echo "  - In-flight requests are allowed to complete gracefully"
    echo "  - Service waits up to 30 seconds for requests to complete"
    echo ""
}

# Main script logic
case "${1:-}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    reload)
        reload_service
        ;;
    status)
        show_status
        ;;
    install)
        install_service
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Error: Unknown command: ${1:-}${NC}" >&2
        echo ""
        show_help
        exit 1
        ;;
esac



#!/bin/bash

set -e

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"

print_status() {
    printf "\e[1;34m>>> %s\e[0m\n" "$1"
}

print_error() {
    printf "\e[1;31mERROR: %s\e[0m\n" "$1"
}

if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (sudo)"
    exit 1
fi

# Pull latest changes as the invoking user, not root
print_status "Pulling latest changes..."
if [ -n "$SUDO_USER" ]; then
    sudo -u "$SUDO_USER" git -C "$INSTALL_DIR" pull
else
    git -C "$INSTALL_DIR" pull
fi

# Sync dependencies
print_status "Syncing dependencies..."
uv sync --project "$INSTALL_DIR"

# Restart running services
print_status "Restarting services..."
SERVICES=("fetchsensors" "updateoled")
for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service.service"; then
        systemctl restart "$service.service"
        print_status "$service.service restarted"
    else
        print_status "$service.service is not active, skipping"
    fi
done

print_status "Update complete!"

#!/bin/bash

# Exit on error
set -e

# Default values
DEFAULT_INSTALL_DIR="$(pwd)"
DEFAULT_USER="pi"
DEFAULT_GROUP="pi"

# Function to print in color
print_status() {
    echo -e "\e[1;34m>>> $1\e[0m"
}

print_error() {
    echo -e "\e[1;31mERROR: $1\e[0m"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run as root (sudo)"
    exit 1
fi

# Get installation directory
read -p "Enter installation directory [$DEFAULT_INSTALL_DIR]: " INSTALL_DIR
INSTALL_DIR=${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}

# Ensure absolute path
if [[ "$INSTALL_DIR" != /* ]]; then
    INSTALL_DIR="$(pwd)/$INSTALL_DIR"
fi

# Get user input
read -p "Enter user to run services [$DEFAULT_USER]: " SERVICE_USER
SERVICE_USER=${SERVICE_USER:-$DEFAULT_USER}

read -p "Enter group for services [$DEFAULT_GROUP]: " SERVICE_GROUP
SERVICE_GROUP=${SERVICE_GROUP:-$DEFAULT_GROUP}

# Verify user exists
if ! id "$SERVICE_USER" &>/dev/null; then
    print_error "User $SERVICE_USER does not exist!"
    exit 1
fi

# Verify group exists
if ! getent group "$SERVICE_GROUP" &>/dev/null; then
    print_error "Group $SERVICE_GROUP does not exist!"
    exit 1
fi

print_status "Installing system dependencies..."
apt-get update
apt-get install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    i2c-tools \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7 \
    libtiff6 \
    jq

# Handle installation directory
if [ "$INSTALL_DIR" != "$DEFAULT_INSTALL_DIR" ]; then
    print_status "Creating installation directory..."
    mkdir -p "$INSTALL_DIR"
    
    print_status "Copying files..."
    cp -r ./* "$INSTALL_DIR/"
else
    print_status "Installing in current directory, skipping file copy..."
fi

# Create and activate virtual environment
print_status "Setting up Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"

# Install Python packages
print_status "Installing Python packages..."
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Set permissions
print_status "Setting permissions..."
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"/*.py

# Configure and install services
print_status "Configuring systemd services..."
SERVICES=("updateoled" "fetchsensors")

for service in "${SERVICES[@]}"; do
    read -p "Install $service service? [Y/n]: " install_service
    install_service=${install_service:-Y}
    
    if [[ $install_service =~ ^[Yy] ]]; then
        # Create temporary file for service configuration
        tmp_service=$(mktemp)
        cp "$INSTALL_DIR/$service.service" "$tmp_service"
        
        # Update service configuration
        sed -i "s|User=pi|User=$SERVICE_USER|" "$tmp_service"
        sed -i "s|Group=pi|Group=$SERVICE_GROUP|" "$tmp_service"
        sed -i "s|WorkingDirectory=/usr/local/raspi-status|WorkingDirectory=$INSTALL_DIR|" "$tmp_service"
        sed -i "s|/usr/local/raspi-status/venv|$INSTALL_DIR/venv|g" "$tmp_service"
        
        # Install service file
        mv "$tmp_service" "/etc/systemd/system/$service.service"
        
        # Ask about enabling and starting
        read -p "Enable $service service to start at boot? [Y/n]: " enable_service
        enable_service=${enable_service:-Y}
        
        if [[ $enable_service =~ ^[Yy] ]]; then
            systemctl enable "$service.service"
            print_status "$service.service enabled"
            
            read -p "Start $service service now? [Y/n]: " start_service
            start_service=${start_service:-Y}
            
            if [[ $start_service =~ ^[Yy] ]]; then
                systemctl start "$service.service"
                print_status "$service.service started"
            fi
        fi
    fi
done

# Reload systemd to pick up new/changed service files
systemctl daemon-reload

print_status "Installation complete!"
echo
echo "Service management commands:"
echo "  Start:  sudo systemctl start <service>"
echo "  Stop:   sudo systemctl stop <service>"
echo "  Status: sudo systemctl status <service>"
echo "  Logs:   sudo journalctl -u <service> -f"
echo
echo "Available services:"
for service in "${SERVICES[@]}"; do
    if [ -f "/etc/systemd/system/$service.service" ]; then
        echo "  - $service.service"
    fi
done
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

APP_DIR="$PWD"
APP_USER="${SUDO_USER:-$USER}"

echo "Installing system packages for Handy IoT..."
sudo apt update
sudo apt install -y python3-pygame python3-venv python3-pip mpv ffmpeg \
  fonts-dejavu-core libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-mixer-2.0-0 libsdl2-ttf-2.0-0

echo "Adding $APP_USER to device groups..."
for group in audio video render input; do
  if getent group "$group" >/dev/null 2>&1; then
    sudo usermod -aG "$group" "$APP_USER"
  fi
done

echo "Creating Python environment..."
python3 -m venv --system-site-packages --clear .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if ! .venv/bin/python -c "import pygame" >/dev/null 2>&1; then
  echo "python3-pygame was not importable, installing pygame-ce from source..."
  sudo apt install -y libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev build-essential python3-dev
  .venv/bin/pip install pygame-ce --no-binary pygame-ce
fi

if [ ! -f config.json ]; then
  cp config.example.json config.json
fi

sudo chown -R "$APP_USER":"$APP_USER" .venv config.json

echo "Installing kiosk and MCP services..."
for service in handy-iot handy-mcp; do
  sudo cp "systemd/${service}.service" "/etc/systemd/system/${service}.service"
  sudo sed -i "s|__USER__|$APP_USER|g; s|__DIR__|$APP_DIR|g" "/etc/systemd/system/${service}.service"
done
sudo systemctl daemon-reload
sudo systemctl enable handy-iot.service handy-mcp.service

if command -v raspi-config >/dev/null 2>&1; then
  sudo raspi-config nonint do_blanking 1 || true
fi

chmod +x run.sh

echo
echo "Install complete."
echo "1. Open Google Calendar settings, copy the public iCal address of the calendar"
echo "   and paste it into $APP_DIR/config.json under calendar.ics_url."
echo "   You can also set it later on the Settings screen of the app."
echo "2. Start the dashboard and MCP server with: sudo systemctl start handy-iot"
echo "3. View logs with: journalctl -u handy-iot -u handy-mcp -f"
echo "4. Stop both with: sudo systemctl stop handy-iot"
echo "5. The local MCP endpoint is http://127.0.0.1:8765/mcp"
echo
echo "The service uses KMSDRM directly on tty1. If your touchscreen is rotated,"
echo "rotate it at the OS level (config.txt display_rotate or video=...,rotate=90)."

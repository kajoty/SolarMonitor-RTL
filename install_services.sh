#!/bin/bash
# Installiert systemd-Services für SolarMonitor Minimal-Setup

set -e

echo "🔧 Installiere SolarMonitor systemd-Services..."

# Kopiere Service-Dateien
sudo cp solarmonitor-postgres.service /etc/systemd/system/
sudo cp solarmonitor-hackrf.service /etc/systemd/system/
sudo cp solarmonitor-hackrf.timer /etc/systemd/system/
sudo cp solarmonitor-rtl.service /etc/systemd/system/
sudo cp solarmonitor-rtl.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable solarmonitor-postgres.service
sudo systemctl enable solarmonitor-hackrf.timer
sudo systemctl enable solarmonitor-rtl.timer

echo ""
echo "✅ Services installiert!"
echo ""
echo "📋 Verfügbare Services:"
echo "  solarmonitor-postgres.service  - REST API (läuft dauerhaft)"
echo "  solarmonitor-hackrf.timer      - HackRF Scanner (alle 5 Min)"
echo "  solarmonitor-rtl.timer         - RTL-SDR Scanner (alle 5 Min)"
echo ""
echo "🚀 Starten:"
echo "  sudo systemctl start solarmonitor-postgres.service"
echo "  sudo systemctl start solarmonitor-hackrf.timer"
echo "  sudo systemctl start solarmonitor-rtl.timer"
echo ""
echo "📊 Status prüfen:"
echo "  sudo systemctl status solarmonitor-postgres.service"
echo "  sudo systemctl list-timers solarmonitor-*"
echo ""
echo "📝 Logs:"
echo "  sudo journalctl -u solarmonitor-postgres.service -f"
echo "  sudo journalctl -u solarmonitor-hackrf.service -f"
echo "  sudo journalctl -u solarmonitor-rtl.service -f"

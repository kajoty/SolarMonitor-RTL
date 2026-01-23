#!/bin/bash
# Deinstalliert die systemd-Services für das SolarMonitor-Setup

set -e

echo "🗑️ Deinstalliere SolarMonitor systemd-Services..."

SERVICES=("solarmonitor-web.service" "solarmonitor-heatmap.service" "solarmonitor-rtl.service")
TIMERS=("solarmonitor-rtl.timer")

# Timers stoppen und deaktivieren
echo "Stoppe Timer..."
for timer in "${TIMERS[@]}"; do
    if systemctl is-active --quiet "$timer"; then
        sudo systemctl stop "$timer"
    fi
    sudo systemctl disable "$timer" || true
done

# Services stoppen und deaktivieren
echo "Stoppe Services..."
for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service"; then
        sudo systemctl stop "$service"
    fi
    sudo systemctl disable "$service" || true
done

# Dateien aus /etc/systemd/system/ löschen
echo "Entferne Service-Dateien..."
for file in "${SERVICES[@]}" "${TIMERS[@]}"; do
    if [ -f "/etc/systemd/system/$file" ]; then
        sudo rm "/etc/systemd/system/$file"
    fi
done

# Systemd neu laden
sudo systemctl daemon-reload
sudo systemctl reset-failed

echo ""
echo "✅ Alle SolarMonitor Services wurden entfernt!"
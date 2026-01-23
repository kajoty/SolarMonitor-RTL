#!/bin/bash
# Installiert die systemd-Services für das SolarMonitor-Setup

set -e

echo "🔧 Installiere SolarMonitor systemd-Services..."

# Prüfen, ob die Service-Dateien existieren, bevor sie kopiert werden
FILES=("solarmonitor-web.service" "solarmonitor-heatmap.service" "solarmonitor-rtl.service" "solarmonitor-rtl.timer")

for file in "${FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Fehler: $file nicht gefunden!"
        exit 1
    fi
done

# Kopiere Service- und Timer-Dateien
sudo cp solarmonitor-web.service /etc/systemd/system/
sudo cp solarmonitor-heatmap.service /etc/systemd/system/
sudo cp solarmonitor-rtl.service /etc/systemd/system/
sudo cp solarmonitor-rtl.timer /etc/systemd/system/

# Systemd neu laden, um neue Dateien zu erkennen
sudo systemctl daemon-reload

# Services und Timer aktivieren (Autostart bei Boot)
sudo systemctl enable solarmonitor-web.service
sudo systemctl enable solarmonitor-heatmap.service
sudo systemctl enable solarmonitor-rtl.timer

echo ""
echo "✅ Services erfolgreich installiert!"
echo ""
echo "📋 Verfügbare Services:"
echo "  solarmonitor-web.service     - Flask Web Interface (Dauerbetrieb)"
echo "  solarmonitor-heatmap.service - Automatischer Bild-Export (Dauerbetrieb)"
echo "  solarmonitor-rtl.timer       - RTL-SDR Scanner (Alle 5 Minuten)"
echo ""
echo "🚀 Manuell starten:"
echo "  sudo systemctl start solarmonitor-web.service"
echo "  sudo systemctl start solarmonitor-heatmap.service"
echo "  sudo systemctl start solarmonitor-rtl.timer"
echo ""
echo "📊 Status prüfen:"
echo "  sudo systemctl status solarmonitor-web.service"
echo "  sudo systemctl list-timers solarmonitor-*"
echo ""
echo "📝 Logs einsehen:"
echo "  sudo journalctl -u solarmonitor-web.service -f"
echo "  sudo journalctl -u solarmonitor-rtl.service -f"
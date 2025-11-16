#!/bin/bash

# SolarMonitor-RTL Systemd Service Installer
# Installiert und aktiviert den Service für dauerhaften Betrieb

set -e

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║     SolarMonitor-RTL - Systemd Service Installation                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Farben
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Prüfungen
echo -e "${YELLOW}1️⃣ Systemd Umgebung prüfen...${NC}"

if ! command -v systemctl &> /dev/null; then
    echo -e "${RED}❌ systemctl nicht gefunden. Systemd nicht installiert?${NC}"
    exit 1
fi

echo -e "${GREEN}✅ systemctl gefunden${NC}"
echo ""

# Prüfe ob Service-Datei existiert
echo -e "${YELLOW}2️⃣ Service-Datei prüfen...${NC}"

SERVICE_FILE="/home/pi/Projekte/solarmonitor/SolarMonitor-RTL/solarmonitor-rtl.service"

if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${RED}❌ Service-Datei nicht gefunden: $SERVICE_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Service-Datei gefunden${NC}"
echo ""

# Kopiere Service-Datei nach /etc/systemd/system/
echo -e "${YELLOW}3️⃣ Service-Datei installieren...${NC}"
echo "   Kopiere $SERVICE_FILE nach /etc/systemd/system/"

if ! sudo cp "$SERVICE_FILE" /etc/systemd/system/solarmonitor-rtl.service; then
    echo -e "${RED}❌ Fehler beim Kopieren. Benötige Sudo-Rechte.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Service-Datei installiert${NC}"
echo ""

# Setze richtige Berechtigungen
echo -e "${YELLOW}4️⃣ Berechtigungen setzen...${NC}"
sudo chmod 644 /etc/systemd/system/solarmonitor-rtl.service
echo -e "${GREEN}✅ Berechtigungen gesetzt${NC}"
echo ""

# Reload systemd daemon
echo -e "${YELLOW}5️⃣ Systemd konfiguration neu laden...${NC}"
sudo systemctl daemon-reload
echo -e "${GREEN}✅ Systemd konfiguration neu geladen${NC}"
echo ""

# Aktiviere Service
echo -e "${YELLOW}6️⃣ Service aktivieren (Auto-Start)...${NC}"

if ! sudo systemctl enable solarmonitor-rtl.service; then
    echo -e "${RED}❌ Fehler beim Aktivieren des Services${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Service aktiviert (startet automatisch bei Boot)${NC}"
echo ""

# Starte Service
echo -e "${YELLOW}7️⃣ Service starten...${NC}"

if ! sudo systemctl start solarmonitor-rtl.service; then
    echo -e "${RED}❌ Fehler beim Starten des Services${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Service gestartet${NC}"
echo ""

# Status prüfen
echo -e "${YELLOW}8️⃣ Service-Status prüfen...${NC}"
echo ""

sudo systemctl status solarmonitor-rtl.service --no-pager || true

echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo -e "${GREEN}✅ INSTALLATION ABGESCHLOSSEN${NC}"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Dashboard läuft jetzt auf: http://localhost:5000/"
echo "🔍 Discovery läuft jetzt auf: http://localhost:5000/discovery"
echo ""
echo "🔧 Nützliche Kommandos:"
echo ""
echo "   Status prüfen:"
echo "   $ sudo systemctl status solarmonitor-rtl"
echo ""
echo "   Service stoppen:"
echo "   $ sudo systemctl stop solarmonitor-rtl"
echo ""
echo "   Service neu starten:"
echo "   $ sudo systemctl restart solarmonitor-rtl"
echo ""
echo "   Logs anschauen (live):"
echo "   $ sudo journalctl -u solarmonitor-rtl -f"
echo ""
echo "   Logs anschauen (letzte 50 Zeilen):"
echo "   $ sudo journalctl -u solarmonitor-rtl -n 50"
echo ""
echo "   Auto-Start deaktivieren:"
echo "   $ sudo systemctl disable solarmonitor-rtl"
echo ""
echo "   Service deinstallieren:"
echo "   $ sudo systemctl disable solarmonitor-rtl"
echo "   $ sudo systemctl stop solarmonitor-rtl"
echo "   $ sudo rm /etc/systemd/system/solarmonitor-rtl.service"
echo "   $ sudo systemctl daemon-reload"
echo ""

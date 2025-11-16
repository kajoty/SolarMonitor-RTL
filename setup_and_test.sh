#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║         SolarMonitor-RTL - Setup & Test Assistent                         ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Farben für Output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check Python
echo -e "${YELLOW}1️⃣ Python Version prüfen...${NC}"
python3 --version
echo ""

# Step 2: Create venv
echo -e "${YELLOW}2️⃣ Virtual Environment erstellen...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ venv erstellt${NC}"
else
    echo -e "${GREEN}✅ venv existiert bereits${NC}"
fi
echo ""

# Step 3: Activate venv
echo -e "${YELLOW}3️⃣ Virtual Environment aktivieren...${NC}"
source venv/bin/activate
echo -e "${GREEN}✅ venv aktiviert${NC}"
echo ""

# Step 4: Install dependencies
echo -e "${YELLOW}4️⃣ Dependencies installieren (kann 5-10 Min dauern)...${NC}"
pip install --upgrade pip > /dev/null 2>&1
echo "   Installiere: python-dotenv, influxdb, flask, numpy, matplotlib, scipy, pillow..."
pip install -q python-dotenv influxdb flask flask-cors requests scipy pillow
echo "   Installiere: numpy, matplotlib (kann länger dauern auf Pi)..."
pip install -q numpy matplotlib

# Optional: rtl-sdr (kann fehlschlagen wenn rtlsdr lib nicht vorhanden)
echo "   Versuche rtl-sdr zu installieren..."
pip install -q rtl-sdr 2>/dev/null && echo -e "${GREEN}✅ rtl-sdr installiert${NC}" || echo -e "${YELLOW}⚠️  rtl-sdr nicht verfügbar (benötigt libusb)${NC}"

echo -e "${GREEN}✅ Dependencies installiert${NC}"
echo ""

# Step 5: Check imports
echo -e "${YELLOW}5️⃣ Imports testen...${NC}"
python3 << 'PYTHON_TEST'
import sys
modules = ['dotenv', 'flask', 'numpy', 'matplotlib', 'scipy', 'PIL', 'influxdb']
success_count = 0

for module in modules:
    try:
        __import__(module)
        print(f"   ✅ {module}")
        success_count += 1
    except ImportError:
        print(f"   ❌ {module}")

try:
    import rtlsdr
    print(f"   ✅ rtlsdr")
    success_count += 1
except ImportError:
    print(f"   ⚠️  rtlsdr (optional - benötigt RTL-SDR Hardware)")

print(f"\n   {success_count}/7 Module verfügbar")
PYTHON_TEST
echo ""

# Step 6: Create .env if not exists
echo -e "${YELLOW}6️⃣ .env Datei prüfen...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ .env erstellt (von .env.example)${NC}"
else
    echo -e "${GREEN}✅ .env existiert bereits${NC}"
fi
echo ""

# Step 7: Show available tests
echo -e "${YELLOW}7️⃣ Verfügbare Tests:${NC}"
echo ""
echo "   Syntax-Check (alle Python-Dateien):"
echo "   $ python3 -m py_compile *.py"
echo ""
echo "   Imports testen:"
echo "   $ python3 -c 'from heatmap_generator import create_heatmap_generator_from_env; print(\"✅ OK\")'"
echo ""
echo "   RTL-SDR Gain-Werte testen (mit Hardware):"
echo "   $ python3 test_rtl_gains.py"
echo ""
echo "   Flask Server starten:"
echo "   $ python3 app.py"
echo ""
echo "   Discovery UI öffnen:"
echo "   → http://localhost:5000/discovery"
echo ""
echo "   Heatmap Dashboard öffnen:"
echo "   → http://localhost:5000/"
echo ""

echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Setup abgeschlossen! Bereit zum Testen.${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Nächste Schritte:"
echo "1. Virtual Environment aktivieren:"
echo "   $ source venv/bin/activate"
echo ""
echo "2. Flask Server starten:"
echo "   $ python3 app.py"
echo ""


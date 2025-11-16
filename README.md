# 📡 SolarMonitor-RTL - RTL-SDR Frequency Monitor

Ein **neues Projekt** für RTL-SDR basiertes Frequenz-Monitoring auf dem Raspberry Pi.

## Hardware
- **RTL2838 DVB-T USB Stick** (Realtek Semiconductor)
- Raspberry Pi 4B

## Status
🔨 **In Development** - Projekt wird gerade aufgebaut

## Ziele
- [ ] RTL-SDR Scanning-Engine
- [ ] InfluxDB Integration
- [ ] Web Dashboard
- [ ] Alerts & Monitoring

## Start
```markdown
# 📡 SolarMonitor-RTL - RTL-SDR Frequency Monitor

Ein **neues Projekt** für RTL-SDR basiertes Frequenz-Monitoring auf dem Raspberry Pi.

## Hardware
- **RTL2838 DVB-T USB Stick** (Realtek Semiconductor)
- Raspberry Pi 4B

## Status
🔨 **In Development** - Projekt wird gerade aufgebaut

## Features
- ✅ FFT Spektrum Heatmaps mit Zeit-Frequenz Visualisierung
- ✅ Automatische Frequenzbereich Discovery & Scanning
- ✅ REST API für Heatmaps und Scanner
- ✅ Web Dashboards (Heatmap + Discovery)
- ✅ Systemd Service für 24/7 Betrieb
- ✅ Konfigurierbare Gain-Einstellungen

## Ziele
- [x] RTL-SDR Scanning-Engine
- [x] Web Dashboard mit FFT Heatmaps
- [x] Frequenzbereich Discovery
- [ ] InfluxDB Integration für Datenspeicherung
- [ ] Alerts & Monitoring

## Quick Start

### 1️⃣ Installation

```bash
cd /home/pi/Projekte/solarmonitor/SolarMonitor-RTL
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2️⃣ Als Systemd Service starten (empfohlen)

```bash
bash install_service.sh
```

Das Service startet automatisch beim Boot und läuft 24/7.

**Dashboards verfügbar unter:**
- Heatmap Dashboard: `http://localhost:5000/`
- Discovery UI: `http://localhost:5000/discovery`

### 3️⃣ Manueller Start (für Entwicklung)

```bash
source venv/bin/activate
python3 app.py
```

## Systemd Service Verwaltung

```bash
# Status prüfen
sudo systemctl status solarmonitor-rtl

# Service stoppen
sudo systemctl stop solarmonitor-rtl

# Service neu starten
sudo systemctl restart solarmonitor-rtl

# Live Logs anschauen
sudo journalctl -u solarmonitor-rtl -f

# Letzte 50 Logs
sudo journalctl -u solarmonitor-rtl -n 50

# Auto-Start deaktivieren
sudo systemctl disable solarmonitor-rtl

# Service deinstallieren
sudo systemctl disable solarmonitor-rtl
sudo systemctl stop solarmonitor-rtl
sudo rm /etc/systemd/system/solarmonitor-rtl.service
sudo systemctl daemon-reload
```

## Dokumentation

- 📄 **QUICKSTART.md** - Quick Start Anleitung
- 📄 **HEATMAP_GUIDE.md** - FFT Heatmap API & Beispiele
- 📄 **FREQUENCY_DISCOVERY_GUIDE.md** - Discovery API & Beispiele
- 📄 **.github/copilot-instructions.md** - AI-Agent Dokumentation

## Komponenten

### FFT Heatmap Generator
- Spektraldaten aus InfluxDB abrufen
- Zeit-Frequenz Heatmaps visualisieren
- Verschiedene Zeiträume (1h, 6h, 24h, 7d, 30d)
- 17+ Colormaps

### Frequenzbereich Discovery
- Automatisches Scannen von 11 Frequenzbereichen
- SNR und Aktivitätsberechnung
- Intelligente Empfehlungen
- Mehrere Visualisierungstypen

## REST API

### Heatmap Endpoints
```
GET  /api/heatmap              - Spektraldaten Heatmap
GET  /api/time-ranges          - Verfügbare Zeiträume
GET  /api/colormaps            - Verfügbare Colormaps
GET  /api/health               - InfluxDB Status
```

### Discovery Endpoints
```
POST /api/scan/start           - Scan starten
GET  /api/scan/status          - Scan Status
GET  /api/scan/results         - Scan Ergebnisse
GET  /api/scan/recommendations - Empfehlungen
GET  /api/scan/visualization   - Grafiken (PNG/Base64)
```

## RTL-SDR Konfiguration

**Gain-Einstellungen in `.env`:**
```env
RTL_GAIN=auto              # Automatisch (default)
RTL_GAIN=25.4              # Empfohlen für Balance
RTL_GAIN=35.0              # Für schwache Signale
```

**Gain-Werte ermitteln (mit Hardware):**
```bash
python3 test_rtl_gains.py
```

## Testing

### Demo ohne Hardware
```bash
python3 demo_test.py
```

### Mit Mock-Daten
```bash
python3 app.py
# Browser: http://localhost:5000/discovery
```

## Anforderungen

- Python 3.8+
- RTL-SDR Hardware (optional, für echte Scans)
- InfluxDB (optional, für Datenspeicherung)

## Dependencies

```
python-dotenv
influxdb
flask
flask-cors
requests
rtl-sdr
numpy
matplotlib
scipy
pillow
```

## Lizenz

SolarMonitor-RTL © 2025 kajoty
```

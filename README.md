# 📡 SolarMonitor-RTL - RTL-SDR Frequency Monitoring

Ein professionelles **RTL-SDR Frequenz-Monitoring System** für Raspberry Pi mit InfluxDB Integration, FFT Heatmap-Visualisierung und Web-Dashboard.

## 🎯 Überblick

SolarMonitor-RTL ist ein vollständiges System zur kontinuierlichen Überwachung von Funkfrequenzen mit einem RTL2838 DVB-T USB Dongle. Das System erfasst Spektrumdaten, speichert sie in InfluxDB und bietet umfassende Visualisierungen sowie REST APIs für Integration.

**Status:** ✅ **Produktionsreife** - Alle Komponenten getestet und funktionsfähig  
**Deployment:** ✅ **24/7 Betrieb** - Via Systemd Service mit Auto-Restart  

## 🚀 Features

| Feature | Beschreibung |
|---------|-------------|
| 📊 **FFT Heatmap Generator** | Spektrumvisualisierung über Zeit mit 17+ Colormaps |
| 🔍 **RTL-SDR Scanner** | Automatische Frequenzbereich-Analyse mit SNR/Power Metriken |
| 💾 **InfluxDB Integration** | Zeitreihen-Datenspeicherung für langfristige Analysen |
| 🌐 **REST API** | Vollständige Schnittstelle für Integration und Automatisierung |
| 📱 **Web Dashboards** | Moderne, responsive UIs für Heatmaps und Frequenzentdeckung |
| 🔄 **Systemd Service** | 24/7 automatischer Betrieb mit Auto-Start nach Reboot |
| ⚙️ **Flexible Konfiguration** | Umgebungsvariablen für alle Parameter |
| 📋 **Professionelles Logging** | Strukturiertes Logging zu Syslog/Journal |

## 💻 Hardware-Anforderungen

### Minimal Setup
- **Raspberry Pi 4B** (2GB+ RAM) mit Raspbian/Debian OS
- **RTL2838 DVB-T USB Dongle** (Realtek Semiconductor)
  - USB IDs: `0bda:2838`
  - Tuner: Rafael Micro R828D
  - Frequenzbereich: 24-1766 MHz (optimiert 470-862 MHz DVB-T)

### Optional
- **InfluxDB Server** (lokal oder remote, z.B. `192.168.178.100:8086`)
  - Für Datenspeicherung und Langzeit-Analysen
  - Default: `localhost:8086`

## 📦 Installation

### 1. Repository Clone & Virtual Environment

```bash
cd /home/pi/Projekte/solarmonitor
git clone https://github.com/kajoty/SolarMonitor-RTL.git
cd SolarMonitor-RTL

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Konfiguration

**`.env` erstellen** (basierend auf `.env.example`):
```bash
cp .env.example .env
nano .env  # Anpassen falls nötig
```

**Standard-Konfiguration:**
```env
# RTL-SDR
RTL_DEVICE_INDEX=0          # Gerät-Index (0 für erstes Gerät)
RTL_SAMPLE_RATE=2000000     # Sample Rate in Hz
RTL_GAIN=42.1               # Gain in dB (0-49.6 oder 'auto')

# InfluxDB (optional)
INFLUXDB_HOST=192.168.178.100
INFLUXDB_PORT=8086
INFLUXDB_USER=admin
INFLUXDB_PASSWORD=admin
INFLUXDB_DATABASE=rtl_monitor

# Automatischer Scan
SCAN_INTERVAL_MINUTES=3     # Scan-Frequenz
```

### 3. Systemd Service (Empfohlen)

```bash
sudo bash install_service.sh
```

Dies:
- Kopiert Service-Datei zu `/etc/systemd/system/`
- Aktiviert Auto-Start beim Reboot
- Startet den Service sofort

### 4. Systemd Verwaltung

```bash
# Status prüfen
sudo systemctl status solarmonitor-rtl

# Service neu starten
sudo systemctl restart solarmonitor-rtl

# Live Logs anschauen
sudo journalctl -u solarmonitor-rtl -f

# Letzte 50 Log-Einträge
sudo journalctl -u solarmonitor-rtl -n 50

# Service stoppen
sudo systemctl stop solarmonitor-rtl

# Auto-Start deaktivieren
sudo systemctl disable solarmonitor-rtl
```

## 🚀 Quick Start (Entwicklung)

### Manueller Start ohne Systemd

```bash
source venv/bin/activate
python3 app.py
```

**Output:**
```
INFO:__main__:InfluxDB verbunden: 192.168.178.100:8086/rtl_monitor
INFO:__main__:RTL-SDR Scanner erfolgreich initialisiert
INFO:__main__:✅ Scheduler gestartet - Scans alle 3 Minuten
 * Running on http://0.0.0.0:5000
```

### Web Interfaces

Öffnen Sie im Browser:

1. **Heatmap Dashboard** → `http://localhost:5000/`
   - FFT Spektraldaten visualisieren
   - Zeiträume wählen (1h, 6h, 24h, 7d, 30d)
   - Colormaps anpassen (viridis, plasma, jet, etc.)
   - PNG Download

2. **Discovery Dashboard** → `http://localhost:5000/discovery`
   - RTL-SDR Frequenzbereiche scannen
   - SNR und Aktivität pro Band sehen
   - Beste Bänder empfohlen bekommen
   - Spektrum-Visualisierungen

## 🧬 Architektur

### Komponenten

```
┌─────────────────────────────────────────────┐
│          Flask REST API (app.py)            │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────┐  ┌──────────────────┐ │
│  │ Heatmap Generator│  │ Frequency Scanner│ │
│  │ (heatmap_gen)    │  │ (frequency_scan) │ │
│  └────────┬─────────┘  └─────────┬────────┘ │
│           │                      │          │
│           └──────────┬───────────┘          │
│                      │                      │
│                  InfluxDB                   │
│            (Time-Series Database)           │
│                                             │
└─────────────────────────────────────────────┘
         RTL-SDR USB Dongle
       (RTL2838 / Rafael Micro)
```

### Module

| Datei | Beschreibung |
|-------|------------|
| `app.py` | Flask REST API Server, Route Handler, Scheduler |
| `frequency_scanner.py` | RTL-SDR Hardware Interface, Frequenz-Analyser |
| `heatmap_generator.py` | InfluxDB Query, FFT Heatmap Rendering |
| `spectrum_analyzer.py` | Spektrum-Visualisierungen (4 Chart-Typen) |
| `templates/dashboard.html` | Web UI für Heatmaps |
| `templates/discovery.html` | Web UI für Frequenz Discovery |

## 📡 RTL-SDR Konfiguration

### Frequenzbänder (vordefiniert)

Der Scanner überprüft diese 5 Hauptbänder:

| Band | Frequenz | Typ | Nutzung |
|------|----------|------|---------|
| FM Radio | 87.5-108 MHz | UKW Rundfunk | Lokale Radiostationen |
| VHF | 46-230 MHz | Analog/Digital | TV, Funkverkehr |
| UHF | 470-862 MHz | **DVB-T (Standard)** | TV, Messdaten |
| Mobilfunk | 890-960 MHz | GSM-900 | Mobilfunknetzwerk |
| L-Band | 1400-1500 MHz | Satellit/ISM | Diverse Dienste |

**Pro Band werden 150 Frequenzen gescannt** (ca. 0.137 MHz Auflösung)

### Gain-Einstellungen

```env
RTL_GAIN=auto              # Automatisch (LoVNA-Filter, Standard)
RTL_GAIN=25.4              # Guter Balance (empfohlen)
RTL_GAIN=35.0              # Schwache Signale
RTL_GAIN=42.1              # Starke Verstärkung (aktuell in .env)
RTL_GAIN=49.6              # Maximal (viel Rauschen)
```

**Optimale Gains finden:**
```bash
python3 test_rtl_gains.py
```

## 🌐 REST API

### Heatmap Endpoints

```bash
# Heatmap generieren (JSON oder PNG)
GET /api/heatmap?time_range=24h&cmap=viridis&format=json

# Spezifisches Frequenzband
GET /api/heatmap/band?band_name=FM+Radio&time_range=24h

# Verfügbare Zeiträume
GET /api/time-ranges
→ ["1h", "6h", "24h", "7d", "30d"]

# Verfügbare Colormaps
GET /api/colormaps
→ ["viridis", "plasma", "jet", "hot", ...]

# InfluxDB Health Check
GET /api/health
→ {"status": "ok", "influxdb": "connected", ...}
```

### Discovery Endpoints

```bash
# Scan starten (async)
POST /api/scan/start

# Scan-Status prüfen
GET /api/scan/status
→ {"scanning": true/false, "progress": "50%"}

# Komplette Scan-Ergebnisse
GET /api/scan/results
→ {
    "bands": [...],
    "statistics": {...},
    "recommendations": [...]
  }

# Intelligente Empfehlungen
GET /api/scan/recommendations
→ [{
    "band": "UHF",
    "snr": 15.3,
    "score": 9.2,
    "reason": "Starkes Signal mit hoher Aktivität"
  }, ...]

# Visualisierungen (PNG als Base64)
GET /api/scan/visualization?format=both
→ {"snr_chart": "data:image/png;...", ...}
```

## 📊 Datenbank Schema

### InfluxDB Measurements

#### `frequency_scan` (Band-Statistiken)
```
Tags:
  - band_name: "FM Radio", "UHF", etc.
  - active: "true"/"false"

Fields:
  - freq_start (float)
  - freq_end (float)
  - avg_power (dB)
  - peak_power (dB)
  - noise_floor (dB)
  - signal_to_noise (dB)
  - activity_percentage (%)
  - num_peaks (int)
  - scan_time (seconds)
```

#### `frequency_spectrum` (Spektrumdaten für Heatmaps)
```
Tags:
  - band_name: "FM Radio", etc.

Fields:
  - frequency (MHz)
  - power (dB)

Timestamp: RFC 3339 Format
```

## 🧪 Testing

### Demo ohne RTL-SDR Hardware

```bash
python3 demo_test.py
```

Generiert Demo-Scan-Ergebnisse für UI-Tests.

### Integration Test

```bash
source venv/bin/activate
python3 -c "
from frequency_scanner import create_scanner_from_env
scanner = create_scanner_from_env()
print(f'RTL-SDR verbunden: {scanner.is_connected}')
"
```

## 📁 Projektstruktur

```
SolarMonitor-RTL/
├── app.py                      # Flask Server (Main)
├── frequency_scanner.py         # RTL-SDR Hardware Interface
├── heatmap_generator.py         # FFT Heatmap Generation
├── spectrum_analyzer.py         # Spektrum-Visualisierungen
├── requirements.txt             # Python Dependencies
├── .env.example                 # Konfigurationstemplate
├── solarmonitor-rtl.service     # Systemd Service
├── install_service.sh           # Service Installer
├── templates/
│   ├── dashboard.html           # Heatmap Web UI
│   └── discovery.html           # Discovery Web UI
├── README.md                    # Diese Datei
├── QUICKSTART.md                # Quick Start Anleitung
├── HEATMAP_GUIDE.md             # Heatmap Dokumentation
├── FREQUENCY_DISCOVERY_GUIDE.md # Discovery Dokumentation
└── venv/                        # Python Virtual Environment
```

## 🔧 Troubleshooting

### RTL-SDR wird nicht erkannt

```bash
# USB-Gerät prüfen
lsusb | grep -i realtek
# Sollte zeigen: "Bus 001 Device 003: ID 0bda:2838 Realtek Semiconductor Corp."

# Berechtigungen prüfen
ls -la /dev/bus/usb/*/
# Sollte Lesezugriff für Nutzer haben
```

### InfluxDB Verbindungsfehler

```bash
# InfluxDB Status prüfen
curl http://192.168.178.100:8086/ping

# Datenbank existiert?
curl -u admin:admin http://192.168.178.100:8086/query?q="SHOW DATABASES"

# .env Werte checken
cat .env | grep INFLUXDB
```

### Service startet nicht

```bash
# Logs prüfen
sudo journalctl -u solarmonitor-rtl -n 50

# Manuell testen
source venv/bin/activate
python3 app.py

# Service-Datei prüfen
sudo cat /etc/systemd/system/solarmonitor-rtl.service
```

## 📚 Weitere Dokumentation

- **QUICKSTART.md** - Schnelle Einstiegshilfe
- **HEATMAP_GUIDE.md** - FFT Heatmap API & Beispiele
- **FREQUENCY_DISCOVERY_GUIDE.md** - Discovery System Dokumentation
- **.github/copilot-instructions.md** - AI-Agent Integration Guide

## 🤝 Lizenz

MIT License - Siehe LICENSE Datei

## 📧 Support

Issues und Feature Requests: https://github.com/kajoty/SolarMonitor-RTL/issues

---

**Last Updated:** November 2025  
**Version:** 1.0 (Production Ready)

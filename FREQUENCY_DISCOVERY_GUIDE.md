# RTL-SDR Frequenzbereich Discovery - Dokumentation

## Übersicht

Das **Frequency Discovery System** ermöglicht es, automatisch verfügbare und aktive Frequenzbereiche auf einem RTL-SDR Dongle zu ermitteln und die besten Bereiche für Monitoring zu empfehlen.

## Features

✅ **Automatische Frequenzbereich-Analyse** - Scannt 11 vordefinierte Bänder  
✅ **Signal-to-Noise Ratio Berechnung** - Bestimmt Signalqualität  
✅ **Aktivitätserkennung** - Ermittelt, welche Bänder aktiv sind  
✅ **Intelligente Empfehlungen** - Schlägt beste Bänder vor  
✅ **Spektrum-Visualisierung** - 4 verschiedene Grafiken und Diagramme  
✅ **REST API** - Programmgesteuerte Integration  
✅ **Web-Dashboard** - Benutzerfreundliche Discovery UI  

## Installieren & Starten

### Dependencies
```bash
pip install -r requirements.txt
```

### Flask Server starten
```bash
python3 app.py
```

### Discovery UI öffnen
```
http://localhost:5000/discovery
```

## Funktionsweise

### 1. Scanner-Initialisierung
Der `RTLSDRScanner` verbindet sich mit dem RTL2838 USB Dongle und konfiguriert ihn:
- Sample Rate: 2 MHz
- Gain: Auto
- Device Index: 0 (konfigurierbar via `.env`)

### 2. Frequenzbereich-Scan
Der Scanner durchläuft vordefinierte Frequenzbänder:
```
UKW Radio (87.5-108 MHz)
FM Broadcast (88-108 MHz)
VHF I (46-68 MHz)
VHF II (174-216 MHz)
VHF III (216-230 MHz)
UHF IV (470-606 MHz)
UHF V (606-862 MHz) - DVB-T Hauptband
GSM-900 (890-960 MHz)
GSM-1800 (1710-1880 MHz)
2.4 GHz ISM (2400-2500 MHz)
```

### 3. Datenanalyse
Für jeden Bereich werden berechnet:
- **Average Power** - Durchschnittliche Leistung
- **Peak Power** - Maximale Leistung
- **Noise Floor** - Rauschpegel (10. Perzentil)
- **Signal-to-Noise Ratio** - Peak - Noise Floor
- **Activity Percentage** - % mit Signal über Rauschboden
- **Num Peaks** - Anzahl Signalspitzen

### 4. Empfehlungen
Der `FrequencyAnalyzer` kategorisiert Bänder nach:
- **STRONG_SIGNAL** - Hohe SNR (>3 dB), aktive Bänder
- **QUIET_BAND** - Ruhige, saubere Bänder für Test-Setups

## API Dokumentation

### POST `/api/scan/start`

Startet einen Frequenzbereich-Scan (läuft im Background)

**Request Body (optional):**
```json
{
  "quick": true,
  "custom_bands": [
    {"name": "Custom Band", "freq_start": 100, "freq_end": 200}
  ]
}
```

**Response (202 Accepted):**
```json
{
  "status": "started",
  "message": "Frequenz-Scan gestartet...",
  "timestamp": "2025-11-16T12:34:56"
}
```

**Hinweis:** Der Scan läuft asynchron. Nutzen Sie `/api/scan/status` zum Abfragen des Fortschritts.

---

### GET `/api/scan/status`

Gibt den Status des aktuellen Scans zurück

**Response:**
```json
{
  "scanning": false,
  "has_results": true,
  "timestamp": "2025-11-16T12:34:56"
}
```

---

### GET `/api/scan/results`

Gibt vollständige Scan-Ergebnisse zurück

**Response:**
```json
{
  "status": "success",
  "data": {
    "scan_data": [
      {
        "band": {
          "name": "FM Broadcast",
          "freq_start": 88,
          "freq_end": 108,
          "description": "UKW Rundfunk"
        },
        "avg_power": -35.5,
        "peak_power": -15.2,
        "noise_floor": -45.8,
        "signal_to_noise": 30.6,
        "active": true,
        "activity_percentage": 85.3,
        "num_peaks": 42,
        "scan_time": 2.35,
        "timestamp": "2025-11-16T12:34:56"
      },
      ...
    ],
    "analysis": {
      "status": "success",
      "total_scanned": 11,
      "active_bands_found": 5,
      "strong_signals": 3,
      "summary": {
        "max_snr": 30.6,
        "avg_activity": 45.2,
        "quietest_band": "VHF III"
      },
      "recommendations": [...]
    },
    "timestamp": "2025-11-16T12:34:56"
  }
}
```

---

### GET `/api/scan/recommendations`

Gibt empfohlene Frequenzbereiche zurück

**Response:**
```json
{
  "status": "success",
  "summary": {
    "max_snr": 30.6,
    "avg_activity": 45.2,
    "quietest_band": "VHF III"
  },
  "recommendations": [
    {
      "rank": 1,
      "type": "STRONG_SIGNAL",
      "band": {
        "name": "FM Broadcast",
        "freq_start": 88,
        "freq_end": 108,
        "description": "UKW Rundfunk"
      },
      "reason": "Starkes Signal mit SNR 30.6 dB",
      "metrics": {
        "snr": 30.6,
        "activity": 85.3,
        "peak_power": -15.2
      }
    },
    ...
  ],
  "total_scanned": 11,
  "timestamp": "2025-11-16T12:34:56"
}
```

---

### GET `/api/scan/visualization`

Gibt Visualisierungen als Base64-kodierte PNG-Bilder zurück

**Query Parameter:**
- `format`: `overview`, `spectrum`, oder `both` (Standard: `overview`)

**Response:**
```json
{
  "status": "success",
  "visualizations": {
    "overview": "iVBORw0KGgoAAAANSUhEUgAAAAUA...",
    "spectrum": "iVBORw0KGgoAAAANSUhEUgAAAAUA..."
  },
  "timestamp": "2025-11-16T12:34:56"
}
```

## Visualisierungen

### 1. SNR Vergleich (Horizontal Bar Chart)
Zeigt Signal-to-Noise Ratio für alle Bänder mit Schwelle-Markierung

### 2. Aktiv vs. Ruhig (Pie Chart)
Prozentuale Verteilung von aktiven und ruhigen Bändern

### 3. Power-Spektrum (Grouped Bar Chart)
Vergleicht Peak Power, Average Power und Noise Floor pro Band

### 4. Aktivitätsmatrix (Heatmap)
Farbkodierte Aktivitätsrate mit Wert-Anzeige

### 5. Frequenzspektrum-Übersicht (Frequency Map)
Räumliche Darstellung aller Frequenzbänder mit SNR-Färbung:
- **Grün:** Sehr stark (>10 dB)
- **Orange:** Stark (5-10 dB)
- **Dunkel Orange:** Schwach (0-5 dB)
- **Grau:** Sehr schwach (<0 dB)

## Python Code-Beispiele

### Einfacher Scan
```python
from frequency_scanner import create_scanner_from_env

scanner = create_scanner_from_env()

# Schnell-Scan aktiver Bänder
results = scanner.find_active_bands()

for result in results:
    print(f"{result.band.name}: SNR = {result.signal_to_noise:.1f} dB")
```

### Detaillierte Analyse
```python
from frequency_scanner import RTLSDRScanner, FrequencyAnalyzer

scanner = RTLSDRScanner()
results = scanner.scan_all_bands()

# Analysiere und erhalte Empfehlungen
analysis = FrequencyAnalyzer.recommend_bands(results)

print(f"Aktive Bänder: {analysis['active_bands_found']}")
print(f"Max SNR: {analysis['summary']['max_snr']} dB")

for rec in analysis['recommendations']:
    print(f"#{rec['rank']}: {rec['band']['name']} - {rec['reason']}")
```

### Visualisierung erstellen
```python
from spectrum_analyzer import SpectrumAnalyzer

# Erstelle Übersicht
buf = SpectrumAnalyzer.plot_scan_results(results)
buf.seek(0)

# Speichere als PNG
with open('scan_overview.png', 'wb') as f:
    f.write(buf.getvalue())
```

## Typische Scan-Szenarien

### Szenario 1: Rundfunk-Monitoring
**Empfohlen: FM Broadcast (88-108 MHz)**
- Starke, stabile Signale
- Viele Sender
- Gute Decken

### Szenario 2: Digitales TV (DVB-T)
**Empfohlen: UHF V (606-862 MHz)**
- Standard für Europa
- Viele Multiplex-Kanäle
- RTL2838 optimiert für diesen Bereich

### Szenario 3: Mobilfunk-Monitoring (älter)
**Empfohlen: GSM-900/1800**
- Viel Aktivität
- Gute Signal-Qualität
- Erfordert höhere Gain-Einstellung

### Szenario 4: Test/Entwicklung
**Empfohlen: VHF III oder ruhige Bänder**
- Wenig natürliche Interferenz
- Ideal für Signal-Generatoren
- Saubere Baselines

## Fehlerbehandlung

### RTL-SDR nicht verbunden
```
Error: RTL-SDR Scanner nicht verfügbar
```
**Lösung:**
1. Prüfen Sie USB-Verbindung
2. Installieren Sie libusb: `apt-get install libusb-1.0-0`
3. Geben Sie Berechtigungen: `sudo usermod -a -G plugdev pi`

### Zu wenig Speicher (Raspberry Pi)
Der Scan benötigt ~50-100 MB RAM. Auf sehr begrenzten Systemen:
```python
# Reduzieren Sie Sample-Rate
scanner = RTLSDRScanner(sample_rate=1000000)  # 1 MSps statt 2
```

### Scan-Timeout
Der Scan benötigt 30-60 Sekunden. Erhöhen Sie Poll-Timeout in der UI.

## Konfiguration via .env

```env
# RTL-SDR Scanner Konfiguration
RTL_DEVICE_INDEX=0           # Geräte-Index (0 = erstes)
RTL_SAMPLE_RATE=2000000      # Sample-Rate in Hz
```

## Performance-Tipps

1. **Scan-Auflösung:** Der Scanner nutzt 50 Frequenzen pro Band = 550 Messungen
2. **Caching:** Ergebnisse werden im Memory gespeichert - neue Scans überschreiben alte
3. **Threading:** Scans laufen im Background - Flask bleibt responsive
4. **Visualisierung:** PNG-Generierung ist CPU-intensiv - kann 5-10 Sekunden auf Pi dauern

## Integration mit Heatmap-System

Nach Frequenzbereich-Entdeckung können Sie direkt Heatmaps für empfohlene Bänder erstellen:

```javascript
// Hole Empfehlungen
const recs = await fetch('/api/scan/recommendations').then(r => r.json());

// Nutze erstes empfohlenes Band für Heatmap
const band = recs.recommendations[0].band;
const heatmapUrl = `/api/heatmap?freq_start=${band.freq_start}&freq_end=${band.freq_end}&time_range=24h`;
```

## Lizenz

SolarMonitor-RTL © 2025 kajoty

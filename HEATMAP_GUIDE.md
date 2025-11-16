# FFT Heatmap Generator - Dokumentation

## Übersicht

Der FFT Heatmap Generator ist eine Komponente des SolarMonitor-RTL Systems, die Frequenzspektrum-Daten aus InfluxDB abruft und sie als interaktive Wärmekarten (Heatmaps) visualisiert.

**Features:**
- 📊 FFT Spektrum Heatmaps mit Zeit-Frequenz-Auflösung
- ⏰ Wählbare Zeiträume (1h, 6h, 24h, 7d, 30d)
- 🎨 Verschiedene Colormaps (viridis, plasma, jet, etc.)
- 🔍 Filterung nach Frequenzbereich
- 💾 PNG Download der Heatmaps
- 🌐 REST API + Web-Dashboard

## Installation

### 1. Dependencies installieren
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. InfluxDB konfigurieren

Die `.env` Datei muss die folgenden Variablen enthalten:
```env
INFLUXDB_HOST=192.168.178.100
INFLUXDB_PORT=8086
INFLUXDB_USER=admin
INFLUXDB_PASSWORD=admin
INFLUXDB_DATABASE=rtl_monitor
```

Die InfluxDB Datenbank muss eine Messung namens `frequency_spectrum` mit folgenden Feldern enthalten:
- **Tags:** `frequency` (in MHz)
- **Fields:** `power` (in dB oder linear)
- **Timestamp:** RFC 3339 Format

### 3. Flask App starten
```bash
python3 app.py
```

Die Web-Dashboard ist dann verfügbar unter: `http://localhost:5000`

## API Dokumentation

### GET `/api/heatmap`

Generiert eine FFT Heatmap basierend auf Spektraldaten.

**Query Parameter:**
| Parameter | Typ | Standard | Beschreibung |
|-----------|-----|---------|-------------|
| `time_range` | string | `24h` | Zeitraum: `1h`, `6h`, `24h`, `7d`, `30d` |
| `freq_start` | float | - | Startfrequenz in MHz (optional) |
| `freq_end` | float | - | Endfrequenz in MHz (optional) |
| `cmap` | string | `viridis` | Colormap: `viridis`, `plasma`, `jet`, etc. |
| `format` | string | `png` | Ausgabeformat: `png` oder `json` |

**Response (PNG):**
Direktes PNG-Bild (type: `image/png`)

**Response (JSON):**
```json
{
  "status": "success",
  "time_range": "24h",
  "freq_start": 100,
  "freq_end": 1000,
  "cmap": "viridis",
  "data": "iVBORw0KGgoAAAANSUhEUgAAAAUA...",
  "timestamp": "2025-11-16T12:34:56.789012"
}
```

**Beispiele:**

```bash
# Einfache 24h Heatmap
curl http://localhost:5000/api/heatmap

# 7-Tage Heatmap mit Frequenzbereich 100-800 MHz
curl "http://localhost:5000/api/heatmap?time_range=7d&freq_start=100&freq_end=800"

# Als JSON mit Hot Colormap
curl "http://localhost:5000/api/heatmap?format=json&cmap=hot"
```

### GET `/api/health`

Prüft die Verbindung zu InfluxDB.

**Response:**
```json
{
  "status": "healthy",
  "influxdb_connected": true,
  "timestamp": "2025-11-16T12:34:56.789012"
}
```

### GET `/api/time-ranges`

Gibt verfügbare Zeiträume zurück.

**Response:**
```json
{
  "time_ranges": ["1h", "6h", "24h", "7d", "30d"]
}
```

### GET `/api/colormaps`

Gibt verfügbare Colormaps zurück.

**Response:**
```json
{
  "colormaps": ["viridis", "plasma", "inferno", "magma", "jet", ...]
}
```

## Web-Dashboard

### Features
- **Zeitraum-Auswahl:** Quick-Buttons und Dropdown für 1h, 6h, 24h, 7d, 30d
- **Frequenzfilter:** Optionale Eingaben für Start- und End-Frequenz
- **Colormap-Auswahl:** 17+ verschiedene Farbschemas
- **Live Health-Check:** Status der InfluxDB-Verbindung
- **Download:** PNG Export der Heatmap
- **Responsive Design:** Funktioniert auf Desktop und Tablets

### Bedienung
1. Wählen Sie einen Zeitraum über Quick-Buttons oder Dropdown
2. (Optional) Geben Sie Start- und End-Frequenz ein
3. (Optional) Wählen Sie ein Colormap-Schema
4. Klicken Sie "Heatmap generieren"
5. Download als PNG möglich

## Code-Beispiele

### Python - Direkte Nutzung

```python
from heatmap_generator import create_heatmap_generator_from_env

# Generator initialisieren
gen = create_heatmap_generator_from_env()

# Spektraldaten laden
spektrum_data, timestamps, frequencies = gen.get_frequency_data(
    time_range='24h',
    freq_start=100,
    freq_end=800
)

# Heatmap als Base64 String generieren
heatmap_base64 = gen.generate_heatmap_base64(
    spektrum_data, 
    timestamps, 
    frequencies,
    title="Meine Heatmap",
    cmap='plasma'
)

# Oder: Alles auf einmal
heatmap_base64 = gen.get_heatmap_data(time_range='7d', cmap='hot')
```

### JavaScript - Fetch API

```javascript
// Heatmap als PNG laden und anzeigen
async function loadHeatmap() {
  const response = await fetch('/api/heatmap?time_range=24h&cmap=viridis');
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  document.getElementById('image').src = url;
}

// Oder: Als JSON mit Base64
async function loadHeatmapJSON() {
  const response = await fetch('/api/heatmap?format=json&time_range=7d');
  const data = await response.json();
  const img = document.createElement('img');
  img.src = `data:image/png;base64,${data.data}`;
  document.getElementById('image').appendChild(img);
}
```

### cURL Beispiele

```bash
# Standard 24h Heatmap herunterladen
curl -o heatmap.png http://localhost:5000/api/heatmap

# 7-Tage Heatmap mit Frequenzbereich 100-800 MHz
curl "http://localhost:5000/api/heatmap?time_range=7d&freq_start=100&freq_end=800" \
  -o heatmap_filtered.png

# JSON Response für weitere Verarbeitung
curl "http://localhost:5000/api/heatmap?format=json&cmap=plasma" \
  | jq '.data' > heatmap_base64.txt
```

## InfluxDB Schema

### Erforderliche Messungen

```
Measurement: frequency_spectrum
Tags:
  - frequency: Frequenz in MHz (z.B. "100.5", "800.0")
Fields:
  - power: Leistung in dB oder Linear (Float)
Timestamp: RFC 3339 (z.B. "2025-11-16T12:00:00Z")
```

### Beispiel Insert (InfluxDB Line Protocol)

```
frequency_spectrum,frequency=100.5 power=45.2 1731761400000000000
frequency_spectrum,frequency=101.0 power=42.8 1731761400000000000
frequency_spectrum,frequency=200.5 power=38.5 1731761400000000000
```

### Daten schreiben (Python)

```python
from influxdb import InfluxDBClient

client = InfluxDBClient(host='localhost', port=8086)
client.switch_db('rtl_monitor')

# Beispiel: Schreibe Frequenzspektrum-Daten
json_body = [
    {
        "measurement": "frequency_spectrum",
        "tags": {
            "frequency": "100.5"
        },
        "fields": {
            "power": 45.2
        }
    }
]

client.write_points(json_body)
```

## Fehlerbehandlung

### Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|--------|--------|
| InfluxDB ist nicht verbunden | Falsche Konfiguration oder Service offline | Prüfen Sie `.env` und InfluxDB Status |
| Keine Daten verfügbar | Keine Daten in InfluxDB für den Zeitraum | Schreiben Sie Testdaten in die Datenbank |
| HTTP 400 - freq_start >= freq_end | Ungültiger Frequenzbereich | Start-Frequenz muss kleiner sein |
| HTTP 500 - Server Error | Interner Fehler im Generator | Prüfen Sie Logs auf Fehlermeldungen |

### Logging

Das System verwendet Python Logging. Für Debug-Informationen:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance-Tipps

- **Große Zeiträume:** Verwenden Sie Frequenzfilter um Datenmengen zu reduzieren
- **Raspberry Pi:** Aktivieren Sie Caching in Flask für wiederholte Requests
- **InfluxDB:** Erstellen Sie Indizes auf `frequency` Tag für schnellere Abfragen

## Erweiterungen

### Custom Colormaps
```python
import matplotlib.pyplot as plt
custom_cmap = plt.cm.get_cmap('custom_name')
# Nutzen Sie im Generator mit cmap Parameter
```

### Exportformate erweitern
Der Generator kann leicht erweitert werden für andere Formate (SVG, PDF, etc.)

### 3D-Visualisierung
Zukünftige Version könnte 3D-Oberflächen nutzen: `matplotlib.mplot3d`

## Lizenz

SolarMonitor-RTL © 2025 kajoty

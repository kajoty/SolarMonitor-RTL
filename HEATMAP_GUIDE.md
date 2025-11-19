# FFT Heatmap Generator - Dokumentation

## Übersicht

Der FFT Heatmap Generator ist eine Komponente des SolarMonitor-RTL Systems, die Frequenzspektrum-Daten aus SQLite abruft und sie als interaktive Wärmekarten (Heatmaps) visualisiert.

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

### 2. SQLite Datenbank

Die SQLite-Datenbank wird automatisch initialisiert und unter `./spectrum.db` gespeichert. Keine manuelle Konfiguration nötig.

Die Datenbank enthält eine Tabelle `frequency_spectrum` mit folgenden Feldern:
- **timestamp** - Unix-Timestamp (int)
- **frequency_mhz** - Frequenz in MHz (float)
- **power_db** - Leistung in dB (float)

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

Prüft die Verbindung zu SQLite und den Datenbankstatus.

**Response:**
```json
{
  "status": "healthy",
  "sqlite_connected": true,
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
- **Live Health-Check:** Status der SQLite-Datenbankverbindung
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

## SQLite Schema

### Tabellenstruktur

Die Tabelle `frequency_spectrum` enthält:

```sql
CREATE TABLE frequency_spectrum (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    frequency_mhz REAL NOT NULL,
    power_db REAL NOT NULL
);
```

### Beispiel Query

```sql
SELECT * FROM frequency_spectrum 
WHERE timestamp > strftime('%s', 'now') - 86400 
ORDER BY timestamp DESC;
```

### Daten schreiben (Python)

```python
import sqlite3

conn = sqlite3.connect('./spectrum.db')
cursor = conn.cursor()

# Beispiel: Schreibe Frequenzspektrum-Daten
timestamp = int(time.time())
frequency_mhz = 100.5
power_db = 45.2

cursor.execute(
    'INSERT INTO frequency_spectrum (timestamp, frequency_mhz, power_db) VALUES (?, ?, ?)',
    (timestamp, frequency_mhz, power_db)
)
conn.commit()
```

## Fehlerbehandlung

### Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|--------|--------|
| Keine Datenbankverbindung | SQLite nicht erreichbar | Prüfen Sie die Dateiberechtigungen für `spectrum.db` |
| Keine Daten verfügbar | Keine Daten in SQLite für den Zeitraum | Überprüfen Sie, ob der RTL-SDR Scanner aktiv ist |
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
- **SQLite:** Erstellen Sie Indizes auf `frequency_mhz` und `timestamp` für schnellere Abfragen

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

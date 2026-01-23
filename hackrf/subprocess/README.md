# Standalone Heatmap Generator Service

Eigenständiger Service zur Heatmap-Generierung auf einem leistungsstarken Rechner.

## Installation (auf dem leistungsstarken Rechner)

```bash
# Python 3.8+ erforderlich
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

pip install -r requirements.txt

# Konfiguration
cp .env.example .env
# Editiere .env mit korrekten PostgreSQL-Zugangsdaten
```

## Service starten

```bash
source venv/bin/activate
python3 heatmap_service.py
```

Service läuft auf: `http://0.0.0.0:8888`

## API-Endpunkte

### 1. Status prüfen
```bash
curl http://localhost:8888/status
```

**Response:**
```json
{
  "status": "ok",
  "database": "connected",
  "records": 3572976,
  "timestamp": "2025-12-07T16:40:00"
}
```

### 2. Heatmap generieren

**PNG direkt:**
```bash
curl -X POST http://localhost:8888/generate \
  -H "Content-Type: application/json" \
  -d '{
    "band": "Solar Radio",
    "hours": 24,
    "colormap": "YlOrRd",
    "width": 16,
    "height": 10,
    "dpi": 100
  }' \
  --output heatmap.png
```

**Base64-Encoding (für JSON-Response):**
```bash
curl -X POST http://localhost:8888/generate \
  -H "Content-Type: application/json" \
  -d '{
    "band": "Solar Radio",
    "hours": 24,
    "colormap": "YlOrRd",
    "format": "base64"
  }'
```

**Response:**
```json
{
  "status": "success",
  "format": "base64",
  "image": "iVBORw0KGgoAAAANSUhEUgAA...",
  "size_bytes": 345678
}
```

## Parameter

| Parameter | Typ | Standard | Beschreibung |
|---|---|---|---|
| `band` | string | "Solar Radio" | Band-Name in DB |
| `hours` | int | 24 | Zeitbereich (1-168h) |
| `colormap` | string | "YlOrRd" | Matplotlib colormap |
| `receiver` | string | null | Filter: 'rtl', 'hackrf' oder null=alle |
| `format` | string | "png" | Ausgabe: 'png' oder 'base64' |
| `width` | int | 16 | Breite in Inches |
| `height` | int | 10 | Höhe in Inches |
| `dpi` | int | 100 | Auflösung |

## Colormaps

Verfügbare Colormaps:
- `YlOrRd` (Gelb → Orange → Rot)
- `viridis` (Blau → Grün → Gelb)
- `plasma` (Blau → Pink → Gelb)
- `inferno` (Schwarz → Rot → Gelb)
- `coolwarm` (Blau ↔ Rot)
- `RdYlBu_r` (Rot → Gelb → Blau, reversed)

Siehe: https://matplotlib.org/stable/gallery/color/colormap_reference.html

## Integration in Raspberry Pi

Auf dem Pi kannst du den Service via REST-API aufrufen:

```python
import requests

# Heatmap generieren
response = requests.post(
    'http://<LEISTUNGSSTARKER-RECHNER>:8888/generate',
    json={
        'band': 'Solar Radio',
        'hours': 24,
        'colormap': 'YlOrRd',
        'format': 'base64'
    }
)

if response.status_code == 200:
    data = response.json()
    image_base64 = data['image']
    # Nutze in Grafana oder Web-UI
```

## Systemd-Service (Optional)

Für automatischen Start beim Booten:

```bash
sudo nano /etc/systemd/system/heatmap-generator.service
```

```ini
[Unit]
Description=SolarMonitor Heatmap Generator Service
After=network.target

[Service]
Type=simple
User=<USERNAME>
WorkingDirectory=/pfad/zu/hackrf/subprocess
Environment="PATH=/pfad/zu/hackrf/subprocess/venv/bin"
ExecStart=/pfad/zu/hackrf/subprocess/venv/bin/python3 heatmap_service.py
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable heatmap-generator.service
sudo systemctl start heatmap-generator.service
sudo systemctl status heatmap-generator.service
```

## Performance

Auf einem leistungsstarken Rechner:
- 24h Heatmap: ~1-2 Sekunden
- 7 Tage Heatmap: ~3-5 Sekunden
- 30 Tage Heatmap: ~10-15 Sekunden

Vs. Raspberry Pi 4B:
- 24h: ~5-8 Sekunden
- 7 Tage: ~15-30 Sekunden
- 30 Tage: >60 Sekunden (Timeout-Gefahr)

## Logs

Service-Logs in `heatmap_service.log`:
```bash
tail -f heatmap_service.log
```

## Troubleshooting

**Verbindung fehlgeschlagen:**
```bash
# PostgreSQL-Verbindung testen
psql -h 192.168.178.100 -U admin -d solarmonitor
```

**Port bereits belegt:**
```bash
# Port ändern in .env
PORT=8889
```

**Matplotlib-Fehler:**
```bash
# Non-interactive Backend konfiguriert (bereits in Code)
# Falls Fehler: sudo apt-get install python3-tk
```

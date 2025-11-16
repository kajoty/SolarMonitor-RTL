# 🚀 SolarMonitor-RTL - Quick Start Guide

## ✅ Status: Alles getestet und ready!

Alle Komponenten wurden erfolgreich installiert und getestet.

## 📋 Was Sie haben:

- ✅ **FFT Heatmap Generator** - Visualisierung von Spektraldaten über Zeit
- ✅ **Frequenzbereich Discovery** - Automatisches Scannen verfügbarer Bänder
- ✅ **REST API** - Vollständige API für beide Komponenten
- ✅ **Web Dashboards** - Moderne UIs für Heatmaps und Discovery
- ✅ **Konfigurierbare Gain-Einstellungen** - RTL-SDR Empfindlichkeit anpassbar

## 🎯 Los geht's:

### 1️⃣ Virtual Environment aktivieren

```bash
cd /home/pi/Projekte/solarmonitor/SolarMonitor-RTL
source venv/bin/activate
```

### 2️⃣ Flask Server starten

```bash
python3 app.py
```

Erwartet Output:
```
 * Running on http://0.0.0.0:5000
```

### 3️⃣ Browser öffnen

Öffnen Sie eine dieser URLs:

- **Heatmap Dashboard**: `http://localhost:5000/`
  - FFT Spektrumheatmaps anschauen
  - Verschiedene Zeiträume und Colormaps

- **Discovery UI**: `http://localhost:5000/discovery`
  - RTL-SDR Frequenzbereiche scannen
  - Beste Bänder empfohlen bekommen
  - Visualisierungen mit SNR und Aktivität

## 🧪 Ohne RTL-SDR Hardware testen

Führen Sie das Demo-Script aus:

```bash
python3 demo_test.py
```

Das erstellt Mock-Daten und testet alle Komponenten.

## 🔧 Mit RTL-SDR Hardware

### Gain-Werte überprüfen

Wenn die RTL2838 Hardware angeschlossen ist:

```bash
python3 test_rtl_gains.py
```

Das zeigt alle verfügbaren Gain-Werte und deren Power-Messungen.

### Gain konfigurieren

Bearbeiten Sie `.env`:

```env
# Automatisch (default)
RTL_GAIN=auto

# Oder fester Wert
RTL_GAIN=25.4
```

### Frequenzbereiche scannen

1. Browser → `http://localhost:5000/discovery`
2. Klick auf "Schnell-Scan starten"
3. Warten Sie 30-60 Sekunden
4. Sehen Sie Empfehlungen und Visualisierungen

## 📊 REST API Endpoints

### Heatmap API

```bash
# 24h Heatmap als PNG
curl http://localhost:5000/api/heatmap

# 7-Tage Heatmap mit Frequenzfilter
curl "http://localhost:5000/api/heatmap?time_range=7d&freq_start=100&freq_end=800"

# Als JSON mit Base64
curl "http://localhost:5000/api/heatmap?format=json&cmap=plasma"
```

### Discovery API

```bash
# Scan starten
curl -X POST http://localhost:5000/api/scan/start

# Status prüfen
curl http://localhost:5000/api/scan/status

# Ergebnisse abrufen
curl http://localhost:5000/api/scan/results

# Empfehlungen abrufen
curl http://localhost:5000/api/scan/recommendations

# Visualisierungen abrufen
curl http://localhost:5000/api/scan/visualization?format=both
```

## 📁 Wichtige Dateien

```
├── app.py                      # Flask Server (Haupteinstieg)
├── heatmap_generator.py        # FFT Heatmap Engine
├── frequency_scanner.py        # RTL-SDR Scanner & Analyzer
├── spectrum_analyzer.py        # Visualisierungen
├── demo_test.py               # Demo ohne Hardware
├── test_rtl_gains.py          # RTL-SDR Gain-Tester
├── templates/
│   ├── dashboard.html         # Heatmap UI
│   └── discovery.html         # Discovery UI
├── HEATMAP_GUIDE.md          # Heatmap Dokumentation
├── FREQUENCY_DISCOVERY_GUIDE.md  # Discovery Dokumentation
└── .env                       # Konfiguration (RTL_GAIN, etc.)
```

## 💡 Troubleshooting

### "InfluxDB nicht verbunden"

Das ist OK für erste Tests. Sie brauchen InfluxDB nur, wenn Sie echte Spektraldaten speichern möchten.

### "RTL-SDR nicht verbunden"

Das ist normal, wenn der USB Dongle nicht angeschlossen ist. Das System läuft trotzdem!

Mit Hardware:
1. Prüfen Sie USB-Verbindung
2. Installieren Sie libusb: `sudo apt-get install libusb-1.0-0`
3. Geben Sie Berechtigungen: `sudo usermod -a -G plugdev pi`

### Langsam auf Raspberry Pi?

Das ist normal:
- FFT Heatmap Generierung: 5-10 Sekunden
- Frequenz-Scanner: 30-60 Sekunden für alle 11 Bänder
- Matplotlib Rendering ist CPU-intensiv

## 🎓 Beispiele

### Python: Mock-Scan durchführen

```python
from frequency_scanner import FrequencyBand, ScanResult, FrequencyAnalyzer

band = FrequencyBand("Test", 100, 200)
result = ScanResult(
    band=band,
    avg_power=-40,
    peak_power=-20,
    noise_floor=-50,
    signal_to_noise=30,
    active=True,
    activity_percentage=80,
    num_peaks=50,
    scan_time=2.0
)

analysis = FrequencyAnalyzer.recommend_bands([result])
print(analysis['recommendations'])
```

### JavaScript: Heatmap laden

```javascript
fetch('/api/heatmap?time_range=24h&format=json')
  .then(r => r.json())
  .then(data => {
    const img = document.createElement('img');
    img.src = `data:image/png;base64,${data.data}`;
    document.body.appendChild(img);
  });
```

### cURL: Scan durchführen

```bash
# Scan starten
curl -X POST http://localhost:5000/api/scan/start

# Status prüfen (repeat bis scanning=false)
sleep 5
curl http://localhost:5000/api/scan/status

# Ergebnisse abrufen
curl http://localhost:5000/api/scan/results | jq '.data.analysis.recommendations'
```

## ❓ Häufige Fragen

**F: Kann ich ohne RTL-SDR Hardware arbeiten?**  
A: Ja! Die Heatmap-Komponente funktioniert mit InfluxDB-Daten. Der Demo-Test zeigt Mock-Daten.

**F: Wie oft sollte ich scannen?**  
A: Initial 1x für Baseline. Bei Änderungen (neuen Antennen, Ort, etc.) erneut.

**F: Welcher Gain-Wert ist am besten?**  
A: Für balance: `25.4`. Für schwache Signale: `35.0+`. Test mit `test_rtl_gains.py`!

**F: Kann ich die Zeiträume anpassen?**  
A: Ja, in `frequency_scanner.py` → `TIME_RANGES` dict.

**F: Kann ich Custom Frequenzbänder hinzufügen?**  
A: Ja, via POST `/api/scan/start` mit `custom_bands` parameter.

## 📚 Weitere Ressourcen

- `HEATMAP_GUIDE.md` - Vollständige Heatmap-Dokumentation
- `FREQUENCY_DISCOVERY_GUIDE.md` - Vollständige Discovery-Dokumentation
- `.github/copilot-instructions.md` - AI-Agent Dokumentation

---

**Happy Monitoring! 📡**

Fragen? Schauen Sie in die `.md` Dateien oder führen Sie `python3 demo_test.py` aus!

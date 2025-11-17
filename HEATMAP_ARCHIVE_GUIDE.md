# 📅 Tägliche Heatmap Archivierung

Das Script `save_daily_heatmaps.py` speichert automatisch Heatmaps pro Tag für Langzeit-Archivierung.

## 🚀 Verwendung

### Manuelle Speicherung
```bash
# Heute speichern
python3 save_daily_heatmaps.py

# Gestern speichern
python3 save_daily_heatmaps.py --date yesterday

# Spezifisches Datum
python3 save_daily_heatmaps.py --date 2025-11-15

# Zeitraum speichern
python3 save_daily_heatmaps.py --from 2025-11-01 --to 2025-11-17

# Mehrere Colormaps
python3 save_daily_heatmaps.py --cmap viridis --cmap plasma --cmap jet

# Anderes Ausgabeverzeichnis
python3 save_daily_heatmaps.py --output-dir /mnt/archive/heatmaps
```

### Archiv-Statistiken anzeigen
```bash
python3 save_daily_heatmaps.py --stats
```

## ⏰ Automatisierung mit Cronjob

Füge folgende Zeile zu crontab hinzu (täglich um 23:55):
```bash
crontab -e
```

Dann einfügen:
```
# Täglich um 23:55 Heatmaps archivieren (viridis + plasma)
55 23 * * * cd /home/pi/Projekte/solarmonitor/SolarMonitor-RTL && /home/pi/Projekte/solarmonitor/SolarMonitor-RTL/venv/bin/python3 save_daily_heatmaps.py --output-dir ./heatmaps --cmap viridis --cmap plasma 2>&1 | logger -t solarmonitor-heatmap
```

### Überprüfe ob Cronjob läuft
```bash
# Zeige crontab
crontab -l

# Zeige letzte Logs
sudo journalctl -t solarmonitor-heatmap -n 20
```

## 📁 Verzeichnisstruktur

```
heatmaps/
├── 2025-11-15/
│   ├── heatmap_viridis.png
│   ├── heatmap_plasma.png
│   └── metadata.json
├── 2025-11-16/
│   ├── heatmap_viridis.png
│   ├── heatmap_plasma.png
│   └── metadata.json
└── 2025-11-17/
    ├── heatmap_viridis.png
    ├── heatmap_plasma.png
    ├── heatmap_jet.png
    └── metadata.json
```

## 📊 Metadaten pro Tag

Jeder Tag hat eine `metadata.json`:
```json
{
  "date": "2025-11-17",
  "band_name": "Solar Radio",
  "cmap": "viridis",
  "saved_at": "2025-11-17T22:41:15.975559",
  "heatmap_file": "2025-11-17/heatmap_viridis.png"
}
```

## 💾 Speichergröße

- Pro Heatmap: ~150-200 KB (PNG)
- Pro Tag (3 Colormaps): ~500 KB
- Pro Monat: ~15 MB
- Pro Jahr: ~180 MB

## 🔧 Tipps

### Nur bestimmte Colormaps speichern
```bash
# Nur viridis (kleinste Dateigröße)
python3 save_daily_heatmaps.py --cmap viridis

# Nur plasma (gute Farbenkontraste)
python3 save_daily_heatmaps.py --cmap plasma
```

### Mit externem Speicher
```bash
# Auf USB-Stick oder Network-Drive
python3 save_daily_heatmaps.py --output-dir /mnt/usb/heatmaps
python3 save_daily_heatmaps.py --output-dir /mnt/nfs/archive/solarmonitor
```

### Batch-Archivierung für mehrere Bands
```bash
# Wenn mehrere Bands konfiguriert:
python3 save_daily_heatmaps.py --date today --band "Solar Radio"
python3 save_daily_heatmaps.py --date today --band "VHF Band"
```

## 🎯 Empfohlener Setup

1. **Tägliche Automatisierung**: Cronjob jeden Abend um 23:55
2. **Colormaps**: viridis + plasma (beste Balance aus Größe/Qualität)
3. **Speicherort**: `./heatmaps` (lokal auf Pi)
4. **Backup**: Periodisch auf externen Speicher kopieren

```bash
# Beispiel: Wöchentliches Backup auf USB
0 3 * * 0 rsync -av /home/pi/Projekte/solarmonitor/SolarMonitor-RTL/heatmaps /mnt/usb/ 2>&1 | logger -t solarmonitor-backup
```

## ❓ Häufige Fragen

**F: Kann ich alte Heatmaps löschen?**
A: Ja, einfach die Verzeichnisse unter `heatmaps/` löschen:
```bash
rm -rf heatmaps/2025-10-*  # Oktober löschen
```

**F: Kann ich mehrere Colormaps gleichzeitig speichern?**
A: Ja! Das Script speichert automatisch mehrere Versionen wenn du sie mit `--cmap` angibst.

**F: Was wenn die API nicht antwortet?**
A: Das Script logged einen Fehler und setzt den Tag auf "failed" - es läuft einfach weiter.

**F: Kann ich die Größe reduzieren?**
A: Nutze nur eine Colormap (z.B. viridis), das spart ~40% Speicherplatz.

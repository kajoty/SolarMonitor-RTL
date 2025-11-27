# RTL-Power Parallel System

Dieses Verzeichnis enthält ein **paralleles** Spektrum-Analyse-System basierend auf `rtl_power` (klassisches RTL-SDR Tool). Es läuft **unabhängig** vom Haupt-System und dient zum **Vergleich**.

## Unterschiede zum Haupt-System

| Feature | Haupt-System (app.py) | rtl_power System |
|---------|----------------------|------------------|
| **Backend** | Python rtlsdr Library | C-Tool rtl_power |
| **Datenspeicherung** | SQLite (persistent) | CSV-Dateien |
| **Heatmaps** | Matplotlib (dynamisch) | PIL (statisch) |
| **Auflösung** | 500 Frequenzen | Konfigurierbar (bis 10.000+) |
| **Integration** | Flask API | Standalone |
| **Performance** | ~30s Scan | Schneller (C-basiert) |

## Verwendung

### Quick Test (10 Minuten)
```bash
./rtl_power_quick.sh
```
Erstellt einen 10-Minuten-Test mit grober Auflösung.

### Voller Scan (6 Stunden)
```bash
./rtl_power_compare.sh
```
**Achtung:** Blockiert den RTL-SDR Dongle! Stoppe vorher die Haupt-Services:
```bash
sudo systemctl stop solarmonitor-app.service
```

### Manueller Scan
```bash
# Hohe Auflösung (6000 bins, 24h)
rtl_power -f 20M:80M:10k -g 20.7 -i 60 -e 24h spectrum.csv

# Heatmap generieren
python3 rtl_power_heatmap.py spectrum.csv output.png
```

## Parameter erklärt

**Frequenzbereich:** `-f 20M:80M:10k`
- Start: 20 MHz
- Ende: 80 MHz
- Bin-Size: 10 kHz (kleinerer Wert = mehr Details, größere Dateien)

**Gain:** `-g 20.7`
- Verstärkung in dB (wie im Haupt-System)

**Integration Time:** `-i 60`
- Sekunden pro Messung (höher = weniger Rauschen)

**Dauer:** `-e 6h`
- Scan-Dauer: 6h, 24h, 7d, etc.

## Vorteile rtl_power

✅ **Höhere Frequenz-Auflösung** - Bis zu 10.000+ bins möglich  
✅ **Bewährtes Tool** - Seit Jahren im Einsatz, stabil  
✅ **Performance** - C-basiert, schneller als Python  
✅ **Kompatibilität** - CSV-Export für andere Tools  

## Nachteile

❌ **Keine Live-Anzeige** - Nur nach Scan-Ende  
❌ **Keine Datenbank** - Nur CSV-Dateien  
❌ **Keine REST API** - Standalone-Tool  
❌ **Blockiert Dongle** - Kann nicht parallel zum Haupt-System laufen  

## Vergleich durchführen

1. **Stoppe Haupt-System:**
   ```bash
   sudo systemctl stop solarmonitor-app.service
   ```

2. **Starte rtl_power:**
   ```bash
   ./rtl_power_quick.sh
   ```

3. **Warte 10 Minuten**

4. **Vergleiche Heatmaps:**
   - rtl_power: `./rtl_power_data/quick_*.png`
   - Haupt-System: `http://localhost:5000` (nach Neustart)

5. **Starte Haupt-System wieder:**
   ```bash
   sudo systemctl start solarmonitor-app.service
   ```

## Dateien

- `rtl_power_heatmap.py` - Original heatmap.py von keenerd/rtl-sdr-misc
- `rtl_power_compare.sh` - 6-Stunden Vergleichs-Scan
- `rtl_power_quick.sh` - 10-Minuten Schnelltest
- `rtl_power_data/` - Output-Verzeichnis (CSV + PNG)

## Detailgrad einstellen

Für **mehr Details** (aber größere Dateien):
```bash
# Sehr hohe Auflösung
rtl_power -f 20M:80M:1k -g 20.7 -i 60 -e 1h spectrum_hires.csv
```

Für **schnelle Übersicht**:
```bash
# Niedrige Auflösung
rtl_power -f 20M:80M:100k -g 20.7 -i 30 -e 30m spectrum_quick.csv
```

## Cleanup

```bash
# Alte Dateien löschen
rm -rf rtl_power_data/*.csv rtl_power_data/*.png
```

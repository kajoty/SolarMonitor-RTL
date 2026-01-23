# SolarMonitor-RTL - Minimal Scanner

Minimales Setup für kontinuierliches RTL-SDR + HackRF Scanning mit PostgreSQL-Speicherung.

## Dateien

- `frequency_scanner.py` - RTL-SDR Scanner (24-80 MHz Solar Radio)
- `hackrf_scanner.py` - HackRF Scanner (24-80 MHz Solar Radio)
- `postgres_server.py` - REST API → PostgreSQL (192.168.178.100:5432)
- `.env` - Konfiguration

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editiere .env falls nötig
```

## Manuelles Scanning

### PostgreSQL-Server (Port 8002)
```bash
python3 postgres_server.py
```

### RTL-SDR Scanner
```bash
python3 frequency_scanner.py
# Scannt einmal, dann Exit
```

### HackRF Scanner
```bash
python3 hackrf_scanner.py
# Scannt einmal, dann Exit
```

## Automatisches Scanning (Cron)

```bash
# Bearbeite crontab
crontab -e

# Füge hinzu (alle 5 Minuten):
*/5 * * * * cd /home/pi/Projekte/scanner/SolarMonitor-RTL && source venv/bin/activate && python3 frequency_scanner.py >> scanner.log 2>&1
*/5 * * * * cd /home/pi/Projekte/scanner/SolarMonitor-RTL && source venv/bin/activate && python3 hackrf_scanner.py >> scanner.log 2>&1
```

## Datenbank

PostgreSQL auf 192.168.178.100:5432, Datenbank `solarmonitor`, Tabelle `frequency_spectrum`:

| Feld | Typ | Beschreibung |
|---|---|---|
| id | INTEGER | Primary Key |
| timestamp | TEXT | ISO 8601 Zeitstempel |
| band_name | TEXT | "Solar Radio" |
| frequency | REAL | MHz |
| power | REAL | dB |
| receiver | TEXT | "rtl" oder "hackrf" |
| created_at | TIMESTAMP | Server-Zeit |

## Logs

```bash
tail -f scanner.log
```

## Daten prüfen

```bash
psql -h 192.168.178.100 -U admin -d solarmonitor -c "SELECT COUNT(*), receiver FROM frequency_spectrum GROUP BY receiver;"
```

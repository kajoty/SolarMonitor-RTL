# SolarMonitor-RTL (RTL-SDR Only)

Spezialisiertes Setup für kontinuierliches Monitoring von Solar Radio Bursts (26.0–80.0 MHz) mit dem RTL-SDR Dongle und automatischer Speicherung in einer PostgreSQL-Datenbank.

## Kernfunktionen
- **Frequenzbereich:** 26.0 MHz bis 80.0 MHz (optimiert für solares Weltraumwetter).
- **Hardware:** RTL-SDR (RTL2832U / R828D).
- **Backend:** Speicherung in PostgreSQL auf externem Host (`192.168.178.100`).
- **Automatisierung:** Vollautomatisch über Systemd-Timer.

## Dateien
- `frequency_scanner.py`: Haupt-Skript für die Datenerfassung via `rtl_power`.
- `.env`: Konfiguration (Gain, Datenbank-Zugriff, Intervalle).
- `requirements.txt`: Python-Abhängigkeiten.
- `solarmonitor-rtl.service/timer`: Systemd-Konfigurationsdateien.

## Installation & Setup

### 1. System-Abhängigkeiten (Raspberry Pi)
```bash
sudo apt update
sudo apt install librtlsdr-dev rtl-sdr
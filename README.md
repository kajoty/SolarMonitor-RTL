Das ist eine hervorragende und präzise Zusammenfassung für dein neues Setup. Ich habe den Text noch einmal final formatiert, damit er direkt als professionelle README.md genutzt werden kann.Hier ist die finale Version:SolarMonitor-RTL (RTL-SDR Only)Spezialisiertes Setup für kontinuierliches Monitoring von Solar Radio Bursts (26.0–80.0 MHz) mit dem RTL-SDR Dongle und automatischer Speicherung in einer PostgreSQL-Datenbank.KernfunktionenFrequenzbereich: 26.0 MHz bis 80.0 MHz (optimiert für solares Weltraumwetter).Hardware: RTL-SDR (RTL2832U / R828D).Backend: Speicherung in PostgreSQL auf externem Host (192.168.178.100).Automatisierung: Vollautomatisch über Systemd-Timer (kein manueller Cron-Eintrag nötig).Dateienfrequency_scanner.py: Haupt-Skript für die Datenerfassung via rtl_power..env: Konfiguration (Gain, Datenbank-Zugriff, Scan-Intervalle).requirements.txt: Python-Abhängigkeiten.solarmonitor-rtl.service/timer: Systemd-Konfigurationsdateien.Installation & Setup1. System-Abhängigkeiten (Raspberry Pi)Bevor Python gestartet wird, müssen die Hardware-Treiber auf dem Pi installiert sein:Bashsudo apt update
sudo apt install librtlsdr-dev rtl-sdr
2. Python-UmgebungBashpython3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
3. WICHTIG: Python 3.13 Library-FixUnter Python 3.13 auf Linux sucht das Paket pyrtlsdr oft fälschlicherweise nach einer Windows-DLL. Dieser Befehl korrigiert den Pfad innerhalb deiner virtuellen Umgebung:Bashecho '{"x64": "/usr/lib/aarch64-linux-gnu/librtlsdr.so.0", "x86": "/usr/lib/aarch64-linux-gnu/librtlsdr.so.0"}' > venv/lib/python3.13/site-packages/rtlsdr/config.json
Automatisierung (Systemd)Das Projekt wird über einen Systemd-Timer gesteuert, der alle paar Minuten einen Scan auslöst. Dies ist zuverlässiger als ein klassischer Cron-Job.Services installieren & starten:Bash# Dateien kopieren
sudo cp solarmonitor-rtl.service /etc/systemd/system/
sudo cp solarmonitor-rtl.timer /etc/systemd/system/

# Systemd neu laden und Timer aktivieren
sudo systemctl daemon-reload
sudo systemctl enable --now solarmonitor-rtl.timer
Überwachung:Nächster Scan: systemctl list-timers solarmonitor-rtl.timerLive-Logs: journalctl -u solarmonitor-rtl.service -fDatenbank-StrukturDie Daten werden in der Tabelle frequency_spectrum gespeichert. Ein Scan erzeugt ca. 660 Datenpunkte pro Durchlauf.FeldTypBeschreibungtimestampTEXTISO 8601 Zeitstempel (z.B. 2026-01-23T...)band_nameTEXTFestgelegt auf "Solar Radio"frequencyREALFrequenz in MHzpowerREALSignalstärke in dBreceiverTEXTFixer Wert "rtl"
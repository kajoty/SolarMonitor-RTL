# ☀️ SolarMonitor-RTL

Ein automatisiertes Radiospektrometer zur Überwachung solarer Radio-Bursts im Frequenzbereich von **26 MHz bis 80 MHz**. Das System nutzt einen RTL-SDR Dongle, speichert die Daten in einer PostgreSQL-Datenbank und visualisiert sie über ein interaktives Web-Interface.

## 🚀 Features

* **Kontinuierliches Spektrum-Logging:** Erfasst Signalstärken (dB) über das gesamte Band.
* **Langzeit-Archivierung:** Speicherung in PostgreSQL ohne automatisches Löschen.
* **Interaktiver Wasserfall:** Web-Anwendung mit Plotly-Heatmaps.
* **Performance-Optimierung:** Dynamisches Downsampling (Zeit-Aggregierung) bei großen Zeiträumen (z.B. 24h-Ansicht).
* **Präzise Achsen:** Korrekte Darstellung von Frequenz (MHz) und Zeitstempeln durch fixierte Achsen-Typen.

## 🛠 System-Architektur

1. **Datenquelle:** `rtl_power` scannt das Spektrum und schreibt die Daten in die DB.
2. **Datenbank:** PostgreSQL (Langzeit-Speicherung).
3. **Backend:** Flask & SQLAlchemy (Datenabfrage und Downsampling-Logik).
4. **Frontend:** Plotly.js (Interaktive Heatmap im Browser).

## 📦 Installation

### 1. System-Anforderungen

* Raspberry Pi (getestet auf Pi 4B)
* RTL-SDR USB-Dongle
* Installierte Pakete: `rtl-sdr`, `postgresql`, `libpq-dev`

### 2. Projekt-Setup

```bash
# Repository klonen
git clone <dein-repo-link>
cd SolarMonitor-RTL

# Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

```

### 3. Konfiguration

Erstelle eine Datei namens `.env` im Projektordner:

```env
POSTGRES_HOST=localhost
POSTGRES_DB=deine_db
POSTGRES_USER=dein_user
POSTGRES_PASSWORD=dein_passwort

```

## 🖥 Nutzung

### Web-Interface starten

```bash
source venv/bin/activate
python3 app.py

```

Das Interface ist im Netzwerk unter `http://<IP-DEINES-PI>:5000` erreichbar.

### Zeitfilter & Anzeige

Über das Interface können verschiedene Zeitfenster gewählt werden:

* **1h / 3h / 6h:** Volle Auflösung für Detailanalysen.
* **12h / 24h:** Automatisches Downsampling zur Entlastung des Browsers.

## 📊 Datenbank-Struktur

Die Tabelle `frequency_spectrum` sollte wie folgt aufgebaut sein:

| Spalte | Typ | Beschreibung |
| --- | --- | --- |
| **timestamp** | TIMESTAMP | Messzeitpunkt |
| **frequency** | DOUBLE PRECISION | Frequenz in MHz |
| **power** | DOUBLE PRECISION | Pegel in dB |

> **Profi-Tipp:** Erstelle einen Index auf die Spalte `timestamp`, um die Abfragen zu beschleunigen:
> `CREATE INDEX idx_timestamp ON frequency_spectrum (timestamp);`

## 📈 Visualisierung

Die Heatmap nutzt die `Viridis` Farbskala, optimiert auf einen Bereich von **-50 dB bis -20 dB**, um solare Aktivitäten deutlich vom Hintergrundrauschen abzuheben.
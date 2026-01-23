# SolarMonitor-RTL

An automated radio spectrometer for monitoring solar radio bursts in the frequency range of 26 MHz to 80 MHz. The system utilizes an RTL-SDR dongle, stores data in a PostgreSQL database, and visualizes it via an interactive web interface.

## Features

* **Continuous Spectrum Logging:** Captures signal strength (dB) across the entire band.
* **Long-term Archiving:** Persistent storage in PostgreSQL without automatic deletion.
* **Interactive Waterfall:** Web application featuring Plotly heatmaps with zoom and pan.
* **Automated Image Export:** Background service to generate PNG heatmaps every few hours using Matplotlib.
* **Systemd Integration:** Professional automation using systemd services and timers for high reliability.

## System Architecture

1. **Data Source:** `rtl_power` scans the spectrum via a triggered systemd timer.
2. **Database:** PostgreSQL for high-performance retrieval of signal data.
3. **Backend:** Flask & SQLAlchemy providing the API and web server.
4. **Automated Export:** Background script for periodic image generation in `recordings/`.

## Installation

### 1. System Requirements

* Raspberry Pi (tested on Pi 4B)
* RTL-SDR USB dongle
* Packages: `rtl-sdr`, `postgresql`, `libpq-dev`, `python3-pip`

### 2. Project Setup

```bash
git clone https://github.com/kajoty/SolarMonitor-RTL
cd SolarMonitor-RTL
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

### 3. Automated Service Setup

We provide a setup script to install the necessary background services:

```bash
chmod +x setup_services.sh
./setup_services.sh

```

## Usage

### Web Interface

The dashboard is accessible at `http://<YOUR-PI-IP>:5000`. It provides real-time visualization and historical data navigation.

### Data Acquisition

The scanner is controlled by `solarmonitor-rtl.timer`. By default, it triggers a scan every 5 minutes. You can adjust the frequency by editing the timer file:
`sudo nano /etc/systemd/system/solarmonitor-rtl.timer`

## Uninstallation

To remove all installed services and timers from your system, use the provided uninstallation script:

```bash
chmod +x uninstall_services.sh
./uninstall_services.sh

```

## Database Structure

The `frequency_spectrum` table stores the raw data:

| Column | Type | Description |
| --- | --- | --- |
| **timestamp** | TIMESTAMP | Time of measurement |
| **frequency** | DOUBLE PRECISION | Center frequency in MHz |
| **power** | DOUBLE PRECISION | Measured signal level in dB |

**Optimization:**
Ensure an index is created for fast retrieval:
`CREATE INDEX idx_timestamp ON frequency_spectrum (timestamp);`

## Visualization

The heatmap is calibrated to a color range of **-50 dB to -20 dB** (Viridis scale), optimized to highlight solar radio bursts (Type II/III) against background noise.
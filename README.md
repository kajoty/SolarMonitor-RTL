Hier ist die erweiterte, vollständige englische README inklusive der Informationen zum Heatmap-Generator und den App-Details direkt als Text:

# SolarMonitor-RTL

An automated radio spectrometer for monitoring solar radio bursts in the frequency range of 26 MHz to 80 MHz. The system utilizes an RTL-SDR dongle, stores data in a PostgreSQL database, and visualizes it via an interactive web interface.

## Features

* **Continuous Spectrum Logging:** Captures signal strength (dB) across the entire band.
* **Long-term Archiving:** Persistent storage in PostgreSQL without automatic deletion.
* **Interactive Waterfall:** Web application featuring Plotly heatmaps with zoom and pan.
* **Automated Image Export:** Background service to generate PNG heatmaps every few hours.
* **Performance Optimization:** Dynamic downsampling (time aggregation) for large timeframes (e.g., 24h view).
* **Precise Axes:** Accurate representation of frequency (MHz) and timestamps.

## System Architecture

1. **Data Source:** `rtl_power` scans the spectrum and pipes data into the database.
2. **Database:** PostgreSQL for high-performance retrieval of millions of data points.
3. **Backend:** Flask & SQLAlchemy (provides the API and data processing).
4. **Automated Export:** Matplotlib-based script for periodic image generation.
5. **Frontend:** Plotly.js for interactive data exploration.

## Installation

### 1. System Requirements

* Raspberry Pi (tested on Pi 4B)
* RTL-SDR USB dongle
* Installed packages: `rtl-sdr`, `postgresql`, `libpq-dev`, `python3-pip`

### 2. Project Setup

```bash
# Clone the repository
git clone <your-repo-link>
cd SolarMonitor-RTL

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

```

### 3. Configuration

Create a `.env` file in the project root:

```env
POSTGRES_HOST=localhost
POSTGRES_DB=your_db
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password

```

## Usage

### Web Interface (app.py)

The web app provides a real-time dashboard for data exploration. It allows filtering by time (1h to 24h) and handles data reduction automatically to maintain high performance.

```bash
source venv/bin/activate
python3 app.py

```

Access the dashboard at `http://<YOUR-PI-IP>:5000`.

### Automated Heatmap Export (generate_heatmap.py)

This script runs as a continuous background process. It queries the database every few hours and saves a PNG snapshot of the recent spectrum to the `recordings/` folder. It uses Matplotlib for maximum stability on ARM-based systems.

```bash
python3 generate_heatmap.py

```

## System Integration (systemd)

To ensure both the Web App and the Heatmap Generator run automatically after a reboot, it is recommended to use systemd services.

Example for the Heatmap Service (`/etc/systemd/system/solar-heatmap.service`):

```ini
[Unit]
Description=SolarMonitor Heatmap Generator
After=postgresql.service

[Service]
ExecStart=/home/pi/SolarMonitor-RTL/venv/bin/python3 /home/pi/SolarMonitor-RTL/generate_heatmap.py
WorkingDirectory=/home/pi/SolarMonitor-RTL
User=pi
Restart=always

[Install]
WantedBy=multi-user.target

```

## Database Structure

The `frequency_spectrum` table stores the raw data:

| Column | Type | Description |
| --- | --- | --- |
| **timestamp** | TIMESTAMP | Time of measurement (UTC/Local) |
| **frequency** | DOUBLE PRECISION | Center frequency in MHz |
| **power** | DOUBLE PRECISION | Measured signal level in dB |

**Optimization:**
To maintain query speed as the database grows, an index on the timestamp column is essential:
`CREATE INDEX idx_timestamp ON frequency_spectrum (timestamp);`

## Visualization

The heatmap is calibrated to a color range of **-50 dB to -20 dB** (Viridis scale). This specific range is optimized to distinguish solar radio bursts (Type II/III) from the typical RF background noise of the RTL-SDR hardware.
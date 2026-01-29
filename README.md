# SolarMonitor-RTL v2.5

An automated radio spectrometer for monitoring solar radio bursts in the frequency range of 26 MHz to 80 MHz. The system utilizes RTL-SDR hardware, a PostgreSQL database for long-term data storage, and a Flask-based dashboard featuring automatic signal normalization.

## Core Features

* **Intelligent Gain Control:** Automatically calibrates RTL-SDR gain by analyzing the FM broadcast band (88-108 MHz) to prevent clipping and maximize dynamic range.
* **Astronomical Awareness:** Calculates solar phases (Day, Night, Twilight) based on GPS coordinates to dynamically adjust scan intervals and provide context for solar events.
* **Signal Normalization:** Stores active hardware gain for every sample. Visualizations calculate (Power - Gain), enabling drift-free heatmaps without brightness jumps during gain transitions.
* **Modern Dashboard:** Dark-mode web interface featuring live statistics, 48-hour dynamic trend graphs, and automated waterfall diagrams.

## System Architecture

1. **Scanner (frequency_scanner.py):** The data collection engine. Controls rtl_power, calculates solar phases, and manages gain regulation.
2. **Visualizer (generate_heatmap.py):** A background service that generates PNG graphics from the database every 5 minutes.
3. **Web Interface (app.py):** A Flask server (Port 5001) providing the dashboard and serving the generated images.
4. **Database:** PostgreSQL used for storing high-resolution spectral data.

## Installation and Setup

### 1. System Requirements

* Raspberry Pi (tested on Pi 4B with OS Bookworm)
* RTL-SDR USB dongle
* Software: rtl-sdr, postgresql-client, python3-pip, python3-venv

### 2. Project Installation

```bash
git clone https://github.com/kajoty/SolarMonitor-RTL
cd SolarMonitor-RTL
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

### 3. Environment Configuration (.env)

Create a .env file in the root directory. Note that here PostgreSQL is explicitly configured for Port 5433. While Port 5432 is the standard, this specific setup accounts for environments where two PostgreSQL installations are running simultaneously.

```ini
# Database Configuration
POSTGRES_HOST=192.168.178.100
POSTGRES_PORT=5433
POSTGRES_DB=solarmonitor
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_password

# RTL-SDR and Location
RTL_DEVICE_INDEX=0
RTL_GAIN=25.4
LATITUDE=52.52
LONGITUDE=13.40

# Frequency Range
SOLAR_FREQ_START=26.0
SOLAR_FREQ_END=80.0

```

### 4. Database Initialization

Before running the scanner, initialize the database structure. The following script checks if the required tables exist and creates them if necessary:

```bash
python3 db_setup.py

```

## Database Schema

The system uses a PostgreSQL table named frequency_spectrum. The schema is optimized for both raw data storage and normalized visualization:

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| **id** | INTEGER | No | Primary key (auto-incrementing) |
| **timestamp** | TIMESTAMP | No | Precise time of the radio scan |
| **band_name** | TEXT | No | Solar_Radio or Diagnostic_FM |
| **frequency** | DOUBLE PRECISION | No | Center frequency in MHz |
| **power** | DOUBLE PRECISION | No | Measured signal level in dB |
| **receiver** | TEXT | Yes | Hardware identifier (e.g., rtl) |
| **applied_gain** | DOUBLE PRECISION | Yes | The gain value used by the SDR during the scan |
| **sun_phase** | VARCHAR | Yes | Astronomical state: day, night, or twilight |
| **created_at** | TIMESTAMP | Yes | Database-side record creation timestamp |

### Data Normalization

To achieve consistent visualization regardless of automatic gain adjustments, the following calculation is applied within the SQL queries:
`normalized_power = power - applied_gain`

## Operation

### Hardware Safety (Watchdog)

To ensure the Pi reboots automatically in case of a system hang, enable the hardware watchdog:

```bash
echo "dtparam=watchdog=on" | sudo tee -a /boot/firmware/config.txt

```

### Running the Services

It is recommended to set up the scripts as systemd services. For manual testing:

1. **Scanner:** `python3 frequency_scanner.py` (typically triggered via Cron)
2. **Heatmap Generator:** `python3 generate_heatmap.py` (runs continuously)
3. **Web App:** `python3 app.py` (runs continuously on Port 5001)

## Visualization Logic

The scripts internally use the following formula to eliminate hardware influence:



This allows for consistent comparison of solar bursts even when the system increases gain during night or twilight phases.

---
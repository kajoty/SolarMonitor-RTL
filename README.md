
# SolarMonitor-RTL

An automated radio spectrometer for monitoring solar radio bursts in the frequency range of 26 MHz to 80 MHz. The system utilizes an RTL-SDR dongle, stores data in a PostgreSQL database, and visualizes it via an interactive web interface.

## New Features (v2.0)

* **Dynamic Gain Control:** Automatically calibrates the RTL-SDR gain by analyzing FM broadcast signals to prevent clipping and maximize sensitivity.
* **Astronomical Awareness:** Calculates local solar phases (Day, Night, Twilight) using GPS coordinates to adapt scan intervals and provide context for solar events.
* **Signal Normalization:** Stores applied gain values alongside power levels to allow "drift-free" visualization by normalizing data (Power - Gain).
* **Smart Diagnostic Windows:** Periodically switches to the FM band to recalibrate the hardware without losing significant solar monitoring time.

## System Architecture

1. **Data Source:** `rtl_power` scans the spectrum, controlled by a Python wrapper that manages gain and frequency bands.
2. **Database:** PostgreSQL stores raw signal data, applied gain, and astronomical metadata.
3. **Astronomy Engine:** `astral` library provides precise sunrise/sunset times for the sensor location.
4. **Backend:** Flask & SQLAlchemy providing the API and web server.

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
pip install astral  # New dependency for solar calculations

```

### 3. Environment Configuration (`.env`)

Create a `.env` file with your location and database credentials:

```bash
POSTGRES_HOST=192.168.178.100
POSTGRES_DB=solarmonitor
RTL_GAIN=25.4  # Default starting gain
LATITUDE=52.52
LONGITUDE=13.40

```

## Database Structure

The `frequency_spectrum` table has been upgraded to track hardware and astronomical states:

| Column | Type | Description |
| --- | --- | --- |
| **timestamp** | TIMESTAMP | Time of measurement |
| **band_name** | TEXT | "Solar_Radio" or "Diagnostic_FM" |
| **frequency** | DOUBLE PRECISION | Center frequency in MHz |
| **power** | DOUBLE PRECISION | Measured signal level in dB |
| **applied_gain** | DOUBLE PRECISION | The hardware gain used for this sample |
| **sun_phase** | VARCHAR(20) | "day", "night", or "twilight" |

**Database Upgrade SQL:**

```sql
ALTER TABLE frequency_spectrum ADD COLUMN applied_gain FLOAT DEFAULT 0.0;
ALTER TABLE frequency_spectrum ADD COLUMN sun_phase VARCHAR(20);
CREATE INDEX idx_spectrum_gain_phase ON frequency_spectrum (timestamp DESC, sun_phase);

```

## Usage

### Dynamic Gain Logic

The scanner automatically switches to **Diagnostic_FM** (88-108 MHz) every 30 minutes (10 minutes during twilight). It analyzes the peak power of local radio stations and adjusts the `gain_state.txt` to keep the hardware in its linear range (Target: -12 dB peak).

### Visualization & Normalization

To eliminate "brightness stripes" in your heatmap caused by gain changes, use the following SQL logic in your visualization tool (e.g., Grafana):
`SELECT timestamp, frequency, (power - applied_gain) AS normalized_power FROM frequency_spectrum;`

---

## Uninstallation

To remove all installed services and timers:

```bash
chmod +x uninstall_services.sh
./uninstall_services.sh

```
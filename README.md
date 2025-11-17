# SolarMonitor-RTL - RTL-SDR Frequency Monitoring System

RTL-SDR frequency monitoring system for Raspberry Pi utilizing SQLite for time-series data storage and REST API for data access and visualization.

## Overview

SolarMonitor-RTL is a complete system for continuous radio frequency spectrum monitoring using an RTL2838 DVB-T USB dongle. The system captures spectrum data in the solar radio band (20-80 MHz), stores measurements in SQLite, and provides comprehensive visualization through REST APIs and web dashboards.

**System Status:** Operational - Core components functional and deployed  
**Deployment Method:** Systemd services with automatic restart on failure  
**Current Data:** 42,500+ spectrum measurements across 85+ scans

## Hardware Requirements

### Minimum Setup
- Raspberry Pi 4B (2GB+ RAM) with Raspbian or Debian-based OS
- RTL2838 DVB-T USB Dongle (Realtek Semiconductor)
  - USB Identifiers: `0bda:2838`
  - Tuner: Rafael Micro R828D
  - Frequency Range: 24-1766 MHz (optimized for 470-862 MHz DVB-T)
  - Sample Rate: 2 MSps

## Installation

### 1. Repository Setup

```bash
cd /home/pi/Projekte/solarmonitor
git clone https://github.com/kajoty/SolarMonitor-RTL.git
cd SolarMonitor-RTL

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configuration

Create `.env` file from template:

```bash
cp .env.example .env
nano .env
```

Required configuration variables:

```env
RTL_DEVICE_INDEX=0
RTL_SAMPLE_RATE=2000000
RTL_GAIN=auto

SQLITE_DATABASE=spectrum.db
SCAN_INTERVAL_MINUTES=1
```

### 3. Service Installation

```bash
sudo bash install_service.sh
```

This installs two systemd services:
- `solarmonitor-sqlite.service` - SQLite REST API server (port 8002)
- `solarmonitor-app.service` - Flask application server (port 5000)

Both services are configured for automatic startup on system boot and automatic restart on failure.

### 4. Service Management

```bash
# Check service status
sudo systemctl status solarmonitor-sqlite.service
sudo systemctl status solarmonitor-app.service

# Restart services
sudo systemctl restart solarmonitor-app.service
sudo systemctl restart solarmonitor-sqlite.service

# View service logs
sudo journalctl -u solarmonitor-app.service -f
sudo journalctl -u solarmonitor-sqlite.service -f

# Stop services
sudo systemctl stop solarmonitor-app.service
sudo systemctl stop solarmonitor-sqlite.service

# Disable auto-start
sudo systemctl disable solarmonitor-app.service
sudo systemctl disable solarmonitor-sqlite.service
```

## Quick Start (Manual Execution)

### Development Mode

```bash
source venv/bin/activate
python3 app.py
```

Output indicates successful initialization:
```
INFO:__main__:SQLite database connected
INFO:__main__:RTL-SDR scanner initialized
INFO:__main__:Scanner running on background thread
 * Running on http://0.0.0.0:5000
```

### Web Interfaces

Access via web browser:

1. **Heatmap Dashboard** - `http://localhost:5000/`
   - Time-frequency visualization of spectrum data
   - Time range selection: 1h, 6h, 24h, 7d, 30d, custom intervals
   - Colormap options: viridis, plasma, jet, hot, magma, and 12+ others
   - PNG export functionality

2. **Discovery Dashboard** - `http://localhost:5000/discovery`
   - Frequency band scanning and analysis
   - Signal-to-noise ratio and activity metrics per band
   - Band recommendations based on signal strength

## System Architecture

### Data Flow

```
RTL-SDR Hardware
      |
      v
frequency_scanner.py (capture + FFT analysis)
      |
      v
spectrum_analyzer.py (signal processing)
      |
      v
SQLite Database (spectrum.db)
      |
      +---> sqlite_server.py (REST API, port 8002)
      |
      v
Flask Application (port 5000)
      |
      +---> heatmap_generator.py (visualization)
      |
      v
Web Browsers / Clients
```

### Core Components

| Component | File | Function |
|-----------|------|----------|
| Flask Server | `app.py` | REST API endpoints, scheduling, health monitoring |
| RTL-SDR Interface | `frequency_scanner.py` | Hardware control, FFT computation, scan execution |
| Data Storage | `sqlite_server.py` | SQLite REST wrapper, query handler, data persistence |
| Heatmap Visualization | `heatmap_generator.py` | FFT array generation, matplotlib rendering |
| Spectrum Analysis | `spectrum_analyzer.py` | Signal metrics computation, visualization generation |
| Web Dashboards | `templates/` | HTML/JavaScript client interfaces |

### Analysis Tools

| Tool | File | Purpose |
|------|------|---------|
| Signal Quality Analysis | `analyze_signal_quality.py` | Non-intrusive analysis of stored spectrum data |
| Gain Optimization | `optimize_gain.py` | Automated testing of gain values for optimal SNR |
| Daily Heatmap Archive | `save_daily_heatmaps.py` | Automatic daily heatmap archival with multiple colormaps |

## Configuration Details

### RTL-SDR Parameters

**Frequency Bands Monitored:**

| Band Name | Range | Resolution | Measurements per Scan |
|-----------|-------|------------|-----------------------|
| Solar Radio | 20-80 MHz | 0.12 MHz | 500 frequencies |

**Gain Settings:**

```env
RTL_GAIN=auto      # Automatic (default, recommended)
RTL_GAIN=25.4      # Moderate amplification
RTL_GAIN=42.1      # High amplification (current setting)
RTL_GAIN=49.6      # Maximum (high noise floor)
```

### Scan Parameters

```env
SCAN_INTERVAL_MINUTES=1     # Frequency of measurement scans
SAMPLE_RATE=2000000         # Digital samples per second
```

## REST API Specification

### Heatmap Endpoints

```
GET /api/heatmap
  Parameters:
    time_range: '1h' | '6h' | '24h' | '7d' | '30d'
    OR
    start_time: ISO-8601 timestamp
    end_time: ISO-8601 timestamp
    
    cmap: colormap name (default: 'viridis')
    format: 'json' | 'png' (default: 'png')
  
  Returns: PNG image or JSON array
```

Example requests:

```bash
# Heatmap for last 24 hours as PNG
curl 'http://localhost:5000/api/heatmap?time_range=24h&cmap=viridis'

# Custom time interval as JSON
curl 'http://localhost:5000/api/heatmap?start_time=2025-11-17T00:00:00&end_time=2025-11-17T12:00:00&format=json'

# Available time range presets
curl 'http://localhost:5000/api/time-ranges'

# Available colormaps
curl 'http://localhost:5000/api/colormaps'

# System health status
curl 'http://localhost:5000/api/health'
```

### SQLite REST API (Port 8002)

```
GET /api/read
  Parameters:
    time_range: relative time range ('1h', '6h', '24h', '7d', '30d')
    OR
    start_time: ISO-8601 timestamp
    end_time: ISO-8601 timestamp
  
  Returns: {"timestamps": [...], "frequencies": [...], "data": [[...]]}

GET /api/stats
  Returns: {"total_points": N, "total_scans": M, "latest_timestamp": "..."}

GET /health
  Returns: {"status": "ok"} or {"error": "..."}
```

## Database Schema

### SQLite Table: frequency_spectrum

```sql
CREATE TABLE frequency_spectrum (
    timestamp TEXT NOT NULL,
    frequency REAL NOT NULL,
    power REAL NOT NULL,
    band_name TEXT
)

CREATE INDEX idx_timestamp ON frequency_spectrum(timestamp);
CREATE INDEX idx_band ON frequency_spectrum(band_name);
CREATE INDEX idx_ts_band ON frequency_spectrum(timestamp, band_name);
```

**Data Characteristics:**
- Timestamp: ISO-8601 format, UTC timezone
- Frequency: MHz (range: 20-80 for solar radio band)
- Power: dB scale
- Storage: ~500 KB per day for current scan interval

## Analysis Tools Usage

### Signal Quality Analysis

Non-intrusive analysis of stored data without accessing RTL-SDR hardware:

```bash
python3 analyze_signal_quality.py
python3 analyze_signal_quality.py --time-range 24h
python3 analyze_signal_quality.py --time-range 7d
```

Output: PNG visualization with 4 panels (SNR, dynamic range, activity, frequency distribution)

### Gain Optimization

Automated testing to find optimal gain value:

```bash
sudo python3 optimize_gain.py
sudo python3 optimize_gain.py --duration 5 --tests 10
```

Requires sudo (manages systemd services). Automatically:
- Stops Flask services
- Tests 8-10 different gain values
- Generates performance metrics and visualization
- Recommends optimal gain setting

### Daily Heatmap Archival

Archive heatmaps by date with multiple colormaps:

```bash
python3 save_daily_heatmaps.py                    # Today
python3 save_daily_heatmaps.py --date yesterday
python3 save_daily_heatmaps.py --date 2025-11-15
python3 save_daily_heatmaps.py --cmap viridis --cmap plasma --cmap jet

# Date range
python3 save_daily_heatmaps.py --from 2025-11-01 --to 2025-11-15 --cmap viridis
```

Cronjob example (archive daily at 23:55):
```
55 23 * * * cd /home/pi/Projekte/solarmonitor/SolarMonitor-RTL && source venv/bin/activate && python3 save_daily_heatmaps.py
```

Directory structure created: `heatmaps/YYYY-MM-DD/{heatmap_*.png, metadata.json}`

## Performance Specifications

### Current System Metrics

| Metric | Value |
|--------|-------|
| Database Size | ~500 KB per day |
| Total Data Points | 42,500+ (85+ scans) |
| Scan Duration | 25-30 seconds per scan |
| Scan Interval | 60 seconds |
| Heatmap Generation | ~1 second |
| API Response Time | <100 ms |
| Memory Usage | ~80-120 MB (app + sqlite server) |

### Hardware Resource Utilization

- CPU: 3-5% during normal scanning
- RAM: 120 MB baseline, 200-250 MB with heatmap generation
- Disk I/O: Minimal (sequential writes, ~1 KB/s during scans)
- Network: None (local SQLite only)

## Troubleshooting

### RTL-SDR Device Not Detected

```bash
# Verify USB device
lsusb | grep -i realtek
# Expected output: "ID 0bda:2838 Realtek Semiconductor Corp."

# Check device permissions
ls -la /dev/bus/usb/001/

# Verify in Python
python3 -c "from rtlsdr import RtlSdr; r = RtlSdr(); print(r.is_connected)"
```

### SQLite Connection Failures

```bash
# Verify REST API is running
curl http://localhost:8002/health

# Check database file
ls -lh spectrum.db

# Test direct SQLite access
sqlite3 spectrum.db "SELECT COUNT(*) FROM frequency_spectrum;"
```

### Flask Service Fails to Start

```bash
# Check service logs
sudo journalctl -u solarmonitor-app.service -n 100

# Verify manual execution
source venv/bin/activate
python3 app.py

# Check port binding
lsof -i :5000

# Verify .env file
cat .env | head -10
```

### Systemd Service Stuck in Auto-Restart

```bash
# Check service status
sudo systemctl status solarmonitor-app.service

# View recent log entries
sudo journalctl -u solarmonitor-app.service --since "10 minutes ago"

# Manual service restart
sudo systemctl restart solarmonitor-app.service

# If RTL-SDR is busy
lsof | grep -i rtl
ps aux | grep python3
sudo pkill -9 python3  # Force kill if necessary
```

## Project Structure

```
SolarMonitor-RTL/
├── app.py                           # Flask REST API (main server)
├── sqlite_server.py                 # SQLite wrapper with REST API
├── frequency_scanner.py             # RTL-SDR hardware interface
├── heatmap_generator.py             # FFT visualization engine
├── spectrum_analyzer.py             # Signal processing utilities
├── analyze_signal_quality.py        # Stored data analysis tool
├── optimize_gain.py                 # Gain testing utility
├── save_daily_heatmaps.py          # Daily archive generator
│
├── templates/
│   ├── dashboard.html               # Heatmap web interface
│   └── discovery.html               # Frequency discovery interface
│
├── solarmonitor-sqlite.service      # SQLite service definition
├── solarmonitor-app.service         # Flask service definition
├── install_service.sh               # Service installation script
│
├── requirements.txt                 # Python dependencies
├── .env.example                     # Configuration template
├── .gitignore                       # Git exclusion rules
│
├── README.md                        # This file
├── QUICKSTART.md                    # Quick start guide
├── HEATMAP_GUIDE.md                 # Heatmap API documentation
├── FREQUENCY_DISCOVERY_GUIDE.md     # Discovery system documentation
│
└── venv/                            # Python virtual environment
```

## Development Notes

### Code Organization

**app.py (470 lines)**
- Flask application initialization
- Route definitions for REST API endpoints
- Background scheduler for RTL-SDR scans
- Health check implementation
- Time range preset calculation

**sqlite_server.py (280 lines)**
- SQLite database wrapper
- REST API server (Flask, port 8002)
- Query parameter parsing
- Data serialization and response formatting

**heatmap_generator.py (380 lines)**
- FFT data retrieval from SQLite
- Matplotlib figure generation
- Height scaling based on data volume
- Multiple colormap support
- PNG encoding and transmission

**frequency_scanner.py (420 lines)**
- RTL-SDR initialization and configuration
- FFT computation (numpy.fft)
- Background scanning thread
- Data validation and preprocessing

**Analysis utilities (1000+ lines combined)**
- Signal quality metrics computation
- Gain value testing orchestration
- Daily heatmap generation with metadata

### Testing

Demo mode without RTL-SDR hardware:

```bash
python3 demo_test.py
```

Unit tests for core functionality:

```bash
python3 -m pytest tests/
```

## Known Limitations

1. RTL-SDR device requires exclusive access - systemd ensures clean management
2. Heatmap height scales with data volume - large time ranges may exceed display area
3. SQLite concurrent write limitations - sequential scan operations sufficient for current use case
4. Frequency resolution fixed at 500 points per band - adjust in `frequency_scanner.py` if needed
5. Web dashboards require modern browser with JavaScript support

## Maintenance

### Regular Tasks

Daily heatmap archival (automated via cronjob):
```bash
python3 save_daily_heatmaps.py
```

Weekly backup of SQLite database:
```bash
cp spectrum.db spectrum.db.backup.$(date +%Y%m%d)
```

### Performance Optimization

Signal quality analysis to identify optimal frequency ranges:
```bash
python3 analyze_signal_quality.py --time-range 30d
```

Gain optimization for current environmental conditions:
```bash
sudo python3 optimize_gain.py --duration 30
```

## References

- RTL-SDR Documentation: https://osmocom.org/projects/rtl-sdr/
- Raspberry Pi: https://www.raspberrypi.org/
- Matplotlib: https://matplotlib.org/
- Flask: https://flask.palletsprojects.com/
- SQLite: https://www.sqlite.org/

## License

MIT License

## Version Information

Version: 1.0  
Last Updated: November 2025  
Status: Production

# SolarMonitor-RTL

RTL-SDR frequency monitoring system for Raspberry Pi. Captures radio frequency spectrum in the 20-80 MHz band using an RTL2838 DVB-T USB dongle, stores data in SQLite, and provides visualization via REST API and web interface.

## System Overview

Continuous spectrum monitoring using RTL-SDR hardware on Raspberry Pi 4B. Frequency range: 20-80 MHz (solar radio band). Data stored in local SQLite database with REST API access. Web dashboards for visualization and analysis.

## Hardware

**Required:**
- Raspberry Pi 4B (2GB+ RAM)
- RTL2838 DVB-T USB Dongle (Realtek 0bda:2838)
- USB 2.0 port with extension cable (USB 3.0 causes interference)

**Specifications:**
- Tuner: Rafael Micro R828D
- Sample rate: 2 MSps
- Frequency range: 24-1766 MHz
- Frequency resolution: 500 points per scan = 0.12 MHz per point
- Scan interval: 60 seconds

## Installation

Clone repository and set up Python environment:

```bash
git clone https://github.com/kajoty/SolarMonitor-RTL.git
cd SolarMonitor-RTL
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Configure `.env`:

```bash
cp .env.example .env
```

Install systemd services:

```bash
sudo bash install_service.sh
```

This creates two services running automatically on boot:
- `solarmonitor-sqlite.service` (port 8002)
- `solarmonitor-app.service` (port 5000)

## Usage

**Check status:**
```bash
sudo systemctl status solarmonitor-sqlite.service
sudo systemctl status solarmonitor-app.service
```

**View logs:**
```bash
sudo journalctl -u solarmonitor-app.service -f
```

**Manual start (development):**
```bash
source venv/bin/activate
python3 app.py
```

**Web interfaces:**
- Heatmap Dashboard: `http://localhost:5000/`
- Discovery Dashboard: `http://localhost:5000/discovery`

## Architecture

RTL-SDR dongle → FFT analysis → SQLite database → REST API (port 8002) → Flask app (port 5000) → Web interface

**Components:**
- `frequency_scanner.py` - RTL-SDR hardware interface, FFT computation
- `sqlite_server.py` - SQLite REST API wrapper
- `heatmap_generator.py` - Matplotlib visualization
- `app.py` - Flask REST API server
- `spectrum_analyzer.py` - Signal processing and metrics
- `templates/` - Web UI (dashboard.html, discovery.html)

**Analysis tools:**
- `analyze_signal_quality.py` - Signal quality metrics from stored data
- `optimize_gain.py` - Automated gain value testing
- `save_daily_heatmaps.py` - Daily heatmap archival

## Configuration

`.env` file contains all settings. Key parameters:

```env
RTL_DEVICE_INDEX=0              # USB device index
RTL_SAMPLE_RATE=2000000         # Samples per second
RTL_GAIN=auto                   # Gain setting (auto recommended)
SQLITE_DATABASE=spectrum.db     # Database file
SCAN_INTERVAL_MINUTES=1         # Scan frequency
```

Gain values: 0-49.6 dB or 'auto'. Recommended: 25.4 or 42.1 dB.

## API

**Heatmap endpoint:**

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
```

**SQLite REST API (port 8002):**

```bash
curl 'http://localhost:8002/api/stats'
curl 'http://localhost:8002/api/read?time_range=24h'
curl 'http://localhost:8002/health'
```

## Database

SQLite file: `spectrum.db`

Table `frequency_spectrum`:
- timestamp (ISO-8601 UTC)
- frequency (MHz)
- power (dB)
- band_name

Typical storage: ~500 KB per day at 60-second scan interval.

## Tools

**Signal Quality Analysis:**
```bash
python3 analyze_signal_quality.py --time-range 24h
```
Outputs SNR, dynamic range, activity metrics from stored data.

**Gain Optimization:**
```bash
sudo python3 optimize_gain.py --duration 5
```
Tests gain values automatically. Requires sudo.

**Daily Heatmap Archive:**
```bash
python3 save_daily_heatmaps.py --date today --cmap viridis
```
Archives heatmaps with multiple colormaps.

## Troubleshooting

**RTL-SDR not detected:**
```bash
lsusb | grep -i realtek
# Should show: ID 0bda:2838
```

**USB interference:**
Use USB 2.0 port with extension cable. USB 3.0 causes RF noise in this frequency range.

**Service fails to start:**
```bash
sudo journalctl -u solarmonitor-app.service -n 50
```

**RTL-SDR device busy:**
```bash
ps aux | grep python3
sudo systemctl restart solarmonitor-app.service
```

## Project Files

Core:
- `app.py` - Flask REST API server
- `sqlite_server.py` - SQLite REST wrapper
- `frequency_scanner.py` - RTL-SDR interface
- `heatmap_generator.py` - Visualization
- `spectrum_analyzer.py` - Signal processing

Tools:
- `analyze_signal_quality.py` - Data analysis
- `optimize_gain.py` - Gain testing
- `save_daily_heatmaps.py` - Daily archive

Web:
- `templates/dashboard.html` - Heatmap interface
- `templates/discovery.html` - Discovery interface

Services:
- `solarmonitor-sqlite.service`
- `solarmonitor-app.service`
- `install_service.sh`

Configuration:
- `.env.example` - Configuration template
- `requirements.txt` - Python dependencies
- `.gitignore` - Git exclusion rules

## Performance

Current system (Raspberry Pi 4B):
- CPU: 3-5% during scanning
- Memory: 120-250 MB
- Scan duration: 25-30 seconds
- Scan interval: 60 seconds
- API response: <100 ms
- Database growth: ~500 KB/day

## License

MIT

Version: 1.0 | Updated: November 2025 | Status: Production
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

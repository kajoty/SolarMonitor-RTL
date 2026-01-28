import numpy as np
import logging
import os
import subprocess
import shutil
from datetime import datetime, timezone
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
from astral import LocationInfo
from astral.sun import sun

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pfad für den gespeicherten Gain-Zustand (Gedächtnis des Skripts)
GAIN_STATE_FILE = os.path.join(os.path.dirname(__file__), 'gain_state.txt')

def get_sun_phase(lat, lon):
    """Berechnet die astronomische Phase basierend auf Koordinaten."""
    try:
        city = LocationInfo(latitude=float(lat), longitude=float(lon))
        s = sun(city.observer, date=datetime.now().date())
        now = datetime.now(timezone.utc)
        
        # Fenster für Dämmerung: +/- 30 Minuten um Auf-/Untergang
        margin = 30 
        
        if (abs((now - s['sunrise']).total_seconds()) < margin * 60) or \
           (abs((now - s['sunset']).total_seconds()) < margin * 60):
            return "twilight"
        elif s['sunrise'] < now < s['sunset']:
            return "day"
        else:
            return "night"
    except Exception as e:
        logger.error(f"Fehler bei Sonnenphasen-Berechnung: {e}")
        return "unknown"

def load_current_gain():
    """Lädt den zuletzt gespeicherten Gain-Wert oder nutzt den Standard aus .env"""
    load_dotenv()
    default_gain = float(os.getenv('RTL_GAIN', '25.4'))
    if os.path.exists(GAIN_STATE_FILE):
        try:
            with open(GAIN_STATE_FILE, 'r') as f:
                return float(f.read().strip())
        except Exception:
            return default_gain
    return default_gain

def save_new_gain(new_gain):
    """Speichert den neu berechneten Gain-Wert für den nächsten Lauf."""
    try:
        with open(GAIN_STATE_FILE, 'w') as f:
            f.write(str(round(new_gain, 1)))
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Gain-Zustands: {e}")

def calculate_optimized_gain(power_values, current_gain):
    """Analysiert den FM-Peak und schlägt eine Gain-Anpassung vor."""
    if not power_values:
        return current_gain
    
    max_p = max(power_values)
    target = -12.0  # Ziel-Peak im FM-Band (Sicherheitsabstand zur Sättigung)
    diff = max_p - target
    
    # Korrekturfaktor (0.4) verhindert zu starkes Schwingen der Regelung
    if abs(diff) > 1.5:
        adjustment = diff * 0.4
        new_gain = current_gain - adjustment
        # RTL-SDR Hardware-Limits einhalten
        return max(0.0, min(49.6, new_gain))
    return current_gain

def run_scan():
    load_dotenv()
    
    # 1. Parameter laden
    gain_val = load_current_gain()
    device_idx = int(os.getenv('RTL_DEVICE_INDEX', 0))
    lat = os.getenv('LATITUDE', '52.52')
    lon = os.getenv('LONGITUDE', '13.40')
    
    current_sun_phase = get_sun_phase(lat, lon)
    minute = datetime.now().minute
    
    # 2. Intervall-Logik: In der Dämmerung öfter FM-Diagnose zur Gain-Anpassung
    interval = 10 if current_sun_phase == "twilight" else 30
    is_diagnostic = (minute % interval == 0) and (0 <= minute % interval <= 4)

    if is_diagnostic:
        f_start, f_end = 88.0, 108.0
        current_band = "Diagnostic_FM"
    else:
        f_start = float(os.getenv('SOLAR_FREQ_START', 26.0))
        f_end = float(os.getenv('SOLAR_FREQ_END', 80.0))
        current_band = "Solar_Radio"

    logger.info(f"📡 Start {current_band} | Phase: {current_sun_phase} | Gain: {gain_val:.1f}")

    try:
        rtl_power_path = shutil.which('rtl_power') or '/usr/bin/rtl_power'
        # Scan-Parameter: 100kHz Bins, 2 Sekunden Integrationszeit
        freq_range = f"{int(f_start * 1e6)}:{int(f_end * 1e6)}:100000,2s"
        
        cmd = [rtl_power_path, '-f', freq_range, '-g', str(gain_val), '-d', str(device_idx), '-1']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if not result.stdout.strip():
            logger.error("❌ Keine Daten von rtl_power erhalten.")
            return

        # 3. Datenverarbeitung
        frequencies, power_values = [], []
        for line in result.stdout.strip().split('\n'):
            parts = line.split(',')
            if len(parts) < 7: continue
            
            s_f, e_f, n_bins = float(parts[2]), float(parts[3]), int(parts[5])
            
            # Korrigierte Zeile: n_bins statt num_bins
            bin_powers = [float(x) for x in parts[6:6+n_bins] if x.strip()]
            
            freq_array = np.linspace(s_f, e_f, len(bin_powers), endpoint=False)
            frequencies.extend(freq_array / 1e6)
            power_values.extend(bin_powers)

        # 4. Dynamische Gain-Regelung (nur nach Diagnostic-Scan)
        if is_diagnostic and power_values:
            new_gain = calculate_optimized_gain(power_values, gain_val)
            if abs(new_gain - gain_val) > 0.1:
                save_new_gain(new_gain)
                logger.info(f"⚖️ Gain angepasst: {gain_val:.1f} -> {new_gain:.1f} (Peak war {max(power_values):.1f}dB)")

        # 5. Datenbank-Speicherung
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            database=os.getenv('POSTGRES_DB'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD')
        )
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        data_points = [
            (timestamp, current_band, float(f), float(p), 'rtl', gain_val, current_sun_phase)
            for f, p in zip(frequencies, power_values)
        ]
        
        if data_points:
            query = """
                INSERT INTO frequency_spectrum 
                (timestamp, band_name, frequency, power, receiver, applied_gain, sun_phase) 
                VALUES %s
            """
            execute_values(cursor, query, data_points)
            conn.commit()
            logger.info(f"✅ {len(data_points)} Punkte gespeichert.")
        
        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Kritischer Fehler im Scan-Prozess: {e}")

if __name__ == "__main__":
    run_scan()
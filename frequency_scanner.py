import numpy as np
import logging
import os
import subprocess
import shutil
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_scan():
    load_dotenv()
    
    # Konfiguration aus .env
    gain_val = os.getenv('RTL_GAIN', '25.4')
    device_idx = int(os.getenv('RTL_DEVICE_INDEX', 0))
    
    # Zeit-Logik für 5-Minuten-Fenster
    minute = datetime.now().minute
    
    # Diagnose-Fenster: 0-4, 20-24, 40-44 Minuten der Stunde
    if (0 <= minute <= 4) or (20 <= minute <= 24) or (40 <= minute <= 44):
        f_start = 88.0
        f_end = 108.0
        current_band = "Diagnostic_FM"
        logger.info(f"🔍 Diagnostic-Scan Fenster ({minute}m): {f_start} - {f_end} MHz")
    else:
        # Standard Solar-Bereich aus .env
        f_start = float(os.getenv('SOLAR_FREQ_START', 26.0))
        f_end = float(os.getenv('SOLAR_FREQ_END', 80.0))
        current_band = "Solar_Radio"
        logger.info(f"🚀 Solar-Scan Modus ({minute}m): {f_start} - {f_end} MHz")

    try:
        rtl_power_path = shutil.which('rtl_power') or '/usr/bin/rtl_power'
        # Integrationszeit auf 2s erhöht für bessere Signalqualität
        freq_range = f"{int(f_start * 1e6)}:{int(f_end * 1e6)}:100000,2s"
        
        cmd = [rtl_power_path, '-f', freq_range, '-g', str(gain_val), '-d', str(device_idx), '-1']
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if not result.stdout.strip():
            logger.error("❌ Keine Daten von rtl_power")
            return

        frequencies = []
        power_values = []
        
        for line in result.stdout.strip().split('\n'):
            parts = line.split(',')
            if len(parts) < 7: continue
            
            s_freq = float(parts[2])
            e_freq = float(parts[3])
            num_bins = int(parts[5])
            
            bin_powers = [float(x) for x in parts[6:6+num_bins]]
            freq_array = np.linspace(s_freq, e_freq, len(bin_powers), endpoint=False)
            
            frequencies.extend(freq_array / 1e6)
            power_values.extend(bin_powers)

        # Datenbank-Verbindung
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            database=os.getenv('POSTGRES_DB'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD')
        )
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        data_points = [
            (timestamp, current_band, float(f), float(p), 'rtl')
            for f, p in zip(frequencies, power_values)
        ]
        
        if data_points:
            execute_values(
                cursor,
                "INSERT INTO frequency_spectrum (timestamp, band_name, frequency, power, receiver) VALUES %s",
                data_points
            )
            conn.commit()
            logger.info(f"✅ {len(data_points)} Punkte als '{current_band}' gespeichert.")
        
        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Fehler: {e}")

if __name__ == "__main__":
    run_scan()
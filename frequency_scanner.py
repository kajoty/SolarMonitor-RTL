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
    f_start = float(os.getenv('SOLAR_FREQ_START', 26.0))
    f_end = float(os.getenv('SOLAR_FREQ_END', 80.0))
    gain_val = os.getenv('RTL_GAIN', '25.4')
    device_idx = int(os.getenv('RTL_DEVICE_INDEX', 0))
    
    logger.info(f"🚀 Scan gestartet: {f_start} - {f_end} MHz")

    try:
        rtl_power_path = shutil.which('rtl_power') or '/usr/bin/rtl_power'
        # Integrationszeit 1s für kompletten Sweep
        freq_range = f"{int(f_start * 1e6)}:{int(f_end * 1e6)}:100000,1s"
        
        cmd = [rtl_power_path, '-f', freq_range, '-g', str(gain_val), '-d', str(device_idx), '-1']
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if not result.stdout.strip():
            logger.error("❌ Keine Daten von rtl_power")
            return

        frequencies = []
        power_values = []
        
        # PARSING LOGIK für test_scan.csv Format
        for line in result.stdout.strip().split('\n'):
            parts = line.split(',')
            if len(parts) < 7: continue
            
            s_freq = float(parts[2])
            e_freq = float(parts[3])
            num_bins = int(parts[5])
            
            # Extrahiere genau num_bins Werte ab Spalte 6
            bin_powers = [float(x) for x in parts[6:6+num_bins]]
            
            # Erzeuge passgenaue Frequenzen für diesen Block
            freq_array = np.linspace(s_freq, e_freq, len(bin_powers), endpoint=False)
            
            frequencies.extend(freq_array / 1e6)
            power_values.extend(bin_powers)

        # Datenbank-Upload
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            database=os.getenv('POSTGRES_DB'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD')
        )
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        data_points = [
            (timestamp, "Solar Radio", float(f), float(p), 'rtl')
            for f, p in zip(frequencies, power_values)
        ]
        
        if data_points:
            execute_values(
                cursor,
                "INSERT INTO frequency_spectrum (timestamp, band_name, frequency, power, receiver) VALUES %s",
                data_points
            )
            conn.commit()
            logger.info(f"✅ {len(data_points)} Punkte in DB geschrieben (bis {max(frequencies):.2f} MHz)")
        
        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Fehler: {e}")

if __name__ == "__main__":
    run_scan()
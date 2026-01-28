import os
import time
import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = "recordings"
HOURS_TO_EXPORT = 3      
INTERVAL_SECONDS = 300 

db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}/{os.getenv('POSTGRES_DB')}"
engine = create_engine(db_url)

def generate_snapshot():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    try:
        # 1. Daten abfragen
        query = f"""
            SELECT timestamp, frequency, power, applied_gain 
            FROM frequency_spectrum 
            WHERE timestamp > NOW() - INTERVAL '{HOURS_TO_EXPORT} hours'
            AND band_name = 'Solar_Radio'
            ORDER BY timestamp ASC
        """
        df = pd.read_sql(query, engine)

        if df.empty:
            print(f"[{datetime.now()}] Keine Solar-Daten gefunden.")
            return

        # 2. Daten aufbereiten & Normalisieren
        df['normalized_power'] = df['power'] - df['applied_gain']
        df['frequency'] = df['frequency'].round(1)
        
        pivot_df = df.pivot_table(
            index='timestamp', 
            columns='frequency', 
            values='normalized_power', 
            aggfunc='mean'
        )

        # 3. Plot (Vertikal)
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 14))
        
        # Festgelegte Farbskala für konsistente Ergebnisse
        # vmin: Hintergrundrauschen (lila/blau)
        # vmax: Starke Signale (gelb)
        im = ax.imshow(
            pivot_df.values, 
            aspect='auto', 
            origin='lower',
            extent=[pivot_df.columns.min(), pivot_df.columns.max(), 0, len(pivot_df.index)],
            cmap='viridis',
            vmin=-90,  # Fixierter Mindestwert
            vmax=-30   # Fixierter Maximalwert
        )

        # Zeit-Achse (Y)
        num_ticks = 15
        indices = [int(i) for i in pd.Series(range(len(pivot_df.index))).iloc[::max(1, len(pivot_df.index)//num_ticks)]]
        ax.set_yticks(indices)
        ax.set_yticklabels([pivot_df.index[i].strftime('%H:%M') for i in indices])

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
        ax.set_title(f"Solar Vertical Waterfall (Fixed Scale) {timestamp_str}")
        ax.set_xlabel("Frequenz [MHz]")
        ax.set_ylabel("Zeit (Verlauf nach oben)")
        
        cbar = fig.colorbar(im)
        cbar.set_label('Normalized Power [dBn]')

        # 4. Speichern
        file_path = os.path.join(OUTPUT_DIR, f"heatmap_solar_vert_{timestamp_str}.png")
        plt.savefig(file_path, dpi=100, bbox_inches='tight')
        plt.close(fig) 
        
        print(f"[{datetime.now()}] Konsistente Heatmap erstellt: {file_path}")

    except Exception as e:
        print(f"[{datetime.now()}] Fehler: {e}")

if __name__ == "__main__":
    print(f"[{datetime.now()}] Heatmap-Service (Fixed Scale) gestartet...")
    while True:
        generate_snapshot()
        time.sleep(INTERVAL_SECONDS)
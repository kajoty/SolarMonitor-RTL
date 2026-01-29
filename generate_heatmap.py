import os
import time
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
from datetime import datetime
from dotenv import load_dotenv

# --- KONFIGURATION ---
load_dotenv()
OUTPUT_DIR = "recordings"
INTERVAL_SECONDS = 300 

# [cite_start]Port auf 5433 eingestellt [cite: 1]
db_port = os.getenv('POSTGRES_PORT', '5433') 
db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{db_port}/{os.getenv('POSTGRES_DB')}"
engine = create_engine(db_url)

def generate_dynamic_plots(hours=48):
    """Erzeugt den 48h Solar-Trend ohne FM-Nadeln."""
    try:
        query = f"""
            SELECT timestamp, power, applied_gain 
            FROM frequency_spectrum 
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
            AND band_name = 'Solar_Radio'
            ORDER BY timestamp ASC
        """
        df = pd.read_sql(query, engine)
        if df.empty: return

        df['normalized_power'] = df['power'] - df['applied_gain']
        
        plt.style.use('dark_background')
        fig, ax1 = plt.subplots(figsize=(15, 7))

        df['timestamp'] = df['timestamp'].dt.floor('min')
        s_stats = df.groupby('timestamp')['normalized_power'].agg(['min', 'max']).reset_index()
        
        # Filtert FM-Umschaltpausen (< -130 dBn)
        s_stats = s_stats[s_stats['min'] > -130] 
        s_stats = s_stats.set_index('timestamp').resample('1min').mean()
        s_stats = s_stats.interpolate(method='linear', limit=5).reset_index()
        
        ax1.fill_between(s_stats['timestamp'], s_stats['min'], s_stats['max'], color='#00FF00', alpha=0.15, label='Signal-Bereich')
        ax1.plot(s_stats['timestamp'], s_stats['max'], color='#FFD700', linewidth=1, label='Solar Max (Bursts)')
        ax1.plot(s_stats['timestamp'], s_stats['min'], color='#00BFFF', linewidth=1, label='Solar Min (Floor)')
        
        ax1.axhline(y=-30, color='red', linestyle='--', alpha=0.5, label='Alarm-Limit (-30)')
        
        ax1.set_title(f"Solar Radio Dynamik - Gereinigter {hours}h Verlauf")
        ax1.set_ylabel("Normalisierte Power [dBn]")
        ax1.legend(loc='upper right', ncol=2)
        ax1.grid(True, alpha=0.1)

        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "signal_solar_dynamic_48h.png"), dpi=120)
        plt.close(fig)
    except Exception as e:
        print(f"Fehler Dynamik-Plot: {e}")

def create_waterfall_image(hrs, filename):
    """Generiert eine Heatmap für ein spezifisches Zeitfenster."""
    try:
        query = f"""
            SELECT timestamp, frequency, power, applied_gain 
            FROM frequency_spectrum 
            WHERE timestamp > NOW() - INTERVAL '{hrs} hours'
            AND band_name = 'Solar_Radio'
            ORDER BY timestamp ASC
        """
        df = pd.read_sql(query, engine)
        if df.empty: return

        df['normalized_power'] = df['power'] - df['applied_gain']
        df['frequency'] = df['frequency'].round(1)
        
        # Auto-Scaling für optimalen Kontrast
        auto_vmin = np.percentile(df['normalized_power'], 10)
        auto_vmax = max(-30, df['normalized_power'].max())

        pivot_df = df.pivot_table(index='timestamp', columns='frequency', values='normalized_power', aggfunc='mean')

        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 14))
        
        im = ax.imshow(pivot_df.values, aspect='auto', origin='lower',
                       extent=[pivot_df.columns.min(), pivot_df.columns.max(), 0, len(pivot_df.index)],
                       cmap='viridis', vmin=auto_vmin, vmax=auto_vmax)

        num_ticks = 15
        indices = [int(i) for i in pd.Series(range(len(pivot_df.index))).iloc[::max(1, len(pivot_df.index)//num_ticks)]]
        ax.set_yticks(indices)
        ax.set_yticklabels([pivot_df.index[i].strftime('%H:%M') for i in indices])

        ax.set_title(f"Solar {hrs}h Waterfall")
        plt.savefig(os.path.join(OUTPUT_DIR, filename), dpi=100, bbox_inches='tight')
        plt.close(fig)
    except Exception as e:
        print(f"Fehler Waterfall ({hrs}h): {e}")

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    print(f"[{datetime.now()}] Solar-Only Service gestartet...")
    
    while True:
        # 1. Dynamik Plot (48h)
        generate_dynamic_plots(hours=48)
        
        # 2. Die drei benötigten Waterfall-Fenster für das Dashboard
        create_waterfall_image(1, "latest_1h_Solar.png")
        create_waterfall_image(6, "latest_6h_Solar.png")
        create_waterfall_image(24, "latest_24h_Solar.png")
        
        print(f"[{datetime.now()}] Dashboard-Bilder aktualisiert. Warte {INTERVAL_SECONDS}s...")
        time.sleep(INTERVAL_SECONDS)
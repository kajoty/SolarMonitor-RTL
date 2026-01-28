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

db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}/{os.getenv('POSTGRES_DB')}"
engine = create_engine(db_url)

def generate_dynamic_plots(hours=48):
    """Erzeugt ein sauberes 48h Dynamik-Diagramm nur für Solar-Daten."""
    try:
        # Abfrage nur für Solar_Radio über den Zeitraum X (48h)
        query = f"""
            SELECT timestamp, power, applied_gain 
            FROM frequency_spectrum 
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
            AND band_name = 'Solar_Radio'
            ORDER BY timestamp ASC
        """
        df = pd.read_sql(query, engine)
        if df.empty: return

        # Normalisierung (Power - Gain)
        df['normalized_power'] = df['power'] - df['applied_gain']
        
        plt.style.use('dark_background')
        fig, ax1 = plt.subplots(figsize=(15, 7))

        # --- SOLAR DATEN AUFBEREITUNG ---
        df['timestamp'] = df['timestamp'].dt.floor('min')
        s_stats = df.groupby('timestamp')['normalized_power'].agg(['min', 'max']).reset_index()
        
        # NADEL-KILLER: Filtert Dropouts während der FM-Scan-Pausen (< -130 dBn)
        s_stats = s_stats[s_stats['min'] > -130] 
        
        # Resampling und Interpolation füllt die Lücken der FM-Scans für eine glatte Linie
        s_stats = s_stats.set_index('timestamp').resample('1min').mean()
        s_stats = s_stats.interpolate(method='linear', limit=5).reset_index()
        
        # Plotting
        ax1.fill_between(s_stats['timestamp'], s_stats['min'], s_stats['max'], color='#00FF00', alpha=0.15, label='Signal-Bereich')
        ax1.plot(s_stats['timestamp'], s_stats['max'], color='#FFD700', linewidth=1, label='Solar Max (Bursts)')
        ax1.plot(s_stats['timestamp'], s_stats['min'], color='#00BFFF', linewidth=1, label='Solar Min (Floor)')
        
        # Referenzlinien
        current_min = s_stats['min'].min()
        ax1.axhline(y=-30, color='red', linestyle='--', alpha=0.5, label='Alarm-Limit (-30)')
        ax1.axhline(y=current_min, color='white', linestyle=':', alpha=0.3, label=f'Noise Floor ({current_min:.1f})')
        
        ax1.set_title(f"Solar Radio Dynamik (26-80 MHz) - Gereinigter {hours}h Verlauf")
        ax1.set_ylabel("Normalisierte Power [dBn]")
        ax1.set_xlabel("Zeit (Lokal)")
        ax1.legend(loc='upper right', ncol=2)
        ax1.grid(True, alpha=0.1)

        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "signal_solar_dynamic_48h.png"), dpi=120)
        plt.close(fig)
        print(f"[{datetime.now()}] 48h Solar-Plot aktualisiert.")

    except Exception as e:
        print(f"Fehler bei Dynamik-Plot: {e}")

def generate_waterfall():
    """Erstellt die Heatmap (3h) mit Auto-Scaling für optimalen Kontrast."""
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

    try:
        # 3-Stunden Export für den Waterfall
        query = """
            SELECT timestamp, frequency, power, applied_gain 
            FROM frequency_spectrum 
            WHERE timestamp > NOW() - INTERVAL '3 hours'
            AND band_name = 'Solar_Radio'
            ORDER BY timestamp ASC
        """
        df = pd.read_sql(query, engine)
        if df.empty: return

        df['normalized_power'] = df['power'] - df['applied_gain']
        df['frequency'] = df['frequency'].round(1)
        
        # AUTO-SCALING: 10. Perzentil als vmin für tiefen Noise-Floor
        auto_vmin = np.percentile(df['normalized_power'], 10)
        auto_vmax = max(-30, df['normalized_power'].max())

        pivot_df = df.pivot_table(index='timestamp', columns='frequency', values='normalized_power', aggfunc='mean')

        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 14))
        
        im = ax.imshow(
            pivot_df.values, aspect='auto', origin='lower',
            extent=[pivot_df.columns.min(), pivot_df.columns.max(), 0, len(pivot_df.index)],
            cmap='viridis', vmin=auto_vmin, vmax=auto_vmax
        )

        # Zeit-Achse
        num_ticks = 15
        indices = [int(i) for i in pd.Series(range(len(pivot_df.index))).iloc[::max(1, len(pivot_df.index)//num_ticks)]]
        ax.set_yticks(indices)
        ax.set_yticklabels([pivot_df.index[i].strftime('%H:%M') for i in indices])

        ax.set_title(f"Solar Waterfall (Auto-Scaled: {auto_vmin:.0f} to {auto_vmax:.0f} dBn)")
        ax.set_xlabel("Frequenz [MHz]")
        ax.set_ylabel("Zeit (Verlauf nach oben)")
        fig.colorbar(im, label='Rel. Power [dBn]')

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
        plt.savefig(os.path.join(OUTPUT_DIR, f"heatmap_solar_vert_{timestamp_str}.png"), dpi=100, bbox_inches='tight')
        plt.close(fig) 
        print(f"[{datetime.now()}] Waterfall erstellt.")

    except Exception as e:
        print(f"Fehler bei Heatmap: {e}")

if __name__ == "__main__":
    print(f"[{datetime.now()}] Monitoring gestartet (Waterfall & 48h Dynamik)...")
    while True:
        generate_waterfall()
        generate_dynamic_plots(hours=48)
        time.sleep(INTERVAL_SECONDS)
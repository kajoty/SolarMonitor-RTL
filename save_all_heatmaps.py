#!/usr/bin/env python3
"""
Skript zum Speichern aller verfügbaren 24h-Heatmaps für alle Frequenzbänder
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta
from heatmap_generator import FFTHeatmapGenerator
import base64
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_available_dates():
    """Hole alle verfügbaren Daten mit Spektrum-Daten"""
    conn = sqlite3.connect('spectrum.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT DATE(timestamp) as date
        FROM frequency_spectrum
        ORDER BY date
    """)
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    return dates

def save_all_24h_heatmaps():
    """Speichere 24h-Heatmaps für alle verfügbaren Tage und Bänder"""
    # Initialisiere Heatmap-Generator
    heatmap_gen = FFTHeatmapGenerator()

    # Hole verfügbare Tage
    dates = get_available_dates()
    if not dates:
        logger.warning("Keine Daten in der Datenbank gefunden")
        return

    # Hole verfügbare Bänder aus der Datenbank (nur tatsächlich gescannte Bänder)
    conn = sqlite3.connect('spectrum.db')
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT band_name FROM frequency_spectrum')
    db_bands = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Definiere Frequenzbereiche für bekannte Bänder
    band_definitions = {
        'Solar Radio': {'start': 24, 'end': 80},
    }
    
    # Erstelle Band-Liste nur für tatsächlich vorhandene Daten
    bands = []
    for band_name in db_bands:
        if band_name in band_definitions:
            bands.append({
                'name': band_name,
                'start': band_definitions[band_name]['start'],
                'end': band_definitions[band_name]['end']
            })
    
    logger.info(f'Generiere Heatmaps für {len(bands)} tatsächlich gescannte Bänder: {[b["name"] for b in bands]}')

    total_saved = 0

    for date_str in dates:
        logger.info(f"Verarbeite Datum: {date_str}")

        # Erstelle Verzeichnis
        heatmap_dir = 'heatmaps'
        if not os.path.exists(heatmap_dir):
            os.makedirs(heatmap_dir)

        date_dir = os.path.join(heatmap_dir, date_str)
        if not os.path.exists(date_dir):
            os.makedirs(date_dir)

        # Zeitraum für den ganzen Tag
        start_time = f"{date_str}T00:00:00"
        end_time = f"{date_str}T23:59:59"

        for band in bands:
            try:
                # Generiere Heatmap für dieses Band
                heatmap_base64 = heatmap_gen.get_heatmap_data(
                    start_time=start_time,
                    end_time=end_time,
                    freq_start=band['start'],
                    freq_end=band['end'],
                    title=f"24h FFT Spektrum Heatmap - {band['name']} - {date_str}",
                    cmap='viridis'
                )

                if heatmap_base64:
                    # Speichere als PNG
                    filename = f"{band['name'].replace(' ', '_').lower()}_24h_heatmap.png"
                    filepath = os.path.join(date_dir, filename)

                    image_data = base64.b64decode(heatmap_base64)
                    with open(filepath, 'wb') as f:
                        f.write(image_data)

                    # Speichere Metadaten
                    metadata = {
                        'date': date_str,
                        'band_name': band['name'],
                        'freq_start': band['start'],
                        'freq_end': band['end'],
                        'start_time': start_time,
                        'end_time': end_time,
                        'cmap': 'viridis',
                        'generated_at': datetime.now().isoformat(),
                        'filepath': filepath
                    }

                    metadata_file = os.path.join(date_dir, f"{band['name'].replace(' ', '_').lower()}_metadata.json")
                    with open(metadata_file, 'w') as f:
                        json.dump(metadata, f, indent=2)

                    logger.info(f"✅ Gespeichert: {filepath}")
                    total_saved += 1
                else:
                    logger.warning(f"❌ Konnte keine Heatmap für {band['name']} am {date_str} generieren")

            except Exception as e:
                logger.error(f"Fehler bei {band['name']} am {date_str}: {e}")

    logger.info(f"📊 Insgesamt {total_saved} Heatmaps gespeichert")

if __name__ == '__main__':
    save_all_24h_heatmaps()
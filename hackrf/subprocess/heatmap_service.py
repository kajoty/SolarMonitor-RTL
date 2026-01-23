#!/usr/bin/env python3
"""
Standalone Heatmap Generator Service
=====================================
Läuft auf einem leistungsstarken Rechner und generiert Heatmaps
aus der PostgreSQL-Datenbank auf 192.168.178.100:5432.

REST API:
  POST /generate - Generiert Heatmap mit Parametern
  GET  /status   - Service-Status

Beispiel:
  curl -X POST http://localhost:8888/generate \
    -H "Content-Type: application/json" \
    -d '{"band":"Solar Radio","hours":24,"colormap":"YlOrRd"}'
"""

import os
import sys
import io
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import psycopg2
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('heatmap_service.log')
    ]
)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)
CORS(app)

# PostgreSQL-Verbindungsdetails
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', '192.168.178.100'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'solarmonitor'),
    'user': os.getenv('POSTGRES_USER', 'admin'),
    'password': os.getenv('POSTGRES_PASSWORD', 'admin')
}

class HeatmapGenerator:
    """Generiert Frequenz-Zeit-Heatmaps aus PostgreSQL-Daten"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        logger.info(f"HeatmapGenerator initialisiert mit DB: {db_config['host']}:{db_config['port']}")
    
    def get_connection(self):
        """Erstellt PostgreSQL-Verbindung"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"Datenbankverbindung fehlgeschlagen: {e}")
            raise
    
    def fetch_data(self, band_name: str, hours: int = 24, receiver: Optional[str] = None) -> tuple:
        """
        Holt Spektraldaten aus PostgreSQL
        
        Args:
            band_name: Band-Name (z.B. "Solar Radio")
            hours: Zeitbereich in Stunden
            receiver: Optional filter ('rtl', 'hackrf', None=alle)
        
        Returns:
            (timestamps, frequencies, power_matrix)
        """
        logger.info(f"Lade Daten: band={band_name}, hours={hours}, receiver={receiver}")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Zeit-Filter
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Query mit optionalem Receiver-Filter
        sql = """
            SELECT 
                timestamp::TIMESTAMP as time,
                frequency,
                power
            FROM frequency_spectrum
            WHERE band_name = %s
              AND timestamp >= %s
              AND timestamp <= %s
        """
        params = [band_name, start_time.isoformat(), end_time.isoformat()]
        
        if receiver:
            sql += " AND receiver = %s"
            params.append(receiver)
        
        sql += " ORDER BY timestamp ASC, frequency ASC"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        if not rows:
            logger.warning("Keine Daten gefunden")
            return None, None, None
        
        logger.info(f"Geladene Datensätze: {len(rows)}")
        
        # Parse Daten
        timestamps = []
        frequencies = []
        powers = []
        
        for time_str, freq, power in rows:
            # Parse timestamp (kann String oder datetime sein)
            if isinstance(time_str, str):
                ts = datetime.fromisoformat(time_str)
            else:
                ts = time_str
            
            timestamps.append(ts)
            frequencies.append(freq)
            powers.append(power)
        
        # Gruppiere in 2D-Matrix (Zeit x Frequenz)
        unique_times = sorted(set(timestamps))
        unique_freqs = sorted(set(frequencies))
        
        logger.info(f"Zeit-Intervalle: {len(unique_times)}, Frequenzen: {len(unique_freqs)}")
        
        # Matrix erstellen
        power_matrix = np.full((len(unique_times), len(unique_freqs)), np.nan)
        
        for i, ts in enumerate(timestamps):
            time_idx = unique_times.index(ts)
            freq_idx = unique_freqs.index(frequencies[i])
            power_matrix[time_idx, freq_idx] = powers[i]
        
        return unique_times, unique_freqs, power_matrix
    
    def generate_heatmap(
        self,
        band_name: str,
        hours: int = 24,
        colormap: str = 'YlOrRd',
        receiver: Optional[str] = None,
        width: int = 16,
        height: int = 10,
        dpi: int = 100
    ) -> bytes:
        """
        Generiert Heatmap als PNG
        
        Args:
            band_name: Band-Name
            hours: Zeitbereich in Stunden
            colormap: Matplotlib colormap (YlOrRd, viridis, plasma, etc.)
            receiver: Optional filter
            width: Breite in Inches
            height: Höhe in Inches
            dpi: Auflösung
        
        Returns:
            PNG-Bilddaten (bytes)
        """
        logger.info(f"Generiere Heatmap: {band_name}, {hours}h, {colormap}")
        
        # Daten laden
        times, freqs, matrix = self.fetch_data(band_name, hours, receiver)
        
        if times is None:
            raise ValueError("Keine Daten verfügbar")
        
        # Plot erstellen
        fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
        
        # Heatmap plotten
        im = ax.imshow(
            matrix.T,  # Transpose: Frequenz auf Y-Achse
            aspect='auto',
            cmap=colormap,
            interpolation='nearest',
            origin='lower'
        )
        
        # Achsenbeschriftungen
        ax.set_xlabel('Zeit', fontsize=12)
        ax.set_ylabel('Frequenz (MHz)', fontsize=12)
        ax.set_title(f'{band_name} - Letzten {hours}h', fontsize=14, fontweight='bold')
        
        # Zeit-Ticks
        num_time_ticks = min(10, len(times))
        time_tick_indices = np.linspace(0, len(times) - 1, num_time_ticks, dtype=int)
        time_tick_labels = [times[i].strftime('%H:%M') for i in time_tick_indices]
        ax.set_xticks(time_tick_indices)
        ax.set_xticklabels(time_tick_labels, rotation=45, ha='right')
        
        # Frequenz-Ticks
        num_freq_ticks = min(10, len(freqs))
        freq_tick_indices = np.linspace(0, len(freqs) - 1, num_freq_ticks, dtype=int)
        freq_tick_labels = [f'{freqs[i]:.1f}' for i in freq_tick_indices]
        ax.set_yticks(freq_tick_indices)
        ax.set_yticklabels(freq_tick_labels)
        
        # Colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Power (dB)', rotation=270, labelpad=20)
        
        plt.tight_layout()
        
        # Als PNG speichern
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        logger.info("Heatmap erfolgreich generiert")
        return buf.read()


# Globale Instanz
generator = HeatmapGenerator(DB_CONFIG)


@app.route('/status', methods=['GET'])
def status():
    """Service-Status"""
    try:
        conn = generator.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM frequency_spectrum")
        count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'database': 'connected',
            'records': count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Status-Check fehlgeschlagen: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/generate', methods=['POST'])
def generate():
    """
    Generiert Heatmap
    
    POST-Payload:
    {
        "band": "Solar Radio",
        "hours": 24,
        "colormap": "YlOrRd",
        "receiver": "rtl",  // optional
        "format": "png",     // oder "base64"
        "width": 16,
        "height": 10,
        "dpi": 100
    }
    """
    try:
        data = request.get_json() or {}
        
        # Parameter extrahieren
        band = data.get('band', 'Solar Radio')
        hours = data.get('hours', 24)
        colormap = data.get('colormap', 'YlOrRd')
        receiver = data.get('receiver')
        output_format = data.get('format', 'png')
        width = data.get('width', 16)
        height = data.get('height', 10)
        dpi = data.get('dpi', 100)
        
        logger.info(f"Heatmap-Anfrage: {band}, {hours}h, {colormap}, {output_format}")
        
        # Heatmap generieren
        image_bytes = generator.generate_heatmap(
            band_name=band,
            hours=hours,
            colormap=colormap,
            receiver=receiver,
            width=width,
            height=height,
            dpi=dpi
        )
        
        # Ausgabeformat
        if output_format == 'base64':
            # Base64-Encoding
            encoded = base64.b64encode(image_bytes).decode('utf-8')
            return jsonify({
                'status': 'success',
                'format': 'base64',
                'image': encoded,
                'size_bytes': len(image_bytes)
            })
        else:
            # PNG direkt zurückgeben
            return send_file(
                io.BytesIO(image_bytes),
                mimetype='image/png',
                as_attachment=False,
                download_name=f'heatmap_{band.replace(" ", "_")}_{hours}h.png'
            )
    
    except Exception as e:
        logger.error(f"Heatmap-Generierung fehlgeschlagen: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("Heatmap Generator Service gestartet")
    logger.info(f"PostgreSQL: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    logger.info("Endpoints:")
    logger.info("  GET  /status   - Service-Status")
    logger.info("  POST /generate - Heatmap generieren")
    logger.info("=" * 80)
    
    # Server starten
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8888)),
        debug=False,
        threaded=True
    )

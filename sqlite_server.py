#!/usr/bin/env python3
"""
SQLite REST Server für SolarMonitor-RTL
Läuft auf Port 8002 und bietet REST API für Spektraldaten
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
import logging
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

DB_PATH = "/data/spectrum.db" if os.path.exists("/data") else "./spectrum.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Initialisiere Datenbank-Schema"""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    
    # Aktiviere WAL-Mode für gleichzeitige Lese-/Schreibzugriffe
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB Cache
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS frequency_spectrum (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            band_name TEXT NOT NULL,
            frequency REAL NOT NULL,
            power REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Erstelle Indizes für schnelle Abfragen
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp_band 
        ON frequency_spectrum(timestamp, band_name)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_band_name 
        ON frequency_spectrum(band_name)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp 
        ON frequency_spectrum(timestamp)
    """)
    
    conn.commit()
    conn.close()
    logger.info(f"✅ SQLite DB initialisiert: {DB_PATH} (WAL-Mode aktiv)")

@app.route('/health', methods=['GET'])
def health():
    """Health Check"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute("SELECT 1")
        conn.close()
        return jsonify({"status": "healthy", "db": DB_PATH}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/api/write', methods=['POST'])
def write_data():
    """
    Schreibe Spektraldaten
    
    Erwartet JSON:
    {
        "timestamp": "2025-11-17T20:39:07Z",
        "band_name": "Solar Radio",
        "data": [
            {"frequency": 20.0, "power": -45.3},
            {"frequency": 20.12, "power": -43.1},
            ...
        ]
    }
    """
    try:
        payload = request.get_json()
        timestamp = payload['timestamp']
        band_name = payload['band_name']
        data = payload['data']
        
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        
        inserted_count = 0
        for point in data:
            freq = float(point['frequency'])
            power = float(point['power'])
            
            # Überspringe NaN
            if freq == freq and power == power:  # NaN check
                cursor.execute(
                    "INSERT INTO frequency_spectrum (timestamp, band_name, frequency, power) VALUES (?, ?, ?, ?)",
                    (timestamp, band_name, freq, power)
                )
                inserted_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ {inserted_count} Punkte geschrieben")
        return jsonify({
            "status": "success",
            "inserted": inserted_count,
            "timestamp": datetime.now().isoformat()
        }), 201
        
    except Exception as e:
        logger.error(f"Fehler beim Schreiben: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/read', methods=['GET'])
def read_data():
    """
    Lese Spektraldaten
    
    Parameter:
    - band_name: Band-Name (erforderlich)
    - time_range: '1h', '6h', '24h', '7d', '30d' (Standard: '24h') ODER
    - start_time: ISO-8601 Timestamp (z.B. '2025-11-17T00:00:00')
    - end_time: ISO-8601 Timestamp (optional, default: jetzt)
    
    Rückgabe:
    {
        "timestamps": ["2025-11-17T20:00:00Z", ...],
        "frequencies": [20.0, 20.12, ...],
        "data": [[power_values...], ...]
    }
    """
    try:
        band_name = request.args.get('band_name')
        time_range = request.args.get('time_range', None)
        start_time = request.args.get('start_time', None)
        end_time = request.args.get('end_time', None)
        
        if not band_name:
            return jsonify({"error": "band_name required"}), 400
        
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        
        # Bestimme WHERE-Klausel für Zeit
        if start_time and end_time:
            # Absolute Zeitstempel verwenden
            query = """
                SELECT timestamp, frequency, power 
                FROM frequency_spectrum 
                WHERE band_name = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp DESC, frequency ASC
            """
            rows = cursor.execute(query, (band_name, start_time, end_time)).fetchall()
            logger.info(f"Query: {band_name} zwischen {start_time} und {end_time}")
        elif time_range:
            # time_range verwenden
            time_map = {
                '1h': 3600,
                '6h': 6*3600,
                '24h': 24*3600,
                '7d': 7*24*3600,
                '30d': 30*24*3600
            }
            
            if time_range not in time_map:
                return jsonify({"error": f"Invalid time_range: {time_range}"}), 400
            
            cutoff_seconds = time_map[time_range]
            
            query = """
                SELECT timestamp, frequency, power 
                FROM frequency_spectrum 
                WHERE band_name = ? AND datetime(timestamp) > datetime('now', '-' || ? || ' seconds')
                ORDER BY timestamp DESC, frequency ASC
            """
            rows = cursor.execute(query, (band_name, cutoff_seconds)).fetchall()
            logger.info(f"Query: {band_name} time_range={time_range}")
        else:
            # Default: 24h
            cutoff_seconds = 24*3600
            query = """
                SELECT timestamp, frequency, power 
                FROM frequency_spectrum 
                WHERE band_name = ? AND datetime(timestamp) > datetime('now', '-' || ? || ' seconds')
                ORDER BY timestamp DESC, frequency ASC
            """
            rows = cursor.execute(query, (band_name, cutoff_seconds)).fetchall()
            logger.info(f"Query: {band_name} (default 24h)")
        
        conn.close()
        
        if not rows:
            return jsonify({
                "status": "no_data",
                "band_name": band_name,
                "time_range": time_range,
                "timestamps": [],
                "frequencies": [],
                "data": []
            }), 200
        
        # Organisiere Daten
        timestamps_list = []
        frequencies_list = []
        data_dict = {}
        
        for timestamp, freq, power in rows:
            if timestamp not in data_dict:
                timestamps_list.append(timestamp)
                data_dict[timestamp] = {}
            
            if freq not in frequencies_list:
                frequencies_list.append(freq)
            
            data_dict[timestamp][freq] = power
        
        timestamps_list.sort(reverse=True)
        frequencies_list.sort()
        
        # Baue 2D Array
        data_2d = []
        for ts in timestamps_list:
            row = []
            for freq in frequencies_list:
                row.append(data_dict[ts].get(freq, None))
            data_2d.append(row)
        
        return jsonify({
            "status": "success",
            "band_name": band_name,
            "time_range": time_range,
            "timestamps": timestamps_list,
            "frequencies": frequencies_list,
            "data": data_2d,
            "rows": len(timestamps_list),
            "columns": len(frequencies_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Fehler beim Lesen: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def stats():
    """Statistiken über gespeicherte Daten"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM frequency_spectrum")
        total_count = cursor.fetchone()[0]
        
        # Bands
        cursor.execute("SELECT DISTINCT band_name FROM frequency_spectrum ORDER BY band_name")
        bands = [row[0] for row in cursor.fetchall()]
        
        # Latest timestamp
        cursor.execute("SELECT MAX(timestamp) FROM frequency_spectrum")
        latest = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "total_points": total_count,
            "bands": bands,
            "latest_timestamp": latest
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete', methods=['POST'])
def delete_data():
    """Lösche alte Daten"""
    try:
        days = request.json.get('days', 7)
        
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM frequency_spectrum WHERE datetime(timestamp) < datetime('now', '-' || ? || ' days')",
            (days,)
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"🧹 {deleted} alte Einträge gelöscht (älter als {days} Tage)")
        return jsonify({"status": "success", "deleted": deleted}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    init_db()
    logger.info("🚀 SQLite REST Server läuft auf Port 8002")
    app.run(host='0.0.0.0', port=8002, debug=False, threaded=True)

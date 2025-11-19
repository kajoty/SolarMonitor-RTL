"""
SQLite database wrapper (deprecated - kept for reference only).
The system now uses direct REST API calls to sqlite_server.py.
This module is not actively used.
"""

import sqlite3
import logging
import requests
import json
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)

class SQLiteDB:
    """Verbindung zu SQLite-Datenbank über HTTP REST API auf Docker Container"""
    
    def __init__(self, host: str = "192.168.178.100", port: int = 8001):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.db_path = "spectrum_data.db"
        logger.info(f"SQLiteDB initialisiert: {self.base_url}")
        self._init_schema()
    
    def _init_schema(self):
        """Erstelle Tabellen wenn nicht vorhanden"""
        sql = """
        CREATE TABLE IF NOT EXISTS frequency_spectrum (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            band_name TEXT NOT NULL,
            frequency REAL NOT NULL,
            power REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_timestamp_band ON frequency_spectrum(timestamp, band_name);
        CREATE INDEX IF NOT EXISTS idx_band_name ON frequency_spectrum(band_name);
        CREATE INDEX IF NOT EXISTS idx_timestamp ON frequency_spectrum(timestamp);
        """
        
        try:
            # Starte lokale SQLite-Verbindung
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for statement in sql.split(';'):
                if statement.strip():
                    cursor.execute(statement)
            conn.commit()
            conn.close()
            logger.info("✅ SQLite Schema initialisiert")
        except Exception as e:
            logger.error(f"Fehler beim Initialisieren des Schemas: {e}")
    
    def write_spectrum_data(self, band_name: str, frequencies: np.ndarray, 
                           power_values: np.ndarray, timestamp: str) -> bool:
        """
        Schreibe Spektraldaten in SQLite
        
        Args:
            band_name: Name des Frequenzbandes (z.B. "Solar Radio")
            frequencies: Array von Frequenzen in MHz
            power_values: Array von Power-Werten in dB
            timestamp: ISO-Format Timestamp (z.B. "2025-11-17T20:39:07Z")
        
        Returns:
            True wenn erfolgreich
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            data_to_insert = []
            for freq, power in zip(frequencies, power_values):
                # Überspringe NaN-Werte
                if not (np.isnan(float(freq)) or np.isnan(float(power))):
                    data_to_insert.append((
                        timestamp,
                        band_name,
                        float(freq),
                        float(power)
                    ))
            
            if data_to_insert:
                cursor.executemany(
                    "INSERT INTO frequency_spectrum (timestamp, band_name, frequency, power) VALUES (?, ?, ?, ?)",
                    data_to_insert
                )
                conn.commit()
                logger.info(f"✅ {len(data_to_insert)} Spektrum-Punkte in SQLite geschrieben")
                conn.close()
                return True
            else:
                conn.close()
                logger.warning("Keine gültigen Datenpunkte zum Schreiben")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Schreiben in SQLite: {e}")
            return False
    
    def get_spectrum_data(self, band_name: str, time_range: str = "1h") -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Lädt Spektraldaten aus SQLite
        
        Args:
            band_name: Band-Name zum Filtern
            time_range: Zeitraum ('1h', '6h', '24h', '7d', '30d')
        
        Returns:
            Tuple(spektrum_data, timestamps, frequencies)
        """
        try:
            # Parse time_range
            time_map = {
                '1h': 1/24, '6h': 6/24, '24h': 1, 
                '7d': 7, '30d': 30
            }
            
            if time_range not in time_map:
                logger.error(f"Ungültiger Zeitraum: {time_range}")
                return np.array([]), np.array([]), np.array([])
            
            hours_back = time_map[time_range] * 24
            cutoff_time = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Hole alle Daten im Zeitraum für das Band
            cursor.execute("""
                SELECT timestamp, frequency, power 
                FROM frequency_spectrum 
                WHERE band_name = ? AND timestamp > ?
                ORDER BY timestamp DESC, frequency ASC
            """, (band_name, cutoff_time))
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                logger.warning(f"Keine Daten für Band '{band_name}' im Zeitraum {time_range}")
                return np.array([]), np.array([]), np.array([])
            
            # Organisiere Daten: {(timestamp, freq) -> power}
            data_dict = {}
            timestamps_set = set()
            frequencies_set = set()
            
            for timestamp, freq, power in rows:
                timestamps_set.add(timestamp)
                frequencies_set.add(freq)
                data_dict[(timestamp, freq)] = power
            
            timestamps = sorted(list(timestamps_set))
            frequencies = sorted(list(frequencies_set))
            
            logger.info(f"Loaded: {len(timestamps)} Timestamps, {len(frequencies)} Frequencies")
            
            # Baue 2D Array (Zeit x Frequenz)
            spektrum_data = np.zeros((len(timestamps), len(frequencies)))
            spektrum_data[:] = np.nan
            
            for (ts, freq), power in data_dict.items():
                t_idx = timestamps.index(ts)
                f_idx = frequencies.index(freq)
                spektrum_data[t_idx, f_idx] = power
            
            return spektrum_data, np.array(timestamps), np.array(frequencies)
            
        except Exception as e:
            logger.error(f"Fehler beim Lesen aus SQLite: {e}")
            return np.array([]), np.array([]), np.array([])
    
    def cleanup_old_data(self, days: int = 7):
        """Lösche Daten älter als N Tage"""
        try:
            cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM frequency_spectrum WHERE timestamp < ?", (cutoff_time,))
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            logger.info(f"🧹 {deleted} alte Einträge gelöscht")
        except Exception as e:
            logger.error(f"Fehler beim Löschen alter Daten: {e}")


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = SQLiteDB()
    
    # Test Write
    test_freqs = np.linspace(20, 80, 500)
    test_powers = np.random.normal(-40, 5, 500)
    db.write_spectrum_data("Solar Radio", test_freqs, test_powers, datetime.utcnow().isoformat() + "Z")
    
    # Test Read
    data, ts, freqs = db.get_spectrum_data("Solar Radio", "1h")
    print(f"✅ Data shape: {data.shape}, Timestamps: {len(ts)}, Frequencies: {len(freqs)}")

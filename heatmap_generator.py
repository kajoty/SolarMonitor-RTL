"""
FFT Heatmap Generator für RTL-SDR Frequenzspektrum-Daten
Generiert Heatmaps aus InfluxDB-Daten für verschiedene Zeiträume
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import LogNorm
from datetime import datetime, timedelta
from influxdb import InfluxDBClient
import os
import io
import base64
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class FFTHeatmapGenerator:
    """Generiert FFT Heatmaps aus Frequenzspektrum-Daten"""
    
    # Zeitraum-Presets (in Minuten)
    TIME_RANGES = {
        '1h': 60,
        '6h': 360,
        '24h': 1440,
        '7d': 10080,
        '30d': 43200,
    }
    
    def __init__(self, influxdb_host: str, influxdb_port: int, 
                 influxdb_user: str, influxdb_password: str, 
                 influxdb_database: str):
        """
        Initialisiert den Heatmap-Generator mit InfluxDB Verbindung
        
        Args:
            influxdb_host: Hostname des InfluxDB Servers
            influxdb_port: Port des InfluxDB Servers
            influxdb_user: Benutzername
            influxdb_password: Passwort
            influxdb_database: Datenbankname
        """
        self.influxdb_host = influxdb_host
        self.influxdb_port = influxdb_port
        self.influxdb_user = influxdb_user
        self.influxdb_password = influxdb_password
        self.influxdb_database = influxdb_database
        self.client = None
        
        try:
            self._connect()
        except Exception as e:
            logger.warning(f"InfluxDB Verbindung fehlgeschlagen: {e}")
    
    def _connect(self):
        """Verbindung zu InfluxDB herstellen"""
        self.client = InfluxDBClient(
            host=self.influxdb_host,
            port=self.influxdb_port,
            username=self.influxdb_user,
            password=self.influxdb_password,
            database=self.influxdb_database
        )
    
    def get_frequency_data(self, time_range: str = '24h', 
                          freq_start: Optional[float] = None,
                          freq_end: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Lädt Frequenzspektrum-Daten aus InfluxDB
        
        Args:
            time_range: Zeitraum ('1h', '6h', '24h', '7d', '30d')
            freq_start: Startfrequenz in MHz (optional)
            freq_end: Endfrequenz in MHz (optional)
            
        Returns:
            Tuple mit (spektrum_data, zeitstempel, frequenzen)
            - spektrum_data: 2D Array (Zeit x Frequenz)
            - zeitstempel: Array mit Zeitstempeln
            - frequenzen: Array mit Frequenzen in MHz
        """
        if not self.client:
            raise RuntimeError("InfluxDB ist nicht verbunden")
        
        if time_range not in self.TIME_RANGES:
            raise ValueError(f"Ungültiger Zeitraum. Erlaubt: {list(self.TIME_RANGES.keys())}")
        
        minutes = self.TIME_RANGES[time_range]
        time_str = f"{minutes}m"
        
        # Query: Lese Frequenz und Leistung aus dem Zeitfenster
        query = f"""
            SELECT "frequency", "power" 
            FROM "frequency_spectrum" 
            WHERE time > now() - {time_str}
            ORDER BY time ASC
        """
        
        if freq_start is not None and freq_end is not None:
            query = f"""
                SELECT "frequency", "power" 
                FROM "frequency_spectrum" 
                WHERE time > now() - {time_str}
                  AND "frequency" >= {freq_start}
                  AND "frequency" <= {freq_end}
                ORDER BY time ASC
            """
        
        try:
            result = self.client.query(query)
            
            if not result:
                logger.warning(f"Keine Daten für Zeitraum {time_range} gefunden")
                return np.array([]), np.array([]), np.array([])
            
            # Konvertiere InfluxDB-Ergebnisse in Arrays
            spektrum_data, timestamps, frequencies = self._parse_influxdb_result(result)
            
            return spektrum_data, timestamps, frequencies
            
        except Exception as e:
            logger.error(f"Fehler beim Laden von InfluxDB-Daten: {e}")
            return np.array([]), np.array([]), np.array([])
    
    def _parse_influxdb_result(self, result) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Parse InfluxDB Query-Ergebnisse in strukturierte Arrays
        
        Returns:
            Tuple mit (spektrum_data, timestamps, frequencies)
        """
        data_dict = {}
        timestamps_set = set()
        frequencies_set = set()
        
        try:
            # result ist ein ResultSet, iterieren gibt Listen von Dicts zurück
            for points_list in result:
                # points_list ist eine Liste von Dictionary-Objekten
                for point in points_list:
                    try:
                        timestamp = point.get('time')
                        frequency_str = point.get('frequency')
                        power = point.get('power')
                        
                        if timestamp and frequency_str is not None and power is not None:
                            freq_float = float(frequency_str)  # frequency kommt als String von InfluxDB
                            power_float = float(power)
                            
                            timestamps_set.add(timestamp)
                            frequencies_set.add(freq_float)
                            
                            key = (timestamp, freq_float)
                            data_dict[key] = power_float
                    except (KeyError, TypeError, ValueError) as e:
                        logger.debug(f"Fehler beim Parsen eines Punktes: {e}")
                        continue
            
            if not data_dict:
                logger.warning(f"Keine Datenpunkte nach Parsing gefunden")
                return np.array([]), np.array([]), np.array([])
        
        except Exception as e:
            logger.error(f"Fehler beim Parsing der InfluxDB-Ergebnisse: {e}", exc_info=True)
            return np.array([]), np.array([]), np.array([])
        
        # Sortiere Arrays
        timestamps = sorted(list(timestamps_set))
        frequencies = sorted(list(frequencies_set))
        
        if not timestamps or not frequencies:
            return np.array([]), np.array([]), np.array([])
        
        # Erstelle 2D-Array (Zeit x Frequenz)
        spektrum_data = np.zeros((len(timestamps), len(frequencies)))
        
        for i, ts in enumerate(timestamps):
            for j, freq in enumerate(frequencies):
                spektrum_data[i, j] = data_dict.get((ts, freq), np.nan)
        
        return spektrum_data, timestamps, np.array(frequencies)
    
    def generate_heatmap(self, spektrum_data: np.ndarray, 
                        timestamps: List[str],
                        frequencies: np.ndarray,
                        title: str = "FFT Spektrum Heatmap",
                        cmap: str = 'viridis',
                        figsize: Tuple[int, int] = (14, 6)) -> io.BytesIO:
        """
        Generiert eine Heatmap-Grafik
        
        Args:
            spektrum_data: 2D Array mit Spektraldaten
            timestamps: Liste mit Zeitstempeln
            frequencies: Array mit Frequenzen
            title: Titel der Grafik
            cmap: Colormap (z.B. 'viridis', 'jet', 'plasma')
            figsize: Größe der Grafik
            
        Returns:
            BytesIO Objekt mit PNG-Bild
        """
        if spektrum_data.size == 0:
            logger.warning("Leere Spektraldaten - kann Heatmap nicht generieren")
            return None
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Normalisiere Daten (entferne NaN-Werte)
        data_clean = np.nan_to_num(spektrum_data, nan=0)
        
        # Konvertiere negative dB-Werte zu positiv für LogNorm
        # Power in dB: P_dB = 10*log10(P_linear), negativ bedeutet schwach
        # Verschiebe um Minimum: P_shifted = P_dB - min(P_dB)
        if np.any(data_clean != 0):
            data_min = np.min(data_clean[data_clean != 0])
            if data_min < 0:
                data_clean = data_clean - data_min + 1  # Verschiebe, damit alle > 0
        
        # Verwende logarithmische Skala
        vmin = np.percentile(data_clean[data_clean > 0], 5) if np.any(data_clean > 0) else 1e-6
        vmax = np.percentile(data_clean[data_clean > 0], 95) if np.any(data_clean > 0) else 1
        vmin = max(vmin, 1e-6)  # Verhindere log(0)
        
        # Erstelle Heatmap mit linearer statt logarithmischer Skala für dB-Werte
        im = ax.imshow(data_clean.T, aspect='auto', origin='lower',
                       cmap=cmap, vmin=vmin, vmax=vmax,
                       extent=[0, len(timestamps), frequencies[0], frequencies[-1]])
        
        # Achsenbeschriftungen
        ax.set_ylabel('Frequenz (MHz)')
        ax.set_xlabel('Zeit')
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # Zeitachsen-Formatierung
        if len(timestamps) > 0:
            step = max(1, len(timestamps) // 10)
            ax.set_xticks(np.arange(0, len(timestamps), step))
            ax.set_xticklabels([timestamps[i] for i in range(0, len(timestamps), step)], 
                               rotation=45, ha='right', fontsize=9)
        
        # Colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Leistung (dB)', rotation=270, labelpad=20)
        
        plt.tight_layout()
        
        # Speichere als PNG in BytesIO
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    def generate_heatmap_base64(self, spektrum_data: np.ndarray,
                               timestamps: List[str],
                               frequencies: np.ndarray,
                               title: str = "FFT Spektrum Heatmap",
                               cmap: str = 'viridis') -> Optional[str]:
        """
        Generiert eine Heatmap und gibt sie als Base64-String zurück
        
        Ideal für die Einbettung in HTML
        """
        buf = self.generate_heatmap(spektrum_data, timestamps, frequencies, title, cmap)
        
        if buf is None:
            return None
        
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    
    def get_heatmap_data(self, time_range: str = '24h',
                        freq_start: Optional[float] = None,
                        freq_end: Optional[float] = None,
                        title: str = "FFT Spektrum Heatmap",
                        cmap: str = 'viridis') -> Optional[str]:
        """
        All-in-One Methode: Lädt Daten und generiert Heatmap
        
        Args:
            time_range: Zeitraum
            freq_start: Startfrequenz
            freq_end: Endfrequenz
            title: Grafik-Titel
            cmap: Colormap
            
        Returns:
            Base64-kodierte PNG oder None bei Fehler
        """
        try:
            spektrum_data, timestamps, frequencies = self.get_frequency_data(
                time_range, freq_start, freq_end
            )
            
            if spektrum_data.size == 0:
                logger.warning(f"Keine Daten verfügbar für Heatmap-Generierung")
                return None
            
            return self.generate_heatmap_base64(
                spektrum_data, timestamps, frequencies, title, cmap
            )
        except Exception as e:
            logger.error(f"Fehler bei Heatmap-Generierung: {e}")
            return None


def create_heatmap_generator_from_env() -> FFTHeatmapGenerator:
    """
    Erstellt einen HeatmapGenerator aus Umgebungsvariablen
    """
    from dotenv import load_dotenv
    
    load_dotenv()
    
    return FFTHeatmapGenerator(
        influxdb_host=os.getenv('INFLUXDB_HOST', 'localhost'),
        influxdb_port=int(os.getenv('INFLUXDB_PORT', 8086)),
        influxdb_user=os.getenv('INFLUXDB_USER', 'admin'),
        influxdb_password=os.getenv('INFLUXDB_PASSWORD', 'admin'),
        influxdb_database=os.getenv('INFLUXDB_DATABASE', 'rtl_monitor')
    )

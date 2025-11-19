"""
FFT Heatmap Generator für RTL-SDR Frequenzspektrum-Daten
Generiert Heatmaps aus SQLite-Daten (via REST API) für verschiedene Zeiträume
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import os
import io
import base64
import requests
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class FFTHeatmapGenerator:
    """Generiert FFT Heatmaps aus Frequenzspektrum-Daten (SQLite via REST API)"""
    
    # Zeitraum-Presets
    TIME_RANGES = {
        '1h': '1h',
        '6h': '6h',
        '24h': '24h',
        '7d': '7d',
        '30d': '30d',
    }
    
    def __init__(self, sqlite_rest_url: str = "http://localhost:8002"):
        """
        Initialisiert den Heatmap-Generator mit SQLite REST API Verbindung
        
        Args:
            sqlite_rest_url: URL des SQLite REST API Servers (default: http://localhost:8002)
        """
        self.sqlite_rest_url = sqlite_rest_url
        self.timeout = 30  # Timeout für API-Anfragen
        
        # Test Verbindung
        try:
            response = requests.get(f"{self.sqlite_rest_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ SQLite REST API erreichbar unter {self.sqlite_rest_url}")
            else:
                logger.warning(f"⚠️ SQLite REST API antwortet mit Status {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ SQLite REST API nicht erreichbar: {e}")
    
    def get_frequency_data(self, time_range: str = '24h', 
                          band_name: str = None,
                          freq_start: Optional[float] = None,
                          freq_end: Optional[float] = None,
                          start_time: str = None,
                          end_time: str = None,
                          exclude_last_scans: int = 2) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Lädt Frequenzspektrum-Daten aus SQLite via REST API
        
        Args:
            time_range: Zeitraum ('1h', '6h', '24h', '7d', '30d') ODER None wenn start_time verwendet
            band_name: Band-Name zum Filtern (z.B. 'Solar Radio')
            freq_start: Startfrequenz in MHz (optional)
            freq_end: Endfrequenz in MHz (optional)
            start_time: ISO-8601 Start-Timestamp (optional, überschreibt time_range)
            end_time: ISO-8601 End-Timestamp (optional)
            exclude_last_scans: Anzahl der neuesten Scans auszuschließen (default: 2)
            
        Returns:
            Tuple mit (spektrum_data, zeitstempel, frequenzen)
            - spektrum_data: 2D Array (Zeit x Frequenz)
            - zeitstempel: Array mit Zeitstempeln
            - frequenzen: Array mit Frequenzen in MHz
        """
        # Validierung nur wenn kein start_time
        if not start_time and time_range not in self.TIME_RANGES:
            raise ValueError(f"Ungültiger Zeitraum. Erlaubt: {list(self.TIME_RANGES.keys())}")
        
        # Bereite Band-Namen vor (sauber ohne Klammern)
        band_name_clean = None
        if band_name:
            band_name_clean = band_name.split('(')[0].strip()
        
        try:
            # Rufe SQLite REST API auf
            params = {
                'band_name': band_name_clean,
            }
            
            # Verwende start_time/end_time wenn vorhanden, sonst time_range
            if start_time and end_time:
                params['start_time'] = start_time
                params['end_time'] = end_time
                logger.info(f"SQLite Query: time_range={start_time} bis {end_time}, band_name={band_name_clean}")
            else:
                params['time_range'] = time_range
                logger.info(f"SQLite Query: time_range={time_range}, band_name={band_name_clean}")
            
            response = requests.get(
                f"{self.sqlite_rest_url}/api/read",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('status') != 'success' and result.get('status') != 'no_data':
                logger.error(f"SQLite REST API Fehler: {result.get('error', 'unbekannt')}")
                return np.array([]), np.array([]), np.array([])
            
            # Parse die Antwort
            spektrum_data, timestamps, frequencies = self._parse_sqlite_response(
                result, 
                freq_start=freq_start,
                freq_end=freq_end,
                exclude_last_scans=exclude_last_scans
            )
            
            logger.info(f"✅ Geladen: {len(timestamps)} Scans, {len(frequencies)} Frequenzen, {np.sum(~np.isnan(spektrum_data))} gültige Punkte")
            
            return spektrum_data, timestamps, frequencies
            
        except requests.exceptions.RequestException as e:
            logger.error(f"SQLite REST API Fehler: {e}")
            return np.array([]), np.array([]), np.array([])
        except Exception as e:
            logger.error(f"Fehler beim Laden der SQLite-Daten: {e}", exc_info=True)
            return np.array([]), np.array([]), np.array([])
    
    def _parse_sqlite_response(self, response_data: dict,
                              freq_start: Optional[float] = None,
                              freq_end: Optional[float] = None,
                              exclude_last_scans: int = 2) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Parse SQLite REST API Response in strukturierte Arrays
        
        Response Format:
        {
            "status": "success",
            "timestamps": ["2025-11-17T20:00:00Z", ...],
            "frequencies": [20.0, 20.12, ..., 80.0],
            "data": [[power_values_scan1], [power_values_scan2], ...],
            "rows": N,
            "columns": M
        }
        
        Returns:
            Tuple mit (spektrum_data, timestamps, frequencies)
        """
        try:
            timestamps = response_data.get('timestamps', [])
            frequencies = np.array(response_data.get('frequencies', []), dtype=float)
            data_2d = response_data.get('data', [])
            
            if not timestamps or len(frequencies) == 0 or len(data_2d) == 0:
                logger.warning("SQLite Response ist leer")
                return np.array([]), np.array([]), np.array([])
            
            # Konvertiere data zu numpy array
            spektrum_data = np.array(data_2d, dtype=float)
            
            # Shape sollte sein: (N_timestamps, N_frequencies)
            if spektrum_data.shape[0] != len(timestamps):
                logger.warning(f"Shape-Mismatch: {spektrum_data.shape[0]} != {len(timestamps)}")
                # Versuche zu transponieren wenn nötig
                if spektrum_data.shape[1] == len(timestamps):
                    spektrum_data = spektrum_data.T
            
            # Filtere nach Frequenzbereich wenn angegeben
            if freq_start is not None or freq_end is not None:
                f_start = freq_start if freq_start is not None else frequencies[0]
                f_end = freq_end if freq_end is not None else frequencies[-1]
                
                freq_mask = (frequencies >= f_start) & (frequencies <= f_end)
                frequencies = frequencies[freq_mask]
                spektrum_data = spektrum_data[:, freq_mask]
            
            # Schließe letzte N Scans aus (sind oft unvollständig)
            if exclude_last_scans > 0 and len(timestamps) > exclude_last_scans:
                spektrum_data = spektrum_data[:-exclude_last_scans, :]
                timestamps = timestamps[:-exclude_last_scans]
            
            logger.info(f"Parsed SQLite: {spektrum_data.shape} Array, {len(timestamps)} Timestamps, {len(frequencies)} Frequenzen")
            
            return spektrum_data, timestamps, frequencies
            
        except Exception as e:
            logger.error(f"Fehler beim Parsing der SQLite-Response: {e}", exc_info=True)
            return np.array([]), np.array([]), np.array([])
    
    def generate_heatmap(self, spektrum_data: np.ndarray, 
                        timestamps: List[str],
                        frequencies: np.ndarray,
                        title: str = "FFT Spektrum Heatmap",
                        cmap: str = 'viridis',
                        figsize: Tuple[int, int] = None,
                        freq_min: Optional[float] = None,
                        freq_max: Optional[float] = None) -> io.BytesIO:
        """
        Generiert eine Heatmap-Grafik
        
        Args:
            spektrum_data: 2D Array mit Spektraldaten (time x frequency)
            timestamps: Liste mit Zeitstempeln
            frequencies: Array mit Frequenzen
            title: Titel der Grafik
            cmap: Colormap (z.B. 'viridis', 'jet', 'plasma')
            figsize: Größe der Grafik (default: auto basierend auf Scan-Anzahl)
                    Wird automatisch berechnet: (16, 0.35*n_scans + 2) inches
            
        Returns:
            BytesIO Objekt mit PNG-Bild
        """
        if spektrum_data.size == 0:
            logger.warning("Leere Spektraldaten - kann Heatmap nicht generieren")
            return None
        
        # AUTO-SCALING: Höhe basierend auf Anzahl der Scans berechnen
        # Kompaktere Höhe: 0.15 Zoll pro Scan (kompakter), minimum 5 Zoll, maximum 18 Zoll
        if figsize is None:
            n_scans = len(timestamps)
            # Zielformel: 0.15 Zoll pro Scan (deutlich kompakter als vorher)
            # Minimum 5 Zoll für lesbare kleine Heatmaps
            # Maximum 18 Zoll um Memory-Probleme zu vermeiden
            target_height = min(18, max(5, 0.15 * n_scans + 1.5))
            figsize = (16, target_height)
            
            # Wenn wir zu viele Scans haben, warne den User
            if n_scans > 100:
                logger.warning(f"⚠️ Viele Scans ({n_scans}) - Heatmap ist {target_height:.1f} Zoll hoch. "
                              f"Erwägen Sie, den time_range zu reduzieren oder exclude_last_scans zu erhöhen.")
            
            logger.info(f"Auto-Figsize für {n_scans} Scans: ({figsize[0]}, {figsize[1]:.1f}) inches (~{int(figsize[1]*100)}px @ 100dpi)")
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Normalisiere Daten (entferne NaN-Werte)
        data_clean = np.nan_to_num(spektrum_data, nan=-100)  # NaN → -100 dB (sehr niedrig)
        
        # Für dB-Werte: verwende robuste Normalisierung
        data_valid = data_clean[np.isfinite(data_clean) & (data_clean > -200)]
        
        if len(data_valid) > 0:
            vmin = np.percentile(data_valid, 5)
            vmax = np.percentile(data_valid, 95)
            if vmin >= vmax:
                vmin = np.min(data_valid)
                vmax = np.max(data_valid)
        else:
            vmin = -100
            vmax = -50
        
        # Kehre Datenreihenfolge um, damit Zeit von alt (links) zu neu (rechts) läuft
        # Timestamps kommen reversed (neueste zuerst), also flippen
        data_clean = np.flipud(data_clean)  # Flip rows (Zeit)
        timestamps = timestamps[::-1]  # Reverse timestamps list
        
        # Transponiere data: Von (Zeit x Frequenz) zu (Frequenz x Zeit)
        # Das ermöglicht: X-Achse = Zeit (links→rechts), Y-Achse = Frequenz (unten→oben)
        data_transposed = data_clean.T  # Shape wird zu (N_frequencies, N_timestamps)
        
        # Frequenz-Grenzen
        freq_min_val = freq_min if freq_min is not None else frequencies[0]
        freq_max_val = freq_max if freq_max is not None else frequencies[-1]
        time_min_idx = 0
        time_max_idx = len(timestamps) - 1
        
        # Erstelle Heatmap mit transponierter Daten
        # Data shape: (N_frequencies, N_timestamps)
        # X-Achse = Zeit (0 bis N_timestamps, alt→neu von links→rechts)
        # Y-Achse = Frequenz (freq_min bis freq_max)
        im = ax.imshow(data_transposed, aspect='auto', origin='lower',
                       cmap=cmap, vmin=vmin, vmax=vmax,
                       extent=[time_min_idx, time_max_idx, freq_min_val, freq_max_val],
                       interpolation='nearest')
        
        # Achsenbeschriftungen
        ax.set_ylabel('Frequenz (MHz)', fontsize=11)
        ax.set_xlabel('Zeit', fontsize=11)
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # X-Achse (Zeit) formatieren
        if len(timestamps) > 0:
            # Bestimme Anzahl der Ticks basierend auf Anzahl der Zeitpunkte
            num_ticks = min(10, max(3, len(timestamps)))
            if len(timestamps) > 20:
                # Für viele Zeitpunkte: reduziere Anzahl
                step = max(1, len(timestamps) // 8)
                tick_indices = list(range(0, len(timestamps), step))
                if len(timestamps) - 1 not in tick_indices:
                    tick_indices.append(len(timestamps) - 1)
            else:
                # Für wenige Zeitpunkte: zeige alle
                tick_indices = list(range(len(timestamps)))
            
            # Set X ticks (Zeit)
            ax.set_xticks(tick_indices)
            
            formatted_times = []
            for i in tick_indices:
                if i < len(timestamps):
                    # Timestamps sind jetzt in korrekter Reihenfolge (alt→neu)
                    time_str = timestamps[i]
                    try:
                        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        # Formatiere Zeit basierend auf Zeitspanne
                        if len(timestamps) > 50:
                            formatted_times.append(dt.strftime('%m-%d %H:%M'))
                        else:
                            formatted_times.append(dt.strftime('%H:%M:%S'))
                    except:
                        formatted_times.append(time_str[:10])
            
            ax.set_xticklabels(formatted_times, fontsize=9, rotation=45, ha='right')
        
        # Y-Achse (Frequenz) formatieren
        freq_ticks = np.linspace(freq_min_val, freq_max_val, 7)
        ax.set_yticks(freq_ticks)
        ax.set_yticklabels([f'{f:.1f}' for f in freq_ticks], fontsize=9)
        
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
                               cmap: str = 'viridis',
                               freq_min: Optional[float] = None,
                               freq_max: Optional[float] = None) -> Optional[str]:
        """
        Generiert eine Heatmap und gibt sie als Base64-String zurück
        
        Ideal für die Einbettung in HTML
        """
        buf = self.generate_heatmap(spektrum_data, timestamps, frequencies, title, cmap, 
                                   freq_min=freq_min, freq_max=freq_max)
        
        if buf is None:
            return None
        
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    
    def get_heatmap_data(self, time_range: str = '24h',
                        band_name: str = None,
                        freq_start: Optional[float] = None,
                        freq_end: Optional[float] = None,
                        start_time: str = None,
                        end_time: str = None,
                        title: str = "FFT Spektrum Heatmap",
                        cmap: str = 'viridis',
                        exclude_last_scans: int = 2) -> Optional[str]:
        """
        All-in-One Methode: Lädt Daten und generiert Heatmap
        
        Args:
            time_range: Zeitraum zum Anzeigen (z.B. '24h') ODER None wenn start_time verwendet
            band_name: Band-Name zum Filtern
            freq_start: Startfrequenz
            freq_end: Endfrequenz
            start_time: ISO-8601 Start-Timestamp (optional, überschreibt time_range)
            end_time: ISO-8601 End-Timestamp (optional)
            title: Grafik-Titel
            cmap: Colormap
            exclude_last_scans: Anzahl der neuesten Scans auszuschließen (default: 2)
            
        Returns:
            Base64-kodierte PNG oder None bei Fehler
        """
        try:
            spektrum_data, timestamps, frequencies = self.get_frequency_data(
                time_range, band_name, freq_start, freq_end, 
                start_time=start_time, end_time=end_time,
                exclude_last_scans=exclude_last_scans
            )
            
            if spektrum_data.size == 0:
                logger.warning(f"Keine Daten verfügbar für Heatmap-Generierung")
                return None
            
            return self.generate_heatmap_base64(
                spektrum_data, timestamps, frequencies, title, cmap,
                freq_min=freq_start, freq_max=freq_end
            )
        except Exception as e:
            logger.error(f"Fehler bei Heatmap-Generierung: {e}")
            return None


def create_heatmap_generator_from_env() -> FFTHeatmapGenerator:
    """
    Erstellt einen HeatmapGenerator aus Umgebungsvariablen
    """
    sqlite_rest_url = os.getenv('SQLITE_REST_URL', 'http://localhost:8002')
    return FFTHeatmapGenerator(sqlite_rest_url=sqlite_rest_url)

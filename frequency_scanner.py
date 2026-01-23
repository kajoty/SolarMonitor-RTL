"""
RTL-SDR Frequenzbereich-Scanner und Analyzer
Ermittelt verfügbare und aktive Frequenzbereiche auf dem RTL2838 USB Dongle
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class FrequencyBand:
    """Repräsentiert einen Frequenzbereich"""
    name: str
    freq_start: float  # MHz
    freq_end: float    # MHz
    description: str = ""
    
    def __post_init__(self):
        """Validiere Frequenzbereich"""
        if self.freq_start >= self.freq_end:
            raise ValueError(f"freq_start ({self.freq_start}) muss kleiner als freq_end ({self.freq_end}) sein")
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dictionary für JSON Serialisierung"""
        return {
            'name': self.name,
            'freq_start': self.freq_start,
            'freq_end': self.freq_end,
            'description': self.description
        }


@dataclass
class ScanResult:
    """Ergebnis einer Frequenzbereich-Analyse"""
    band: FrequencyBand
    avg_power: float           # Durchschnittliche Leistung in dB
    peak_power: float          # Maximale Leistung in dB
    noise_floor: float         # Rauschboden
    signal_to_noise: float     # Signal-to-Noise Ratio in dB
    active: bool               # Ob Aktivität erkannt wurde
    activity_percentage: float # % der Zeit mit Signal über Rauschboden
    num_peaks: int             # Anzahl erkannter Signalpeaks
    scan_time: float           # Scan-Dauer in Sekunden
    timestamp: str = None
    frequencies: Optional[np.ndarray] = None  # Array der Frequenzen in MHz (für Heatmap)
    power_values: Optional[np.ndarray] = None  # Array der Power-Werte in dB (für Heatmap)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dictionary für JSON Serialisierung"""
        return {
            'band': {
                'name': self.band.name,
                'freq_start': self.band.freq_start,
                'freq_end': self.band.freq_end,
                'description': self.band.description
            },
            'avg_power': round(float(self.avg_power), 2),
            'peak_power': round(float(self.peak_power), 2),
            'noise_floor': round(float(self.noise_floor), 2),
            'signal_to_noise': round(float(self.signal_to_noise), 2),
            'active': bool(self.active),
            'activity_percentage': round(float(self.activity_percentage), 1),
            'num_peaks': int(self.num_peaks),
            'scan_time': round(float(self.scan_time), 2),
            'timestamp': self.timestamp
        }


class RTLSDRScanner:
    """Scannt Frequenzbereiche mit RTL-SDR Hardware"""
    
    # Solar Radio Astronomy - Meterwellen für Type II/III Solar Bursts
    # RTL2838 Tuner Frequenzbereich: 24-1766 MHz (praktisch: 26-1500 MHz stabil)
    COMMON_BANDS = [
        # Index 0 - Radio Jove / Meterwellen (26-80 MHz) - RTL-SDR kann nicht unter 26 MHz
        FrequencyBand("Solar Radio", 26.0, 80.0, "Type II/III Solar Bursts & Radioastronomie"),
    ]
    
    def __init__(self, rtl_device_index: int = 0, sample_rate: int = 2000000, 
                 gain: str = 'auto', ppm_correction: int = 0, use_mock: bool = False):
        """
        Initialisiert RTL-SDR Scanner
        
        Args:
            rtl_device_index: Index des RTL-SDR Geräts (0 = erstes)
            sample_rate: Sample-Rate in Hz (Standard: 2 MSps für RTL2838)
            gain: 'auto' oder fester Wert in dB (z.B. '20.7', '25.4')
                  Typische Werte für RTL2838: 0-49.6 dB in 0.1er Schritten
            ppm_correction: Frequenz-Kalibrierung in ppm (Parts Per Million)
                           Korrigiert Quarz-Oszillator Drift (-50 bis +50 ppm typisch)
            use_mock: Verwende Mock-Daten statt echter Hardware (für Entwicklung)
        """
        self.rtl_device_index = rtl_device_index
        self.sample_rate = sample_rate
        self.gain = gain
        self.ppm_correction = ppm_correction
        self.device = None
        self.is_connected = False
        self.use_mock = use_mock
        
        if use_mock:
            logger.info("Starte im Mock-Modus (kein RTL-SDR Hardware erforderlich)")
            self.is_connected = False  # Mark as "not really connected" but usable
            return
        
        try:
            self._init_device()
        except Exception as e:
            logger.warning(f"RTL-SDR Gerät nicht verbunden: {e}")
            self.is_connected = False
    
    def _init_device(self):
        """Initialisiere RTL-SDR Gerät"""
        try:
            import rtlsdr
            self.device = rtlsdr.RtlSdr(device_index=self.rtl_device_index)
            self.device.sample_rate = self.sample_rate
            
            # Konvertiere Gain zu float wenn nicht 'auto'
            if self.gain != 'auto':
                try:
                    self.device.gain = float(self.gain)
                except ValueError:
                    logger.warning(f"Ungültige Gain-Wert '{self.gain}', verwende 'auto'")
                    self.device.gain = 'auto'
            else:
                self.device.gain = 'auto'
            
            # Setze PPM-Correction wenn vorhanden
            if self.ppm_correction != 0:
                try:
                    self.device.freq_correction = self.ppm_correction
                    logger.info(f"Frequenz-Kalibrierung: {self.ppm_correction} ppm")
                except Exception as e:
                    logger.warning(f"Konnte PPM-Korrektur nicht setzen: {e}")
            
            self.is_connected = True
            
            # Log Gain-Konfiguration
            if self.gain == 'auto':
                logger.info(f"RTL-SDR Gerät {self.rtl_device_index} verbunden (Auto Gain, PPM: {self.ppm_correction})")
            else:
                logger.info(f"RTL-SDR Gerät {self.rtl_device_index} verbunden (Gain: {self.gain} dB, PPM: {self.ppm_correction})")
        except ImportError:
            logger.error("rtl-sdr Modul nicht verfügbar. Installieren Sie: pip install rtl-sdr")
            raise
        except Exception as e:
            logger.error(f"Fehler beim Verbinden mit RTL-SDR: {e}")
            raise
    
    def _ensure_connected(self):
        """Stelle Verbindung sicher (Lazy Initialization)"""
        if self.is_connected:
            return True
        
        if self.use_mock:
            return False
        
        try:
            self._init_device()
            return True
        except Exception as e:
            logger.warning(f"Konnte nicht mit RTL-SDR verbinden: {e}")
            return False
    
    def scan_band(self, band: FrequencyBand, num_samples: int = 256) -> Optional[ScanResult]:
        """
        Scanne einen Frequenzbereich mit rtl_power CLI Tool (zuverlässiger als pyrtlsdr)
        
        Args:
            band: FrequencyBand zum Scannen
            num_samples: wird ignoriert (rtl_power nutzt interne Einstellung)
            
        Returns:
            ScanResult mit Analyse oder None bei Fehler
        """
        import subprocess
        import tempfile
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Starte Scan für {band.name} ({band.freq_start}-{band.freq_end} MHz) mit rtl_power")
            
            # rtl_power Kommando:
            # -f start:stop:step - Frequenzbereich (MHz)
            # -g gain - Gain (default auto)
            # -p ppm - PPM Korrektur
            # -d device_index
            # -1 - Single measurement (schnell)
            freq_range = f"{int(band.freq_start * 1e6)}:{int(band.freq_end * 1e6)}:100000"  # 100 kHz steps
            
            cmd = [
                'rtl_power',
                '-f', freq_range,
                '-g', str(self.gain if self.gain != 'auto' else 0),  # rtl_power nutzt auto nicht
                '-p', str(self.ppm_correction),
                '-d', str(self.rtl_device_index),
                '-1'  # Single measurement
            ]
            
            # Führe rtl_power aus und parse Output
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.warning(f"rtl_power Fehler: {result.stderr}")
                return None
            
            # Parse rtl_power Output (CSV Format)
            frequencies = []
            power_values = []
            
            for line in result.stdout.strip().split('\n'):
                if not line or line.startswith('#'):
                    continue
                parts = line.split(',')
                if len(parts) >= 2:
                    try:
                        freq_hz = float(parts[0])
                        power_db = float(parts[1])
                        frequencies.append(freq_hz / 1e6)  # Konvertiere zu MHz
                        power_values.append(power_db)
                    except ValueError:
                        continue
            
            if not power_values:
                logger.warning(f"Keine Daten von rtl_power für {band.name}")
                return None
            
            frequencies = np.array(frequencies)
            power_values = np.array(power_values)
            
            scan_duration = (datetime.now() - start_time).total_seconds()
            
            # Berechne Metriken
            avg_power = float(np.mean(power_values))
            peak_power = float(np.max(power_values))
            noise_floor = float(np.percentile(power_values, 10))
            signal_to_noise = peak_power - noise_floor
            
            # Erkenne Peaks (Signal über Rauschboden + 6dB)
            threshold = noise_floor + 6
            peaks = np.sum(power_values > threshold)
            activity_percentage = (peaks / len(power_values)) * 100
            
            # Bestimme ob Band aktiv ist
            active = signal_to_noise > 5  # > 5dB SNR = aktiv
            
            logger.info(f"✅ Scan abgeschlossen: {band.name}, SNR={signal_to_noise:.1f}dB, Aktivität={activity_percentage:.1f}%")
            
            return ScanResult(
                band=band,
                avg_power=avg_power,
                peak_power=peak_power,
                noise_floor=noise_floor,
                signal_to_noise=signal_to_noise,
                active=active,
                activity_percentage=activity_percentage,
                num_peaks=int(peaks),
                scan_time=scan_duration,
                frequencies=frequencies,
                power_values=power_values
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"rtl_power Timeout für {band.name}")
            return None
        except Exception as e:
            logger.error(f"Scan-Fehler für {band.name}: {e}")
            return None
            active = activity_percentage > 5  # >5% als "aktiv" definiert
            
            result = ScanResult(
                band=band,
                avg_power=avg_power,
                peak_power=peak_power,
                noise_floor=noise_floor,
                signal_to_noise=signal_to_noise,
                active=active,
                activity_percentage=activity_percentage,
                num_peaks=int(peaks),
                scan_time=scan_duration,
                frequencies=frequencies,  # Speichere die Frequenzen
                power_values=power_values  # Speichere die Power-Werte
            )
            
            logger.info(f"Scan abgeschlossen: {band.name} - Aktiv: {active}, S/N: {signal_to_noise:.1f} dB")
            return result
        
        except Exception as e:
            logger.error(f"Fehler beim Scannen von {band.name}: {e}", exc_info=True)
            return None
    
    def scan_all_bands(self, bands: Optional[List[FrequencyBand]] = None) -> List[ScanResult]:
        """
        Scanne alle Standard-Frequenzbereiche
        
        Args:
            bands: Liste der zu scannenden Bänder (Standard: COMMON_BANDS)
            
        Returns:
            Liste von ScanResult
        """
        if bands is None:
            bands = self.COMMON_BANDS
        
        results = []
        for band in bands:
            result = self.scan_band(band)
            if result:
                results.append(result)
        
        return results
    
    def find_active_bands(self, bands: Optional[List[FrequencyBand]] = None,
                         threshold_snr: float = 5.0) -> List[ScanResult]:
        """
        Finde aktive Frequenzbereiche
        
        Args:
            bands: Bänder zum Scannen
            threshold_snr: Signal-to-Noise Minimum für "aktiv"
            
        Returns:
            Sortierte Liste aktiver Bänder
        """
        results = self.scan_all_bands(bands)
        
        # Filtere nach SNR
        active_results = [r for r in results if r.signal_to_noise >= threshold_snr]
        
        # Sortiere absteigend nach SNR
        active_results.sort(key=lambda x: x.signal_to_noise, reverse=True)
        
        return active_results
    
    def close(self):
        """Trenne RTL-SDR Verbindung"""
        if self.device:
            try:
                self.device.close()
                logger.info("RTL-SDR Verbindung geschlossen")
            except Exception as e:
                logger.error(f"Fehler beim Schließen: {e}")


class FrequencyAnalyzer:
    """Analysiert Scan-Ergebnisse und gibt Empfehlungen"""
    
    @staticmethod
    def recommend_bands(results: List[ScanResult], 
                       min_snr: float = 3.0,
                       max_interference: float = 50.0) -> Dict:
        """
        Analysiere Scan-Ergebnisse und empfehle beste Bänder
        
        Args:
            results: Liste von ScanResults
            min_snr: Minimum SNR für Empfehlung
            max_interference: Maximum Aktivität% für "saubere" Bänder
            
        Returns:
            Dictionary mit Analyse und Empfehlungen
        """
        if not results:
            return {
                'status': 'error',
                'message': 'Keine Scan-Ergebnisse verfügbar',
                'recommendations': []
            }
        
        # Kategorisiere Bänder
        strong_signals = [r for r in results if r.signal_to_noise >= min_snr]
        clean_bands = [r for r in results if r.activity_percentage <= max_interference]
        active_bands = [r for r in results if r.active]
        
        # Sortiere nach SNR
        strong_signals.sort(key=lambda x: x.signal_to_noise, reverse=True)
        
        recommendations = []
        
        # Top 3 aktive Bänder mit guter Qualität
        top_active = [r for r in strong_signals if r.active][:3]
        for rank, result in enumerate(top_active, 1):
            recommendations.append({
                'rank': rank,
                'type': 'STRONG_SIGNAL',
                'band': result.band.to_dict() if hasattr(result.band, 'to_dict') else {
                    'name': result.band.name,
                    'freq_start': result.band.freq_start,
                    'freq_end': result.band.freq_end
                },
                'reason': f"Starkes Signal mit SNR {result.signal_to_noise:.1f} dB",
                'metrics': {
                    'snr': round(result.signal_to_noise, 2),
                    'activity': round(result.activity_percentage, 1),
                    'peak_power': round(result.peak_power, 2)
                }
            })
        
        # Saubere, relativ stille Bänder (für neue Implementierungen)
        quiet_bands = [r for r in clean_bands if r.signal_to_noise < min_snr][:2]
        for rank, result in enumerate(quiet_bands, 1):
            recommendations.append({
                'rank': rank + 100,
                'type': 'QUIET_BAND',
                'band': result.band.to_dict() if hasattr(result.band, 'to_dict') else {
                    'name': result.band.name,
                    'freq_start': result.band.freq_start,
                    'freq_end': result.band.freq_end
                },
                'reason': f"Relativ ruhig für Test-Setup (SNR {result.signal_to_noise:.1f} dB)",
                'metrics': {
                    'snr': round(result.signal_to_noise, 2),
                    'activity': round(result.activity_percentage, 1)
                }
            })
        
        return {
            'status': 'success',
            'total_scanned': len(results),
            'active_bands_found': len(active_bands),
            'strong_signals': len(strong_signals),
            'summary': {
                'max_snr': round(max([r.signal_to_noise for r in results]), 2),
                'avg_activity': round(np.mean([r.activity_percentage for r in results]), 1),
                'quietest_band': min(results, key=lambda x: x.avg_power).band.name if results else None
            },
            'recommendations': recommendations
        }


def create_scanner_from_env() -> RTLSDRScanner:
    """Erstelle Scanner aus Umgebungsvariablen"""
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    device_idx = int(os.getenv('RTL_DEVICE_INDEX', 0))
    sample_rate = int(os.getenv('RTL_SAMPLE_RATE', 2000000))
    gain = os.getenv('RTL_GAIN', 'auto')  # 'auto' oder fester Wert wie '25.4'
    ppm_correction = int(os.getenv('RTL_PPM_CORRECTION', 0))  # PPM-Offset für Frequenzkalibrierung
    
    return RTLSDRScanner(device_idx, sample_rate, gain, ppm_correction)


if __name__ == "__main__":
    """Haupt-Ausführung: Scanne überwachte Bänder und schreibe zu PostgreSQL"""
    import os
    import sys
    import subprocess
    from dotenv import load_dotenv
    import psycopg2
    from psycopg2.extras import execute_values
    
    # Konfiguration
    load_dotenv()
    
    # Logging Setup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚀 RTL-SDR Scanner mit rtl_power CLI gestartet")
    
    # Band-Konfiguration - hardcodiert (26-80 MHz)
    band = FrequencyBand("Solar Radio", 26.0, 80.0, "Type II/III Solar Bursts & Radioastronomie")
    
    logger.info(f"📡 Scanne Band: {band.name} ({band.freq_start}-{band.freq_end} MHz)")
    
    # Scan mit rtl_power durchführen (ohne pyrtlsdr zu initialisieren!)
    try:
        from datetime import datetime
        import shutil
        
        start_time = datetime.now()
        
        # Finde rtl_power im PATH
        rtl_power_path = shutil.which('rtl_power') or '/usr/bin/rtl_power'
        
        freq_range = f"{int(band.freq_start * 1e6)}:{int(band.freq_end * 1e6)}:100000"
        gain_val = os.getenv('RTL_GAIN', '25.4')
        ppm_val = int(os.getenv('RTL_PPM_CORRECTION', 0))
        device_idx = int(os.getenv('RTL_DEVICE_INDEX', 0))
        
        cmd = [
            rtl_power_path,
            '-f', freq_range,
            '-g', str(gain_val if gain_val != 'auto' else 0),
            '-p', str(ppm_val),
            '-d', str(device_idx),
            '-1'
        ]
        
        logger.info(f"Führe aus: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # rtl_power gibt Diagnose in stderr aber Daten in stdout
        if not result.stdout.strip():
            logger.error(f"❌ Keine Daten von rtl_power (stdout leer)")
            sys.exit(1)
        
        # Parse rtl_power Output (CSV: date, time, start_freq, stop_freq, step, samples, [power_values...])
        frequencies = []
        power_values = []
        
        for line in result.stdout.strip().split('\n'):
            if not line or line.startswith('#'):
                continue
            
            parts = line.split(',')
            if len(parts) < 7:  # date, time, start, stop, step, samples, min_power...
                continue
            
            try:
                start_freq = float(parts[2])  # Start frequency in Hz
                stop_freq = float(parts[3])   # Stop frequency in Hz
                step = float(parts[4])        # Frequency step size
                num_bins = int(parts[5])      # Number of FFT bins
                
                # Power values start at index 6
                bin_powers = [float(x) for x in parts[6:6+num_bins]]
                
                # Generate frequency array for this measurement
                freq_array = np.linspace(start_freq, stop_freq, num_bins, endpoint=False)
                
                frequencies.extend(freq_array / 1e6)  # Convert Hz to MHz
                power_values.extend(bin_powers)
            except (ValueError, IndexError):
                continue
        
        if not power_values:
            logger.error("❌ Keine Daten von rtl_power")
            sys.exit(1)
        
        frequencies = np.array(frequencies)
        power_values = np.array(power_values)
        scan_duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ {len(power_values)} Datenpunkte von rtl_power")
        
        # Daten in PostgreSQL schreiben
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', '192.168.178.100'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'solarmonitor'),
            user=os.getenv('POSTGRES_USER', 'admin'),
            password=os.getenv('POSTGRES_PASSWORD', 'admin')
        )
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        band_name_clean = band.name.split('(')[0].strip()
        
        data_points = [
            (timestamp, band_name_clean, float(freq), float(power), 'rtl')
            for freq, power in zip(frequencies, power_values)
            if not np.isnan(power) and not np.isinf(power)
        ]
        
        if data_points:
            logger.info(f"Schreibe {len(data_points)} Datenpunkte in PostgreSQL...")
            execute_values(
                cursor,
                "INSERT INTO frequency_spectrum (timestamp, band_name, frequency, power, receiver) VALUES %s",
                data_points,
                page_size=1000
            )
            conn.commit()
            logger.info(f"✅ {len(data_points)} Punkte erfolgreich geschrieben")
        else:
            logger.warning("⚠️ Keine gültigen Datenpunkte")
        
        cursor.close()
        conn.close()
        logger.info(f"✅ Scan abgeschlossen! (Dauer: {scan_duration:.2f}s)")
        
    except Exception as e:
        logger.error(f"❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

"""
RTL-SDR Frequenzbereich-Scanner und Analyzer
Ermittelt verfügbare und aktive Frequenzbereiche auf dem RTL2838 USB Dongle
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
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
    
    # Häufig benutzte Frequenzbereiche optimiert für RTL2838 DVB-T Stick
    # RTL2838 Tuner Frequenzbereich: 24-1766 MHz (praktisch: 50-1500 MHz)
    # Index basiert auf .env MONITORED_BANDS Konfiguration
    COMMON_BANDS = [
        # Index 0
        FrequencyBand("FM Radio", 87.5, 108.0, "UKW Rundfunk / FM Broadcast"),
        # Index 1
        FrequencyBand("VHF I", 46.0, 68.0, "Analog TV Band I / DAB"),
        # Index 2
        FrequencyBand("VHF II", 87.5, 108.0, "FM Broadcast (VHF II)"),
        # Index 3
        FrequencyBand("VHF III", 174.0, 230.0, "Analog TV Band III / DVB-T I-IV"),
        # Index 4
        FrequencyBand("UHF IV", 470.0, 606.0, "DVB-T Band IV (Hauptband)"),
        # Index 5
        FrequencyBand("UHF V", 606.0, 862.0, "DVB-T Band V (Hauptband)"),
        # Index 6
        FrequencyBand("GSM-900", 890.0, 960.0, "Mobilfunk D1/D2 (GSM-900)"),
        # Index 7
        FrequencyBand("GSM-1800", 1710.0, 1880.0, "Mobilfunk D3 (GSM-1800)"),
        # Index 8
        FrequencyBand("ISM 2.4 GHz", 2400.0, 2500.0, "WLAN / Bluetooth / ISM-Band"),
    ]
    
    def __init__(self, rtl_device_index: int = 0, sample_rate: int = 2000000, 
                 gain: str = 'auto', use_mock: bool = False):
        """
        Initialisiert RTL-SDR Scanner
        
        Args:
            rtl_device_index: Index des RTL-SDR Geräts (0 = erstes)
            sample_rate: Sample-Rate in Hz (Standard: 2 MSps für RTL2838)
            gain: 'auto' oder fester Wert in dB (z.B. '20.7', '25.4')
                  Typische Werte für RTL2838: 0-49.6 dB in 0.1er Schritten
            use_mock: Verwende Mock-Daten statt echter Hardware (für Entwicklung)
        """
        self.rtl_device_index = rtl_device_index
        self.sample_rate = sample_rate
        self.gain = gain
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
            
            self.is_connected = True
            
            # Log Gain-Konfiguration
            if self.gain == 'auto':
                logger.info(f"RTL-SDR Gerät {self.rtl_device_index} verbunden (Auto Gain)")
            else:
                logger.info(f"RTL-SDR Gerät {self.rtl_device_index} verbunden (Gain: {self.gain} dB)")
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
        Scanne einen Frequenzbereich und analysiere Aktivität
        
        Args:
            band: FrequencyBand zum Scannen
            num_samples: Anzahl der zu erfassenden Samples pro Frequenz
            
        Returns:
            ScanResult mit Analyse oder None bei Fehler
        """
        # Versuche zu verbinden wenn nicht verbunden
        if not self._ensure_connected():
            logger.warning("RTL-SDR nicht verbunden - kann nicht scannen")
            return None
        
        try:
            import rtlsdr
            
            start_time = datetime.now()
            num_frequencies = 150  # Feine Auflösung für bessere Frequenzauflösung
            
            frequencies = np.linspace(band.freq_start, band.freq_end, num_frequencies)
            power_values = []
            
            logger.info(f"Starte Scan für {band.name} ({band.freq_start}-{band.freq_end} MHz)")
            
            for freq in frequencies:
                try:
                    # Stelle Frequenz ein (in Hz)
                    # Wrap in try-except um Hardware-Crashes zu verhindern
                    try:
                        self.device.center_freq = int(freq * 1e6)
                    except Exception as freq_error:
                        logger.warning(f"Konnte Frequenz {freq} MHz nicht setzen: {freq_error}")
                        power_values.append(np.nan)
                        continue
                    
                    # Lies IQ-Samples
                    samples = self.device.read_samples(num_samples)
                    
                    # Berechne Power Spectral Density
                    power = np.abs(samples) ** 2
                    power_db = 10 * np.log10(np.mean(power) + 1e-10)
                    power_values.append(power_db)
                    
                except Exception as e:
                    logger.debug(f"Fehler beim Scan bei {freq} MHz: {e}")
                    power_values.append(np.nan)
            
            # Analysiere Ergebnisse
            power_values = np.array(power_values)
            power_values = power_values[~np.isnan(power_values)]
            
            if len(power_values) == 0:
                logger.warning(f"Keine gültigen Daten für {band.name}")
                return None
            
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
                scan_time=scan_duration
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
    
    return RTLSDRScanner(device_idx, sample_rate, gain)

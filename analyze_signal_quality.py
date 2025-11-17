#!/usr/bin/env python3
"""
Signal-Qualitäts-Analyzer für Solar Radio Band
Analysiert gespeicherte Spektrumdaten aus SQLite ohne RTL-SDR Gerät zu sperren
Perfekt um Signalqualität zu monitoren während der Scan läuft

Verwendung:
    python3 analyze_signal_quality.py [--time-range 24h] [--band 'Solar Radio']
"""

import argparse
import logging
import requests
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, Tuple

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SignalQualityAnalyzer:
    """Analysiert Signalqualität aus SQLite Daten"""
    
    def __init__(self, sqlite_rest_url='http://localhost:8002', time_range='24h'):
        """
        Args:
            sqlite_rest_url: URL zur SQLite REST API
            time_range: Zeitraum ('1h', '6h', '24h', '7d', '30d')
        """
        self.sqlite_rest_url = sqlite_rest_url
        self.time_range = time_range
        
    def fetch_spectrum_data(self, band_name='Solar Radio'):
        """Lädt Spektrumdaten aus SQLite REST API"""
        try:
            response = requests.get(
                f"{self.sqlite_rest_url}/api/read",
                params={'band_name': band_name, 'time_range': self.time_range},
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('status') != 'success':
                logger.error(f"API Fehler: {result.get('error', 'unbekannt')}")
                return None, None, None
            
            timestamps = result.get('timestamps', [])
            frequencies = np.array(result.get('frequencies', []), dtype=float)
            data_2d = np.array(result.get('data', []), dtype=float)
            
            if len(timestamps) == 0 or len(frequencies) == 0 or data_2d.size == 0:
                logger.error("Keine Daten in API-Response")
                return None, None, None
            
            logger.info(f"✅ Geladen: {len(timestamps)} Scans, {len(frequencies)} Frequenzen")
            return data_2d, timestamps, frequencies
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Daten: {e}")
            return None, None, None
    
    def analyze_spectrum(self, data_2d, timestamps, frequencies) -> Dict:
        """
        Analysiert die Spektrumdaten und berechnet Signalqualitäts-Metriken
        
        Returns:
            Dict mit SNR, Peak Power, Noise Floor, Activity, etc.
        """
        if data_2d is None or len(data_2d) == 0:
            return None
        
        # Berechne über alle Scans hinweg
        data_flat = data_2d.flatten()
        data_valid = data_flat[np.isfinite(data_flat) & (data_flat > -200)]
        
        if len(data_valid) == 0:
            logger.error("Keine gültigen Datenpunkte!")
            return None
        
        # Basis-Statistiken
        avg_power = np.mean(data_valid)
        peak_power = np.max(data_valid)
        median_power = np.median(data_valid)
        
        # Noise Floor: Untere 10% Perzentile
        noise_floor = np.percentile(data_valid, 10)
        
        # SNR: Peak - Noise Floor
        snr = peak_power - noise_floor
        
        # Dynamic Range
        dyn_range = peak_power - np.min(data_valid)
        
        # Activity: Anteil der Frequenzen über Noise Floor + 3dB
        active_threshold = noise_floor + 3
        activity_pct = 100 * np.sum(data_valid > active_threshold) / len(data_valid)
        
        # Strong Signal Ratio: über Noise Floor + 6dB
        strong_threshold = noise_floor + 6
        strong_ratio = 100 * np.sum(data_valid > strong_threshold) / len(data_valid)
        
        # Pro Frequenz-Analyse
        avg_per_freq = np.mean(data_2d, axis=0)
        peak_per_freq = np.max(data_2d, axis=0)
        
        # Beste/schlechteste Frequenzen
        best_freq_idx = np.argmax(peak_per_freq)
        worst_freq_idx = np.argmin(peak_per_freq)
        
        best_freq = frequencies[best_freq_idx]
        worst_freq = frequencies[worst_freq_idx]
        
        # Frequenzen mit starkem Signal (über Peak - 10dB)
        strong_freq_threshold = peak_power - 10
        active_freqs = np.sum(peak_per_freq > strong_freq_threshold)
        
        results = {
            'num_scans': len(timestamps),
            'num_frequencies': len(frequencies),
            'time_range_start': timestamps[0] if timestamps else None,
            'time_range_end': timestamps[-1] if timestamps else None,
            'avg_power_db': avg_power,
            'peak_power_db': peak_power,
            'median_power_db': median_power,
            'noise_floor_db': noise_floor,
            'snr_db': snr,
            'dynamic_range_db': dyn_range,
            'activity_pct': activity_pct,
            'strong_signal_ratio_pct': strong_ratio,
            'freq_with_strong_signals': active_freqs,
            'best_freq_mhz': best_freq,
            'best_freq_power_db': peak_per_freq[best_freq_idx],
            'worst_freq_mhz': worst_freq,
            'worst_freq_power_db': peak_per_freq[worst_freq_idx],
        }
        
        return results
    
    def print_analysis(self, results):
        """Druckt formatierte Analyseergebnisse"""
        if not results:
            logger.error("Keine Ergebnisse zum Anzeigen!")
            return
        
        logger.info("\n" + "=" * 75)
        logger.info("📊 SIGNAL-QUALITÄTS-ANALYSE")
        logger.info("=" * 75)
        
        logger.info(f"\n📈 DATENUMFANG:")
        logger.info(f"   Zeitraum: {results['time_range_start']} bis {results['time_range_end']}")
        logger.info(f"   Scans: {results['num_scans']}")
        logger.info(f"   Frequenzen pro Scan: {results['num_frequencies']}")
        logger.info(f"   Gesamt-Datenpunkte: {results['num_scans'] * results['num_frequencies']:,}")
        
        logger.info(f"\n📶 POWER-STATISTIKEN (dB):")
        logger.info(f"   Peak Power:        {results['peak_power_db']:>8.1f} dB")
        logger.info(f"   Average Power:     {results['avg_power_db']:>8.1f} dB")
        logger.info(f"   Median Power:      {results['median_power_db']:>8.1f} dB")
        logger.info(f"   Noise Floor (10%): {results['noise_floor_db']:>8.1f} dB")
        logger.info(f"   Dynamic Range:     {results['dynamic_range_db']:>8.1f} dB")
        
        logger.info(f"\n🎯 SIGNAL-QUALITÄT:")
        logger.info(f"   SNR (Peak-Noise):  {results['snr_db']:>8.1f} dB")
        logger.info(f"   Activity (>NF+3):  {results['activity_pct']:>8.1f} %")
        logger.info(f"   Strong Signals:    {results['strong_signal_ratio_pct']:>8.1f} % (>NF+6dB)")
        
        logger.info(f"\n📡 FREQUENZEN:")
        logger.info(f"   Beste Frequenz:    {results['best_freq_mhz']:>8.1f} MHz @ {results['best_freq_power_db']:>6.1f} dB")
        logger.info(f"   Schlechteste:      {results['worst_freq_mhz']:>8.1f} MHz @ {results['worst_freq_power_db']:>6.1f} dB")
        logger.info(f"   Mit starkem Signal: {results['freq_with_strong_signals']} Frequenzen")
        
        logger.info("\n" + "=" * 75 + "\n")
    
    def plot_spectrum_summary(self, data_2d, timestamps, frequencies, output_file='spectrum_analysis.png'):
        """Erstellt Visualisierung der Spektrumanalyse"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # Plot 1: Peak-Spektrum (über alle Scans)
        peak_spectrum = np.max(data_2d, axis=0)
        axes[0, 0].plot(frequencies, peak_spectrum, 'b-', linewidth=1.5)
        axes[0, 0].fill_between(frequencies, peak_spectrum, alpha=0.3)
        axes[0, 0].set_xlabel('Frequenz (MHz)', fontweight='bold')
        axes[0, 0].set_ylabel('Power (dB)', fontweight='bold')
        axes[0, 0].set_title('Peak-Spektrum (Maximum pro Frequenz)', fontweight='bold')
        axes[0, 0].grid(True, alpha=0.3)
        
        # Plot 2: Average-Spektrum
        avg_spectrum = np.mean(data_2d, axis=0)
        axes[0, 1].plot(frequencies, avg_spectrum, 'g-', linewidth=1.5)
        axes[0, 1].fill_between(frequencies, avg_spectrum, alpha=0.3, color='green')
        axes[0, 1].set_xlabel('Frequenz (MHz)', fontweight='bold')
        axes[0, 1].set_ylabel('Power (dB)', fontweight='bold')
        axes[0, 1].set_title('Durchschnitt-Spektrum (Mittel pro Frequenz)', fontweight='bold')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Plot 3: Power über Zeit (Durchschnitt aller Frequenzen)
        power_over_time = np.mean(data_2d, axis=1)
        axes[1, 0].plot(range(len(power_over_time)), power_over_time, 'r-', linewidth=1)
        axes[1, 0].set_xlabel('Scan-Index', fontweight='bold')
        axes[1, 0].set_ylabel('Power (dB)', fontweight='bold')
        axes[1, 0].set_title('Durchschnittliche Power über Zeit', fontweight='bold')
        axes[1, 0].grid(True, alpha=0.3)
        
        # Plot 4: Heatmap Mini (Peak Power pro Frequenz)
        # Normalisiere für bessere Visualisierung
        heatmap_data = peak_spectrum[np.newaxis, :]
        im = axes[1, 1].imshow(heatmap_data, aspect='auto', cmap='viridis')
        axes[1, 1].set_xlabel('Frequenz (MHz)', fontweight='bold')
        axes[1, 1].set_ylabel('Peak Power', fontweight='bold')
        axes[1, 1].set_title('Peak-Power nach Frequenz (Heatmap)', fontweight='bold')
        axes[1, 1].set_yticks([])
        plt.colorbar(im, ax=axes[1, 1], label='Power (dB)')
        
        # Setze X-Achsen-Labels für Frequenz-Plots
        for ax in [axes[0, 0], axes[0, 1], axes[1, 1]]:
            ax.set_xticks([frequencies[i] for i in np.linspace(0, len(frequencies)-1, 5, dtype=int)])
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        logger.info(f"📈 Grafik gespeichert: {output_file}\n")
        plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='Analysiert Signalqualität aus gespeicherten Spektrumdaten',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python3 analyze_signal_quality.py                    # Letzte 24h analysieren
  python3 analyze_signal_quality.py --time-range 6h   # Letzte 6 Stunden
  python3 analyze_signal_quality.py --time-range 7d   # Letzte Woche
  python3 analyze_signal_quality.py --output my_analysis.png
        """
    )
    
    parser.add_argument('--time-range', type=str, default='24h',
                       choices=['1h', '6h', '24h', '7d', '30d'],
                       help='Zeitraum für Analyse (default: 24h)')
    parser.add_argument('--band', type=str, default='Solar Radio',
                       help='Band-Name (default: Solar Radio)')
    parser.add_argument('--sqlite-url', type=str, default='http://localhost:8002',
                       help='SQLite REST API URL (default: http://localhost:8002)')
    parser.add_argument('--output', type=str, default='spectrum_analysis.png',
                       help='Ausgabedatei für Grafik (default: spectrum_analysis.png)')
    
    args = parser.parse_args()
    
    analyzer = SignalQualityAnalyzer(
        sqlite_rest_url=args.sqlite_url,
        time_range=args.time_range
    )
    
    logger.info(f"Analysiere Spektrum für '{args.band}' (Zeitraum: {args.time_range})...\n")
    
    # Lade Daten
    data_2d, timestamps, frequencies = analyzer.fetch_spectrum_data(args.band)
    
    if data_2d is None:
        logger.error("Fehler beim Laden der Daten - abgebrochen")
        return
    
    # Analysiere
    results = analyzer.analyze_spectrum(data_2d, timestamps, frequencies)
    
    if results:
        analyzer.print_analysis(results)
        analyzer.plot_spectrum_summary(data_2d, timestamps, frequencies, args.output)
        logger.info("✅ Analyse abgeschlossen!")
    else:
        logger.error("Fehler bei der Analyse")


if __name__ == '__main__':
    main()

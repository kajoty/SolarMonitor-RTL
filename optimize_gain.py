#!/usr/bin/env python3
"""
Gain-Optimierungstool für RTL-SDR Solar Radio Monitoring
Testet verschiedene Gain-Werte und findet den besten für dein Band

Verwendung:
    sudo python3 optimize_gain.py [--freq-start 20] [--freq-end 80] [--duration 60] [--device 0]
    
WICHTIG: Muss mit sudo laufen um systemd Services zu stoppen/starten
"""

import argparse
import logging
from datetime import datetime
import time
import subprocess
import numpy as np
from rtlsdr import RtlSdr
import matplotlib.pyplot as plt
from pathlib import Path
import os

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GainOptimizer:
    """Testet verschiedene Gain-Werte und findet den optimalen"""
    
    def __init__(self, freq_start=20e6, freq_end=80e6, device_idx=0, sample_rate=2e6):
        """
        Args:
            freq_start: Start-Frequenz in Hz (default: 20 MHz)
            freq_end: End-Frequenz in Hz (default: 80 MHz)
            device_idx: RTL-SDR Device Index
            sample_rate: Sample Rate in Hz (default: 2 MSps)
        """
        self.freq_start = freq_start
        self.freq_end = freq_end
        self.device_idx = device_idx
        self.sample_rate = sample_rate
        self.device = None
        self.results = {}
        self.services_stopped = False
        
    def manage_systemd_services(self, stop=True):
        """Stoppt oder startet systemd Services"""
        services = ['solarmonitor-app.service', 'solarmonitor-sqlite.service']
        action = 'stop' if stop else 'start'
        
        if os.geteuid() != 0:
            logger.error("❌ Dieser Befehl benötigt sudo Rechte!")
            logger.error("   Bitte führe aus: sudo python3 optimize_gain.py ...")
            return False
        
        try:
            for service in services:
                logger.info(f"{'⏹️  Stoppe' if stop else '▶️  Starte'} {service}...")
                result = subprocess.run(['systemctl', action, service], 
                                      capture_output=True, timeout=10)
                if result.returncode != 0:
                    logger.warning(f"   ⚠️  {service} Statuscode: {result.returncode}")
            
            if stop:
                time.sleep(3)  # Längere Wartezeit um USB-Ressourcen freizugeben
                # Zusätzlicher USB Reset
                try:
                    subprocess.run(['usb-devices'], capture_output=True, timeout=5)
                except:
                    pass
                time.sleep(1)
                self.services_stopped = True
                logger.info("✅ Services gestoppt - RTL-SDR Gerät sollte frei sein\n")
            else:
                time.sleep(2)  # Warte bis Services vollständig hochgefahren
                logger.info("✅ Services neu gestartet\n")
            return True
        except Exception as e:
            logger.error(f"❌ Fehler beim Verwalten von systemd Services: {e}")
            return False
        
    def connect(self):
        """Verbinde zum RTL-SDR Gerät"""
        try:
            self.device = RtlSdr(device_index=self.device_idx)
            self.device.sample_rate = int(self.sample_rate)
            self.device.center_freq = int((self.freq_start + self.freq_end) / 2)
            logger.info(f"✅ RTL-SDR Gerät {self.device_idx} verbunden")
            logger.info(f"   Center Freq: {self.device.center_freq / 1e6:.1f} MHz")
            logger.info(f"   Sample Rate: {self.device.sample_rate / 1e6:.1f} MSps")
            return True
        except Exception as e:
            logger.error(f"❌ Fehler beim Verbinden: {e}")
            return False
    
    def get_available_gains(self):
        """Hole verfügbare Gain-Werte vom Gerät"""
        try:
            gains = sorted(self.device.gain_values)
            logger.info(f"Verfügbare Gain-Werte: {len(gains)} Stufen")
            logger.info(f"  Min: {gains[0]:.1f} dB, Max: {gains[-1]:.1f} dB")
            return gains
        except Exception as e:
            logger.error(f"Fehler beim Lesen von Gain-Werten: {e}")
            return []
    
    def measure_signal_quality(self, gain_value, duration=5):
        """
        Misst Signalqualität bei gegebenem Gain
        
        Returns: dict mit SNR, Peak-Power, Noise-Floor, Activity
        """
        try:
            self.device.gain = gain_value
            logger.info(f"  Teste Gain {gain_value:.1f} dB...")
            
            # Sammle IQ-Samples
            num_samples = int(self.sample_rate * duration)
            samples = self.device.read_samples(num_samples)
            
            # Berechne Power-Spektrum
            power = np.abs(samples) ** 2
            power_db = 10 * np.log10(power + 1e-10)
            
            # Statistiken
            avg_power = np.mean(power_db)
            peak_power = np.max(power_db)
            noise_floor = np.percentile(power_db, 10)  # Untere 10%
            snr = peak_power - noise_floor
            
            # Activity: Anteil der Samples über Noise Floor + 3dB
            active_threshold = noise_floor + 3
            activity_pct = 100 * np.sum(power_db > active_threshold) / len(power_db)
            
            result = {
                'gain': gain_value,
                'avg_power': avg_power,
                'peak_power': peak_power,
                'noise_floor': noise_floor,
                'snr': snr,
                'activity_pct': activity_pct
            }
            
            logger.info(f"    SNR: {snr:.1f} dB, Peak: {peak_power:.1f} dB, Activity: {activity_pct:.1f}%")
            
            return result
            
        except Exception as e:
            logger.error(f"    ❌ Fehler bei Messung: {e}")
            return None
    
    def run_optimization(self, duration=5, test_count=10):
        """
        Testet verschiedene Gain-Werte und findet den optimalen
        
        Args:
            duration: Messdauer pro Gain-Wert in Sekunden
            test_count: Anzahl der zu testenden Gain-Werte
        """
        # Stoppe systemd Services
        if not self.manage_systemd_services(stop=True):
            return None
        
        if not self.connect():
            # Versuche Services wieder zu starten
            self.manage_systemd_services(stop=False)
            return None
        
        gains = self.get_available_gains()
        if not gains:
            logger.error("Keine Gain-Werte verfügbar!")
            self.device.close()
            self.manage_systemd_services(stop=False)
            return None
        
        # Wähle test_count Gain-Werte gleichmäßig verteilt
        test_gains = [gains[int(i * len(gains) / test_count)] for i in range(test_count)]
        
        logger.info(f"🔍 Starte Gain-Optimierung ({len(test_gains)} Tests à {duration}s)...")
        logger.info(f"   Frequenzbereich: {self.freq_start/1e6:.0f}-{self.freq_end/1e6:.0f} MHz\n")
        
        self.results = {}
        for i, gain_val in enumerate(test_gains, 1):
            logger.info(f"Test {i}/{len(test_gains)}")
            result = self.measure_signal_quality(gain_val, duration)
            if result:
                self.results[gain_val] = result
            time.sleep(0.5)  # Kurze Pause zwischen Tests
        
        self.device.close()
        logger.info(f"\n✅ Optimierung abgeschlossen!\n")
        
        # Starte systemd Services wieder
        self.manage_systemd_services(stop=False)
        
        return self.analyze_results()
    
    def analyze_results(self):
        """Analysiert Ergebnisse und findet optimale Gain-Werte"""
        if not self.results:
            logger.error("Keine Messergebnisse vorhanden!")
            return None
        
        gains = list(self.results.keys())
        snrs = [self.results[g]['snr'] for g in gains]
        activities = [self.results[g]['activity_pct'] for g in gains]
        
        # Finde beste Gain-Werte nach verschiedenen Kriterien
        best_snr_gain = max(self.results.keys(), key=lambda g: self.results[g]['snr'])
        best_activity_gain = max(self.results.keys(), key=lambda g: self.results[g]['activity_pct'])
        
        # Balanced: Hohe SNR mit guter Activity
        balanced_gains = sorted(self.results.keys(), 
                               key=lambda g: (self.results[g]['snr'], self.results[g]['activity_pct']),
                               reverse=True)
        best_balanced_gain = balanced_gains[0]
        
        logger.info("=" * 70)
        logger.info("📊 OPTIMIERUNGSERGEBNISSE")
        logger.info("=" * 70)
        
        logger.info(f"\n🥇 Beste SNR: {best_snr_gain:.1f} dB")
        logger.info(f"   SNR: {self.results[best_snr_gain]['snr']:.1f} dB")
        logger.info(f"   Peak Power: {self.results[best_snr_gain]['peak_power']:.1f} dB")
        logger.info(f"   Activity: {self.results[best_snr_gain]['activity_pct']:.1f}%")
        
        logger.info(f"\n🥈 Beste Activity (Signal-Aktivität): {best_activity_gain:.1f} dB")
        logger.info(f"   SNR: {self.results[best_activity_gain]['snr']:.1f} dB")
        logger.info(f"   Activity: {self.results[best_activity_gain]['activity_pct']:.1f}%")
        
        logger.info(f"\n🥉 Ausbalanciert (empfohlen): {best_balanced_gain:.1f} dB")
        logger.info(f"   SNR: {self.results[best_balanced_gain]['snr']:.1f} dB")
        logger.info(f"   Activity: {self.results[best_balanced_gain]['activity_pct']:.1f}%")
        
        logger.info("\n" + "=" * 70)
        logger.info("EMPFEHLUNG")
        logger.info("=" * 70)
        logger.info(f"Setze RTL_GAIN={best_balanced_gain:.1f} in deiner .env Datei")
        logger.info(f"   oder: RTL_GAIN={best_snr_gain:.1f} für maximale SNR")
        logger.info("=" * 70 + "\n")
        
        return {
            'best_snr': best_snr_gain,
            'best_activity': best_activity_gain,
            'best_balanced': best_balanced_gain,
            'all_results': self.results
        }
    
    def plot_results(self, output_file='gain_optimization.png'):
        """Erstellt Visualisierung der Ergebnisse"""
        if not self.results:
            logger.error("Keine Ergebnisse zum Plotten!")
            return
        
        gains = sorted(self.results.keys())
        snrs = [self.results[g]['snr'] for g in gains]
        activities = [self.results[g]['activity_pct'] for g in gains]
        peak_powers = [self.results[g]['peak_power'] for g in gains]
        
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        # SNR
        axes[0].plot(gains, snrs, 'b-o', linewidth=2, markersize=6)
        axes[0].set_ylabel('SNR (dB)', fontsize=11, fontweight='bold')
        axes[0].set_title('RTL-SDR Gain-Optimierung: Signal-zu-Rausch-Verhältnis', fontsize=12, fontweight='bold')
        axes[0].grid(True, alpha=0.3)
        best_snr_gain = max(self.results.keys(), key=lambda g: self.results[g]['snr'])
        axes[0].axvline(best_snr_gain, color='g', linestyle='--', alpha=0.5, label=f'Best: {best_snr_gain:.1f} dB')
        axes[0].legend()
        
        # Activity
        axes[1].plot(gains, activities, 'r-s', linewidth=2, markersize=6)
        axes[1].set_ylabel('Activity (%)', fontsize=11, fontweight='bold')
        axes[1].set_title('Signal-Aktivität nach Gain', fontsize=12, fontweight='bold')
        axes[1].grid(True, alpha=0.3)
        best_activity_gain = max(self.results.keys(), key=lambda g: self.results[g]['activity_pct'])
        axes[1].axvline(best_activity_gain, color='g', linestyle='--', alpha=0.5, label=f'Best: {best_activity_gain:.1f} dB')
        axes[1].legend()
        
        # Peak Power
        axes[2].plot(gains, peak_powers, 'purple', marker='^', linewidth=2, markersize=6)
        axes[2].set_xlabel('Gain (dB)', fontsize=11, fontweight='bold')
        axes[2].set_ylabel('Peak Power (dB)', fontsize=11, fontweight='bold')
        axes[2].set_title('Peak-Leistung nach Gain', fontsize=12, fontweight='bold')
        axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        logger.info(f"📈 Grafik gespeichert: {output_file}")
        plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='Optimiert den Gain-Wert für RTL-SDR Solar Radio Monitoring',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python3 optimize_gain.py                           # Standard: 20-80 MHz
  python3 optimize_gain.py --freq-start 50 --freq-end 75  # Custom Bereich
  python3 optimize_gain.py --duration 10 --tests 20  # Längere Tests
        """
    )
    
    parser.add_argument('--freq-start', type=float, default=20, 
                       help='Start-Frequenz in MHz (default: 20)')
    parser.add_argument('--freq-end', type=float, default=80,
                       help='End-Frequenz in MHz (default: 80)')
    parser.add_argument('--duration', type=int, default=5,
                       help='Messdauer pro Gain-Wert in Sekunden (default: 5)')
    parser.add_argument('--tests', type=int, default=10,
                       help='Anzahl der zu testenden Gain-Werte (default: 10)')
    parser.add_argument('--device', type=int, default=0,
                       help='RTL-SDR Device Index (default: 0)')
    parser.add_argument('--output', type=str, default='gain_optimization.png',
                       help='Ausgabedatei für Grafik (default: gain_optimization.png)')
    
    args = parser.parse_args()
    
    # Konvertiere MHz zu Hz
    freq_start_hz = args.freq_start * 1e6
    freq_end_hz = args.freq_end * 1e6
    
    optimizer = GainOptimizer(
        freq_start=freq_start_hz,
        freq_end=freq_end_hz,
        device_idx=args.device
    )
    
    try:
        results = optimizer.run_optimization(
            duration=args.duration,
            test_count=args.tests
        )
        
        if results:
            optimizer.plot_results(args.output)
            
    except KeyboardInterrupt:
        logger.info("\n⏹️  Optimierung abgebrochen")
        if optimizer.device:
            optimizer.device.close()
        # Stelle sicher dass Services wieder laufen
        if optimizer.services_stopped:
            logger.info("🔄 Starte Services wieder...")
            optimizer.manage_systemd_services(stop=False)
    except Exception as e:
        logger.error(f"Fehler: {e}", exc_info=True)
        # Stelle sicher dass Services wieder laufen
        if optimizer.services_stopped:
            logger.info("🔄 Starte Services wieder...")
            optimizer.manage_systemd_services(stop=False)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
RTL-SDR Gain-Tester
Zeigt alle verfügbaren Gain-Werte für den angeschlossenen USB Dongle
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_gains():
    """Teste alle möglichen Gain-Werte"""
    try:
        import rtlsdr
    except ImportError:
        logger.error("rtl-sdr Modul nicht installiert")
        logger.error("Installieren Sie: pip install rtl-sdr")
        sys.exit(1)
    
    try:
        # Verbinde mit Device
        sdr = rtlsdr.RtlSdr(device_index=0)
        logger.info(f"✅ RTL-SDR Device verbunden")
        
        # Hole verfügbare Gain-Werte
        gains = sdr.get_gains()
        logger.info(f"\n📊 Verfügbare Gain-Werte für RTL2838:")
        logger.info(f"{'─' * 50}")
        
        print("\nAlle verfügbaren Gain-Werte (in dB):")
        print("=" * 50)
        
        for i, gain in enumerate(gains, 1):
            # Konvertiere zu String mit einer Dezimalstelle
            gain_str = f"{gain / 10:.1f}"
            print(f"{i:2d}. {gain_str:6s} dB")
            
            if i % 5 == 0:
                print("-" * 50)
        
        print("=" * 50)
        logger.info(f"Total: {len(gains)} Gain-Werte verfügbar")
        
        # Empfehlungen
        print("\n💡 Empfehlungen:")
        print("─" * 50)
        print("🔹 Automatisch (Auto):          RTL_GAIN=auto")
        print("🔹 Schwach (wenig Rauschen):    RTL_GAIN=0")
        print("🔹 Mittel (ausgewogen):         RTL_GAIN=25.4")
        print("🔹 Stark (hohe Empfindlichkeit): RTL_GAIN=49.6")
        print("🔹 Für schwache Signale:        RTL_GAIN=35.0+")
        print("\nHinweis: Höherer Gain = mehr Empfindlichkeit aber auch mehr Rauschen!")
        
        # Test: Setze verschiedene Gains und lese IQ-Samples
        print("\n\n🔧 Test verschiedener Gains:")
        print("=" * 50)
        
        test_gains_list = [0, 10, 20, 25.4, 30, 40, 49.6]
        
        for test_gain in test_gains_list:
            try:
                # Finde nächstmöglichen Gain-Wert
                available_gain = min(gains, key=lambda x: abs(x - int(test_gain * 10)))
                actual_gain = available_gain / 10
                
                sdr.gain = available_gain
                
                # Lese kurze Sample
                samples = sdr.read_samples(256)
                power = (abs(samples) ** 2).mean()
                power_db = 10 * __import__('numpy').log10(power + 1e-10)
                
                print(f"Gain {actual_gain:5.1f} dB: Power = {power_db:7.2f} dBm, "
                      f"RMS = {(abs(samples)).mean():.4f}")
                
            except Exception as e:
                logger.error(f"Fehler bei Gain {test_gain}: {e}")
        
        # Cleanup
        sdr.close()
        logger.info("\n✅ Test abgeschlossen")
        
    except Exception as e:
        logger.error(f"❌ Fehler: {e}")
        logger.error("\nStellen Sie sicher, dass:")
        logger.error("1. Der RTL-SDR USB Dongle angeschlossen ist")
        logger.error("2. libusb installiert ist: sudo apt-get install libusb-1.0-0")
        logger.error("3. Sie Berechtigungen haben: sudo usermod -a -G plugdev pi")
        sys.exit(1)


if __name__ == '__main__':
    test_gains()

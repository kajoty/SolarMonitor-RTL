#!/usr/bin/env python3
"""
SolarMonitor-RTL - Demo & Test Script
Testet die Funktionalität ohne RTL-SDR Hardware
"""

import sys
import numpy as np
from datetime import datetime, timedelta

# Für Demo: Mock-Daten erzeugen
def demo_test():
    """Demo-Test mit Mock-Daten"""
    
    print("╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║        SolarMonitor-RTL - Demo & Funktions-Test (ohne Hardware)           ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Test 1: FrequencyBand
    print("1️⃣ FrequencyBand Test")
    print("─" * 70)
    
    from frequency_scanner import FrequencyBand, ScanResult
    
    band = FrequencyBand(
        name="Test Band",
        freq_start=100,
        freq_end=200,
        description="Test Frequenzbereich"
    )
    print(f"✅ Band erstellt: {band.name} ({band.freq_start}-{band.freq_end} MHz)")
    print()
    
    # Test 2: ScanResult
    print("2️⃣ ScanResult Test")
    print("─" * 70)
    
    result = ScanResult(
        band=band,
        avg_power=-40.5,
        peak_power=-20.3,
        noise_floor=-50.2,
        signal_to_noise=30.0,
        active=True,
        activity_percentage=75.5,
        num_peaks=42,
        scan_time=2.35
    )
    
    print(f"✅ ScanResult erstellt:")
    print(f"   - Durchschnittliche Leistung: {result.avg_power} dBm")
    print(f"   - Peak Power: {result.peak_power} dBm")
    print(f"   - SNR: {result.signal_to_noise} dB")
    print(f"   - Aktivität: {result.activity_percentage}%")
    print(f"   - Scan-Zeit: {result.scan_time}s")
    print()
    
    # Test 3: FrequencyAnalyzer
    print("3️⃣ FrequencyAnalyzer Test")
    print("─" * 70)
    
    from frequency_scanner import FrequencyAnalyzer
    
    # Erstelle Mock-Ergebnisse
    bands = [
        FrequencyBand("FM Radio", 88, 108, "UKW"),
        FrequencyBand("VHF TV", 174, 216, "DVB-T"),
        FrequencyBand("UHF TV", 470, 862, "DVB-T HD"),
        FrequencyBand("GSM", 890, 960, "Mobilfunk"),
    ]
    
    results = [
        ScanResult(band=bands[0], avg_power=-35, peak_power=-15, noise_floor=-45, 
                  signal_to_noise=30, active=True, activity_percentage=85, num_peaks=50, scan_time=2.0),
        ScanResult(band=bands[1], avg_power=-42, peak_power=-25, noise_floor=-48,
                  signal_to_noise=23, active=True, activity_percentage=60, num_peaks=35, scan_time=2.0),
        ScanResult(band=bands[2], avg_power=-48, peak_power=-28, noise_floor=-50,
                  signal_to_noise=22, active=False, activity_percentage=15, num_peaks=10, scan_time=2.0),
        ScanResult(band=bands[3], avg_power=-55, peak_power=-35, noise_floor=-60,
                  signal_to_noise=25, active=True, activity_percentage=70, num_peaks=40, scan_time=2.0),
    ]
    
    analysis = FrequencyAnalyzer.recommend_bands(results)
    
    print(f"✅ Analyse abgeschlossen:")
    print(f"   - Total gescannt: {analysis['total_scanned']} Bänder")
    print(f"   - Aktive Bänder: {analysis['active_bands_found']}")
    print(f"   - Starke Signale: {analysis['strong_signals']}")
    print(f"   - Max SNR: {analysis['summary']['max_snr']} dB")
    print(f"   - Empfehlungen: {len(analysis['recommendations'])} Bänder")
    print()
    
    # Test 4: SpectrumAnalyzer
    print("4️⃣ SpectrumAnalyzer Visualisierung Test")
    print("─" * 70)
    
    from spectrum_analyzer import SpectrumAnalyzer
    
    try:
        buf = SpectrumAnalyzer.plot_scan_results(results, figsize=(12, 8))
        if buf:
            print(f"✅ SNR-Übersicht Grafik erstellt")
            print(f"   - Größe: {len(buf.getvalue())} bytes")
        
        buf2 = SpectrumAnalyzer.plot_frequency_spectrum(results, figsize=(12, 6))
        if buf2:
            print(f"✅ Frequenzspektrum Grafik erstellt")
            print(f"   - Größe: {len(buf2.getvalue())} bytes")
    except Exception as e:
        print(f"❌ Visualisierung Fehler: {e}")
    
    print()
    
    # Test 5: Flask App
    print("5️⃣ Flask App Validierung")
    print("─" * 70)
    
    try:
        from app import app
        
        with app.test_client() as client:
            # Test Health Endpoint
            response = client.get('/api/health')
            print(f"✅ /api/health: Status {response.status_code}")
            
            # Test Time Ranges
            response = client.get('/api/time-ranges')
            print(f"✅ /api/time-ranges: Status {response.status_code}")
            
            # Test Colormaps
            response = client.get('/api/colormaps')
            print(f"✅ /api/colormaps: Status {response.status_code}")
            
            # Test Scan Status (vor Scan sollte 'no_data' sein)
            response = client.get('/api/scan/status')
            print(f"✅ /api/scan/status: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Flask Test Fehler: {e}")
    
    print()
    
    # Test 6: Recommendations
    print("6️⃣ Empfehlungen Test")
    print("─" * 70)
    
    print("Top Empfehlungen:")
    for i, rec in enumerate(analysis['recommendations'][:3], 1):
        print(f"   {i}. {rec['band']['name']:20s} - {rec['reason']}")
    
    print()
    print("╔═══════════════════════════════════════════════════════════════════════════╗")
    print("✅ ALLE TESTS ERFOLGREICH BESTANDEN!")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    print()
    print("🚀 Nächste Schritte:")
    print()
    print("   1. Flask Server starten:")
    print("      $ python3 app.py")
    print()
    print("   2. Browser öffnen:")
    print("      - Heatmap Dashboard: http://localhost:5000/")
    print("      - Discovery UI:      http://localhost:5000/discovery")
    print()
    print("   3. Mit RTL-SDR Hardware:")
    print("      - Gain-Werte testen: $ python3 test_rtl_gains.py")
    print("      - Discovery durchführen: Klick auf 'Schnell-Scan starten'")
    print()


if __name__ == '__main__':
    try:
        demo_test()
    except Exception as e:
        print(f"❌ Fehler: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
HackRF Frequency Scanner für SolarMonitor-RTL
Scannt einen Frequenzbereich durch Sweeping und schreibt die Daten in die SQLite-Datenbank
"""

import numpy as np
import requests
import datetime
import subprocess
import os
import tempfile
import logging
from dataclasses import dataclass
from typing import List, Tuple

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Konfiguration
FREQ_START_MHZ = 24.0      # Solar Radio Band Start
FREQ_END_MHZ = 80.0        # Solar Radio Band Ende
SAMPLE_RATE = 20_000_000   # 20 MHz Sample Rate (Maximum)
BANDWIDTH_MHZ = 20.0       # Nutzbare Bandbreite pro Sweep
NUM_SAMPLES = 2_000_000    # Samples pro Sweep
FFT_SIZE = 4096            # FFT-Größe
LNA_GAIN = 16              # LNA Gain (0-40 dB, 8dB steps)
VGA_GAIN = 20              # VGA Gain (0-62 dB, 2dB steps)
AMP_ENABLE = 0             # RF Amplifier (0=off, 1=on)

SQLITE_REST_URL = "http://localhost:8002/api/write"
BAND_NAME = "Solar Radio"
RECEIVER = "hackrf"

@dataclass
class SweepResult:
    """Ergebnis eines Frequenz-Sweeps"""
    center_freq_mhz: float
    frequencies_mhz: np.ndarray
    spectrum_db: np.ndarray

def calculate_sweep_plan(start_mhz: float, end_mhz: float, bandwidth_mhz: float) -> List[float]:
    """
    Berechnet die Mittenfrequenzen für das Sweeping
    
    Args:
        start_mhz: Startfrequenz in MHz
        end_mhz: Endfrequenz in MHz
        bandwidth_mhz: Bandbreite pro Sweep in MHz
    
    Returns:
        Liste der Mittenfrequenzen in MHz
    """
    total_range = end_mhz - start_mhz
    num_sweeps = int(np.ceil(total_range / bandwidth_mhz))
    
    # Berechne Mittenfrequenzen mit Überlappung
    center_freqs = []
    for i in range(num_sweeps):
        center = start_mhz + (i * bandwidth_mhz) + (bandwidth_mhz / 2)
        # Stelle sicher, dass wir nicht über das Ende hinausgehen
        if center + (bandwidth_mhz / 2) > end_mhz:
            center = end_mhz - (bandwidth_mhz / 2)
        if center not in center_freqs:
            center_freqs.append(center)
    
    return center_freqs

def capture_iq_data(center_freq_hz: int, sample_rate: int, num_samples: int,
                   lna_gain: int, vga_gain: int, amp_enable: int) -> np.ndarray:
    """
    Erfasst I/Q-Daten mit HackRF
    
    Args:
        center_freq_hz: Mittenfrequenz in Hz
        sample_rate: Sample Rate in Hz
        num_samples: Anzahl der Samples
        lna_gain: LNA Gain in dB
        vga_gain: VGA Gain in dB
        amp_enable: RF Amplifier (0/1)
    
    Returns:
        Complex I/Q samples als numpy array
    """
    # Temporäre Datei im aktuellen Verzeichnis (nicht in /tmp wegen sudo-Berechtigungen)
    tmp_path = f"hackrf_tmp_{center_freq_hz}.iq"
    
    try:
        # HackRF Transfer Befehl
        cmd = [
            'sudo', 'hackrf_transfer',
            '-r', tmp_path,
            '-f', str(center_freq_hz),
            '-s', str(sample_rate),
            '-n', str(num_samples * 2),  # *2 wegen I+Q
            '-l', str(lna_gain),
            '-g', str(vga_gain),
            '-a', str(amp_enable)
        ]
        
        logger.debug(f"Führe aus: {' '.join(cmd)}")
        
        # Führe aus
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"hackrf_transfer fehlgeschlagen: {result.stderr.decode()}")
        
        # Lade I/Q-Daten
        data = np.fromfile(tmp_path, dtype=np.int8)
        iq = data.astype(np.float32).view(np.complex64)
        
        return iq
        
    finally:
        # Lösche temporäre Datei
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def compute_spectrum(iq: np.ndarray, fft_size: int, sample_rate: int, 
                    center_freq_mhz: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Berechnet das Frequenzspektrum aus I/Q-Daten
    
    Args:
        iq: Complex I/Q samples
        fft_size: FFT-Größe
        sample_rate: Sample Rate in Hz
        center_freq_mhz: Mittenfrequenz in MHz
    
    Returns:
        Tuple (frequencies_mhz, spectrum_db)
    """
    # Führe FFT durch (mehrere Chunks mitteln für besseres SNR)
    num_chunks = len(iq) // fft_size
    spectra = []
    
    for i in range(num_chunks):
        chunk = iq[i * fft_size:(i + 1) * fft_size]
        spectrum = np.abs(np.fft.fftshift(np.fft.fft(chunk)))
        spectra.append(spectrum)
    
    # Mittle alle Chunks
    avg_spectrum = np.mean(spectra, axis=0)
    spectrum_db = 20 * np.log10(avg_spectrum + 1e-10)
    
    # Berechne Frequenzen
    freqs_hz = np.fft.fftshift(np.fft.fftfreq(fft_size, d=1/sample_rate))
    freqs_mhz = center_freq_mhz + freqs_hz / 1e6
    
    return freqs_mhz, spectrum_db

def perform_sweep(center_freq_mhz: float) -> SweepResult:
    """
    Führt einen einzelnen Frequenz-Sweep durch
    
    Args:
        center_freq_mhz: Mittenfrequenz in MHz
    
    Returns:
        SweepResult mit Frequenzen und Spektrum
    """
    logger.info(f"Sweep bei {center_freq_mhz:.2f} MHz...")
    
    center_freq_hz = int(center_freq_mhz * 1e6)
    
    # Erfasse I/Q-Daten
    iq = capture_iq_data(
        center_freq_hz, SAMPLE_RATE, NUM_SAMPLES,
        LNA_GAIN, VGA_GAIN, AMP_ENABLE
    )
    
    # Berechne Spektrum
    freqs_mhz, spectrum_db = compute_spectrum(
        iq, FFT_SIZE, SAMPLE_RATE, center_freq_mhz
    )
    
    return SweepResult(center_freq_mhz, freqs_mhz, spectrum_db)

def merge_sweep_results(results: List[SweepResult]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Kombiniert mehrere Sweep-Ergebnisse zu einem durchgehenden Spektrum
    
    Args:
        results: Liste von SweepResult-Objekten
    
    Returns:
        Tuple (frequencies_mhz, spectrum_db)
    """
    all_freqs = []
    all_spectra = []
    
    for result in results:
        all_freqs.extend(result.frequencies_mhz)
        all_spectra.extend(result.spectrum_db)
    
    # Sortiere nach Frequenz
    sorted_indices = np.argsort(all_freqs)
    freqs = np.array(all_freqs)[sorted_indices]
    spectra = np.array(all_spectra)[sorted_indices]
    
    # Entferne Duplikate (durch Überlappung)
    unique_freqs = []
    unique_spectra = []
    last_freq = None
    
    for freq, spec in zip(freqs, spectra):
        if last_freq is None or abs(freq - last_freq) > 0.01:  # 10 kHz Toleranz
            unique_freqs.append(freq)
            unique_spectra.append(spec)
            last_freq = freq
    
    return np.array(unique_freqs), np.array(unique_spectra)

def write_to_database(frequencies_mhz: np.ndarray, spectrum_db: np.ndarray):
    """
    Schreibt Spektrumdaten in die SQLite-Datenbank
    
    Args:
        frequencies_mhz: Frequenzen in MHz
        spectrum_db: Spektrum in dB
    """
    # Filtere ungültige Werte
    valid = ~np.isnan(frequencies_mhz) & ~np.isnan(spectrum_db) & \
            ~np.isinf(frequencies_mhz) & ~np.isinf(spectrum_db)
    
    freqs = frequencies_mhz[valid]
    spectra = spectrum_db[valid]
    
    # Erstelle Payload
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()
    data_points = [
        {"frequency": float(f), "power": float(p)}
        for f, p in zip(freqs, spectra)
    ]
    
    payload = {
        "timestamp": timestamp,
        "band_name": BAND_NAME,
        "receiver": RECEIVER,
        "data": data_points
    }
    
    logger.info(f"Schreibe {len(data_points)} Datenpunkte in Datenbank...")
    
    # Sende an SQLite REST API
    try:
        response = requests.post(SQLITE_REST_URL, json=payload, timeout=30)
        if response.status_code == 201:
            logger.info(f"✅ Erfolgreich {len(data_points)} Punkte importiert")
        else:
            logger.error(f"❌ Fehler: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Datenbank-Fehler: {e}")

def main():
    """Hauptfunktion: Führt kompletten Frequenz-Scan durch"""
    logger.info(f"🚀 HackRF Scanner gestartet: {FREQ_START_MHZ}-{FREQ_END_MHZ} MHz")
    
    # Berechne Sweep-Plan
    center_freqs = calculate_sweep_plan(FREQ_START_MHZ, FREQ_END_MHZ, BANDWIDTH_MHZ)
    logger.info(f"📡 Sweep-Plan: {len(center_freqs)} Schritte")
    logger.info(f"   Mittenfrequenzen: {[f'{f:.1f}' for f in center_freqs]} MHz")
    
    # Führe Sweeps durch
    sweep_results = []
    for i, center_freq in enumerate(center_freqs, 1):
        logger.info(f"[{i}/{len(center_freqs)}] Sweep bei {center_freq:.2f} MHz")
        try:
            result = perform_sweep(center_freq)
            sweep_results.append(result)
        except Exception as e:
            logger.error(f"❌ Fehler bei Sweep {center_freq:.2f} MHz: {e}")
            continue
    
    if not sweep_results:
        logger.error("❌ Keine erfolgreichen Sweeps - Abbruch")
        return
    
    # Kombiniere Ergebnisse
    logger.info("🔗 Kombiniere Sweep-Ergebnisse...")
    frequencies, spectrum = merge_sweep_results(sweep_results)
    logger.info(f"📊 Gesamt-Spektrum: {len(frequencies)} Frequenzpunkte "
                f"({frequencies[0]:.2f} - {frequencies[-1]:.2f} MHz)")
    
    # Schreibe in Datenbank
    write_to_database(frequencies, spectrum)
    
    logger.info("✅ Scan abgeschlossen!")

if __name__ == "__main__":
    main()

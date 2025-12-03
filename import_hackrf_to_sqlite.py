import numpy as np
import requests
import datetime
import os

# Konfiguration
IQ_FILE = "hackrf_52mhz.iq"  # Pfad zur I/Q-Datei
CENTER_FREQ_MHZ = 52.0           # Mittenfrequenz in MHz
SAMPLE_RATE = 2_000_000          # Sample Rate in Hz
SQLITE_REST_URL = "http://localhost:8002/api/write"
BAND_NAME = "Solar Radio"
RECEIVER = "hackrf"

# FFT-Parameter
FFT_SIZE = 4096

# Hilfsfunktion: Lade I/Q-Daten

def load_iq_data(filename):
    data = np.fromfile(filename, dtype=np.int8)
    iq = data.astype(np.float32).view(np.complex64)
    return iq

# Hilfsfunktion: FFT und Spektrum

def compute_spectrum(iq, fft_size, sample_rate, center_freq_mhz):
    spectrum = np.abs(np.fft.fftshift(np.fft.fft(iq[:fft_size])))
    spectrum_db = 20 * np.log10(spectrum + 1e-6)
    freqs = np.fft.fftshift(np.fft.fftfreq(fft_size, d=1/sample_rate))
    freqs_mhz = center_freq_mhz + freqs / 1e6
    return freqs_mhz, spectrum_db

# Hauptfunktion: Import

def main():
    if not os.path.exists(IQ_FILE):
        print(f"Datei nicht gefunden: {IQ_FILE}")
        return
    iq = load_iq_data(IQ_FILE)
    freqs, spectrum_db = compute_spectrum(iq, FFT_SIZE, SAMPLE_RATE, CENTER_FREQ_MHZ)

    # Filtere ungültige Werte
    valid = ~np.isnan(freqs) & ~np.isnan(spectrum_db) & ~np.isinf(freqs) & ~np.isinf(spectrum_db)
    freqs = freqs[valid]
    spectrum_db = spectrum_db[valid]

    # Erstelle Payload
    timestamp = datetime.datetime.utcnow().isoformat()
    data_points = [
        {"frequency": float(f), "power": float(p)}
        for f, p in zip(freqs, spectrum_db)
    ]
    payload = {
        "timestamp": timestamp,
        "band_name": BAND_NAME,
        "receiver": RECEIVER,
        "data": data_points
    }

    # Sende an SQLite REST API
    response = requests.post(SQLITE_REST_URL, json=payload)
    if response.status_code == 201:
        print(f"Erfolgreich {len(data_points)} Punkte importiert.")
    else:
        print(f"Fehler: {response.status_code} - {response.text}")

if __name__ == "__main__":
    main()

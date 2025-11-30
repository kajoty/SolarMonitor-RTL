

"""
Flask REST API for RTL-SDR frequency monitoring with FFT heatmaps.
Data storage: SQLite via REST API.
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import os
import logging
from datetime import datetime, timedelta
import io
import threading
import requests
import numpy as np

# SQLite REST API server
SQLITE_REST_URL = "http://localhost:8002"

# Lade Umgebungsvariablen
load_dotenv()

# Import der Module
from heatmap_generator import create_heatmap_generator_from_env
from frequency_scanner import create_scanner_from_env, FrequencyAnalyzer, RTLSDRScanner
from spectrum_analyzer import SpectrumAnalyzer

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask App initialisieren
app = Flask(__name__)
CORS(app)

# Globale Instanzen
heatmap_gen = None
rtl_scanner = None
scan_results = None
scan_in_progress = False
scan_lock = threading.Lock()





def write_scan_to_sqlite(results, receiver='rtl'):
    """Schreibe Scan-Ergebnisse in SQLite via REST API"""
    try:
        for result in results:
            # Erstelle sauberen band name ohne Klammern (z.B. "Solar Radio (20-80 MHz)" → "Solar Radio")
            band_name_clean = result.band.name.split('(')[0].strip()
            
            logger.debug(f"Frequenzen: {result.frequencies is not None}, Shape: {result.frequencies.shape if result.frequencies is not None else 'N/A'}")
            logger.debug(f"Power-Werte: {result.power_values is not None}, Shape: {result.power_values.shape if result.power_values is not None else 'N/A'}")
            
            if result.frequencies is not None and result.power_values is not None:
                # Erstelle Payload für SQLite REST API
                # Format: {timestamp, band_name, data: [{frequency, power}, ...]}
                data_points = []
                for freq, power in zip(result.frequencies, result.power_values):
                    # Filtere ungültige Werte (NaN, Inf)
                    if not (np.isnan(freq) or np.isnan(power) or np.isinf(freq) or np.isinf(power)):
                        data_points.append({
                            "frequency": float(freq),
                            "power": float(power)
                        })
                
                payload = {
                    "timestamp": result.timestamp,
                    "band_name": band_name_clean,
                    "receiver": receiver,
                    "data": data_points
                }
                
                logger.debug(f"SQLite Payload: {len(data_points)} Frequenzpunkte für {band_name_clean}")
                
                # Sende zu SQLite REST API
                try:
                    response = requests.post(
                        f"{SQLITE_REST_URL}/api/write",
                        json=payload,
                        timeout=10
                    )
                    if response.status_code == 201:
                        logger.info(f"✅ {len(data_points)} Spektrum-Punkte zu SQLite geschrieben ({band_name_clean})")
                    else:
                        logger.error(f"SQLite Write Error: {response.status_code} - {response.text}")
                        return False
                except Exception as e:
                    logger.error(f"SQLite REST API Fehler: {e}", exc_info=True)
                    return False
            else:
                logger.warning("Frequenzen oder Power-Werte sind None!")
        
        return True
    except Exception as e:
        logger.error(f"Fehler beim Schreiben zu SQLite: {e}", exc_info=True)
        return False


def init_heatmap_generator():
    """Initialisiert den Heatmap-Generator beim Start"""
    global heatmap_gen
    try:
        heatmap_gen = create_heatmap_generator_from_env()
        logger.info("Heatmap-Generator erfolgreich initialisiert")
    except Exception as e:
        logger.error(f"Fehler bei Initialisierung des Heatmap-Generators: {e}")


def init_scanner():
    """Initialisiert die verfügbaren Scanner beim Start"""
    global rtl_scanner
    try:
        rtl_scanner = create_scanner_from_env()
        logger.info("✅ RTL-SDR Scanner initialisiert")
            
    except Exception as e:
        logger.error(f"❌ Fehler bei Scanner-Initialisierung: {e}")
        rtl_scanner = None


@app.before_request
def before_request():
    """Initialize generators on first request"""
    global heatmap_gen, rtl_scanner
    if heatmap_gen is None:
        init_heatmap_generator()
    if rtl_scanner is None:
        init_scanner()


@app.route('/', methods=['GET'])
def index():
    """Startet die Web-Dashboard"""
    return render_template('dashboard.html')


@app.route('/discovery', methods=['GET'])
def discovery():
    """Startet die Frequenzbereich Discovery UI"""
    return render_template('discovery.html')


@app.route('/api/heatmap', methods=['GET'])
def get_heatmap():
    """
    REST Endpoint für Heatmap-Daten mit flexibler Zeit-Auswahl
    
    Query Parameter:
    - time_range: Vordefinierte Zeiträume
      * '1h', '6h', '24h', '7d', '30d' (Standard)
      * 'today': Heute ab 00:00
      * 'yesterday': Gestern (full day)
      * 'day_before': Vorgestern (full day)
      * 'this_week': Diese Woche ab Montag
      * 'last_week': Letzte Woche (Montag-Sonntag)
      * 'this_month': Dieser Monat ab 1.
    - start_time: ISO-8601 Timestamp (überschreibt time_range) z.B. "2025-11-17T10:00:00"
    - end_time: ISO-8601 Timestamp (optional, default: jetzt)
    - band_name: Band-Name zum Filtern (optional, default: 'Solar Radio')
    - freq_start: Startfrequenz in MHz (optional)
    - freq_end: Endfrequenz in MHz (optional)
    - cmap: Colormap ('viridis', 'jet', 'plasma', etc.) (default: 'viridis')
    - format: 'png' oder 'json' (default: 'png')
    
    Beispiele:
    - /api/heatmap?time_range=yesterday
    - /api/heatmap?time_range=today
    - /api/heatmap?start_time=2025-11-16T10:00:00&end_time=2025-11-17T10:00:00
    - /api/heatmap?time_range=this_week&band_name=Solar%20Radio
    
    Response:
    - PNG: Direktes Bild
    - JSON: {
        "status": "success" | "error",
        "time_range": "...",
        "data": "base64_encoded_image",
        "message": "..."
    }
    """
    try:
        # Parameter auslesen
        time_range_param = request.args.get('time_range', '24h')
        start_time_param = request.args.get('start_time', None)
        end_time_param = request.args.get('end_time', None)
        band_name = request.args.get('band_name', 'Solar Radio')
        freq_start = request.args.get('freq_start', type=float, default=None)
        freq_end = request.args.get('freq_end', type=float, default=None)
        cmap = request.args.get('cmap', 'viridis')
        response_format = request.args.get('format', 'png')
        receiver = request.args.get('receiver', 'rtl')  # NEU: Empfängerwahl
        
        # Konvertiere Zeit-Presets zu time_range Format
        from datetime import datetime, timedelta, timezone
        now = datetime.now()  # Lokale Zeit (nicht UTC!)
        
        # WICHTIG: Diese Variablen müssen immer definiert sein!
        use_custom_timestamps = False
        
        if start_time_param and end_time_param:
            # Benutzer hat explizit start_time/end_time angegeben
            use_custom_timestamps = True
            try:
                datetime.fromisoformat(start_time_param.replace('Z', '+00:00'))
                datetime.fromisoformat(end_time_param.replace('Z', '+00:00'))
                logger.info(f"Custom Zeit-Interval: {start_time_param} bis {end_time_param}")
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Ungültiges Zeit-Format: {e}'
                }), 400
        elif time_range_param in ['today', 'yesterday', 'day_before', 'this_week', 'last_week', 'this_month']:
            # Zeit-Preset erkannt - konvertiere zu absoluten Zeitstempeln
            preset_map = {
                'today': {
                    'start': now.replace(hour=0, minute=0, second=0, microsecond=0),
                    'end': now
                },
                'yesterday': {
                    'start': (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                    'end': now.replace(hour=0, minute=0, second=0, microsecond=0)
                },
                'day_before': {
                    'start': (now - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0),
                    'end': (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                },
                'this_week': {
                    'start': (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0),
                    'end': now
                },
                'last_week': {
                    'start': (now - timedelta(days=now.weekday() + 7)).replace(hour=0, minute=0, second=0, microsecond=0),
                    'end': (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
                },
                'this_month': {
                    'start': now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
                    'end': now
                },
            }
            
            preset = preset_map[time_range_param]
            start_time_param = preset['start'].isoformat()
            end_time_param = preset['end'].isoformat()
            use_custom_timestamps = True
            logger.info(f"Zeit-Preset '{time_range_param}': {start_time_param} bis {end_time_param}")
        else:
            # Standard time_range verwenden (1h, 6h, 24h, 7d, 30d)
            start_time_param = None
            end_time_param = None
            use_custom_timestamps = False
        
        # Validiere Parameter
        valid_ranges = ['1h', '6h', '24h', '7d', '30d', 'today', 'yesterday', 'day_before', 'this_week', 'last_week', 'this_month']
        if time_range_param not in valid_ranges:
            return jsonify({
                'status': 'error',
                'message': f'Ungültiger Zeitraum. Erlaubt: {valid_ranges}'
            }), 400
        
        if freq_start is not None and freq_end is not None:
            if freq_start >= freq_end:
                return jsonify({
                    'status': 'error',
                    'message': 'freq_start muss kleiner als freq_end sein'
                }), 400
        
        # Heatmap generieren
        # NEU: Empfängerwahl - aber für Heatmap verwenden wir die gespeicherten Daten aus DB
        # Der receiver-Parameter wird ignoriert, da Heatmaps aus historischen Daten kommen
        
        # Verwende den echten Heatmap-Generator aus der DB
        heatmap_base64 = heatmap_gen.get_heatmap_data(
            time_range=time_range_param if not use_custom_timestamps else None,
            band_name=band_name,
            freq_start=freq_start,
            freq_end=freq_end,
            start_time=start_time_param if use_custom_timestamps else None,
            end_time=end_time_param if use_custom_timestamps else None,
            cmap=cmap
        )

        # === Automatisches Löschen nach jeder dritten 24h-Heatmap ===
        import os, json
        COUNTER_FILE = '/tmp/heatmap_24h_counter.json'
        if time_range_param == '24h' and heatmap_base64 is not None:
            # Zähler aus Datei lesen
            try:
                if os.path.exists(COUNTER_FILE):
                    with open(COUNTER_FILE, 'r') as f:
                        counter_data = json.load(f)
                    count = counter_data.get('count', 0)
                else:
                    count = 0
            except Exception:
                count = 0
            count += 1
            # Schreibe neuen Wert zurück
            try:
                with open(COUNTER_FILE, 'w') as f:
                    json.dump({'count': count}, f)
            except Exception:
                pass
            # Wenn 3 erreicht: Datenbank löschen und Zähler zurücksetzen
            if count >= 3:
                try:
                    # SQLite REST API: alle Daten löschen
                    resp = requests.post('http://localhost:8002/api/delete', json={'days': 0}, timeout=30)
                    if resp.status_code == 200:
                        logger.info('Automatisches Löschen: Alle Datenbankeinträge wurden nach 3x 24h-Heatmap entfernt.')
                    else:
                        logger.warning(f'Automatisches Löschen fehlgeschlagen: {resp.text}')
                except Exception as e:
                    logger.error(f'Fehler beim automatischen Löschen: {e}')
                # Zähler zurücksetzen
                try:
                    with open(COUNTER_FILE, 'w') as f:
                        json.dump({'count': 0}, f)
                except Exception:
                    pass
        
        if heatmap_base64 is None:
            return jsonify({
                'status': 'no_data',
                'message': 'Keine Daten verfügbar. Bitte später erneut versuchen.',
                'time_range': time_range_param,
                'band_name': band_name,
                'timestamp': datetime.now().isoformat()
            }), 202
        
        if response_format == 'json':
            return jsonify({
                'status': 'success',
                'time_range': time_range_param,
                'freq_start': freq_start,
                'freq_end': freq_end,
                'cmap': cmap,
                'data': heatmap_base64,
                'timestamp': datetime.now().isoformat()
            })
        else:  # PNG
            # Dekodiere base64 und gebe als PNG zurück
            import base64
            image_data = base64.b64decode(heatmap_base64)
            buf = io.BytesIO(image_data)
            buf.seek(0)
            return send_file(buf, mimetype='image/png')
    
    except Exception as e:
        logger.error(f"Fehler im /api/heatmap Endpoint: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/heatmap/band', methods=['GET'])
def get_band_heatmap():
    """
    REST Endpoint für Band-basierte Heatmap-Daten
    
    Query Parameter:
    - band_name: Name des Frequenzbandes (z.B. 'FM Radio', 'UHF')
    - time_range: '1h', '6h', '24h', '7d', '30d' (default: '24h')
    - cmap: Colormap ('viridis', 'jet', 'plasma', etc.) (default: 'viridis')
    - format: 'json' oder 'png' (default: 'json')
    
    Response:
    - JSON: {
        "status": "success" | "error",
        "band_name": "...",
        "freq_start": ...,
        "freq_end": ...,
        "time_range": "...",
        "data": "base64_encoded_image",
        "message": "..."
    }
    """
    try:
        # Parameter auslesen
        band_name = request.args.get('band_name')
        time_range = request.args.get('time_range', '24h')
        cmap = request.args.get('cmap', 'viridis')
        response_format = request.args.get('format', 'json')
        
        if not band_name:
            return jsonify({
                'status': 'error',
                'message': 'Parameter "band_name" erforderlich'
            }), 400
        
        # Ermittle Frequenzbereich für das Band
        freq_range = None
        for band in RTLSDRScanner.COMMON_BANDS:
            if band.name == band_name:
                freq_range = (band.freq_start, band.freq_end)
                break
        
        if freq_range is None:
            return jsonify({
                'status': 'error',
                'message': f'Band "{band_name}" nicht gefunden'
            }), 400
        
        freq_start, freq_end = freq_range
        
        # Validiere Zeit-Parameter
        valid_ranges = ['1h', '6h', '24h', '7d', '30d']
        if time_range not in valid_ranges:
            return jsonify({
                'status': 'error',
                'message': f'Ungültiger Zeitraum. Erlaubt: {valid_ranges}'
            }), 400
        
        # Heatmap generieren
        heatmap_base64 = heatmap_gen.get_heatmap_data(
            time_range=time_range,
            band_name=band_name,
            freq_start=freq_start,
            freq_end=freq_end,
            cmap=cmap
        )
        
        if heatmap_base64 is None:
            return jsonify({
                'status': 'no_data',
                'message': f'Keine Daten für Band "{band_name}" verfügbar',
                'band_name': band_name,
                'freq_start': freq_start,
                'freq_end': freq_end,
                'time_range': time_range,
                'timestamp': datetime.now().isoformat()
            }), 202
        
        if response_format == 'json':
            return jsonify({
                'status': 'success',
                'band_name': band_name,
                'freq_start': freq_start,
                'freq_end': freq_end,
                'time_range': time_range,
                'cmap': cmap,
                'data': heatmap_base64,
                'timestamp': datetime.now().isoformat()
            })
        else:  # PNG
            import base64
            image_data = base64.b64decode(heatmap_base64)
            buf = io.BytesIO(image_data)
            buf.seek(0)
            return send_file(buf, mimetype='image/png')
    
    except Exception as e:
        logger.error(f"Fehler im /api/heatmap/band Endpoint: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/bands', methods=['GET'])
def get_bands():
    """Gibt verfügbare Frequenzbänder zurück"""
    bands = [
        {
            'name': band.name,
            'freq_start': band.freq_start,
            'freq_end': band.freq_end,
            'description': band.description
        }
        for band in RTLSDRScanner.COMMON_BANDS
    ]
    return jsonify({'bands': bands})


@app.route('/api/time-ranges', methods=['GET'])
def get_time_ranges():
    """Gibt verfügbare Zeiträume und Presets zurück"""
    return jsonify({
        'standard_ranges': ['1h', '6h', '24h', '7d', '30d'],
        'presets': {
            'today': 'Heute ab 00:00',
            'yesterday': 'Gestern (full day)',
            'day_before': 'Vorgestern (full day)',
            'this_week': 'Diese Woche ab Montag',
            'last_week': 'Letzte Woche (Montag-Sonntag)',
            'this_month': 'Dieser Monat ab 1.'
        },
        'custom': 'Auch möglich: start_time=ISO-8601&end_time=ISO-8601'
    })


@app.route('/api/colormaps', methods=['GET'])
def get_colormaps():
    """Gibt verfügbare Colormaps zurück"""
    colormaps = [
        'viridis', 'plasma', 'inferno', 'magma', 'cividis',
        'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
        'jet', 'hot', 'cool', 'spring', 'summer', 'autumn', 'winter'
    ]
    return jsonify({'colormaps': colormaps})


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health-Check Endpoint"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        }
        
        # Prüfe Heatmap Generator
        if heatmap_gen:
            health_status['heatmap_generator'] = 'connected'
        else:
            health_status['heatmap_generator'] = 'disconnected'
        
        # Prüfe SQLite REST API
        try:
            sqlite_response = requests.get(f"{SQLITE_REST_URL}/health", timeout=2)
            if sqlite_response.status_code == 200:
                health_status['sqlite_rest_api'] = 'healthy'
            else:
                health_status['sqlite_rest_api'] = 'unhealthy'
                health_status['status'] = 'degraded'
        except:
            health_status['sqlite_rest_api'] = 'unavailable'
            health_status['status'] = 'degraded'
        
        # Prüfe Scanner
        scanners_status = []
        if rtl_scanner:
            scanners_status.append('rtl-sdr')
        
        if scanners_status:
            health_status['scanners'] = scanners_status
        else:
            health_status['scanners'] = 'none_initialized'
            health_status['status'] = 'degraded'
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health-Check Fehler: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503


@app.errorhandler(404)
def not_found(e):
    """404 Error Handler"""
    return jsonify({'status': 'error', 'message': 'Endpoint nicht gefunden'}), 404


@app.errorhandler(500)
def server_error(e):
    """500 Error Handler"""
    logger.error(f"Server Error: {e}", exc_info=True)
    return jsonify({'status': 'error', 'message': 'Interner Server-Fehler'}), 500


# ============================================================================
# Neue Frequenz-Scanner Endpoints
# ============================================================================

@app.route('/api/scan/status', methods=['GET'])
def get_scan_status():
    """Gibt Status des aktuellen Scans zurück"""
    global scan_in_progress, scan_results
    
    return jsonify({
        'scanning': scan_in_progress,
        'has_results': scan_results is not None,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/scan/start', methods=['POST'])
def start_frequency_scan():
    """
    Startet einen Frequenzbereich-Scan mit allen verfügbaren Scannern
    
    Optional JSON Body:
    {
        "quick": true/false,  // Schneller Scan (Standard-Bänder)
        "custom_bands": [     // Custom Frequenzbänder
            {"name": "Custom 1", "freq_start": 100, "freq_end": 200}
        ]
    }
    """
    global scan_in_progress, scan_results, rtl_scanner
    
    available_scanners = []
    if rtl_scanner:
        available_scanners.append('rtl')
    
    if not available_scanners:
        return jsonify({
            'status': 'error',
            'message': 'Keine Scanner verfügbar'
        }), 503
    
    with scan_lock:
        if scan_in_progress:
            return jsonify({
                'status': 'error',
                'message': 'Ein Scan läuft bereits'
            }), 409
        
        scan_in_progress = True
    
    # Parse Request Data VOR dem Threading
    data = request.get_json() or {}
    quick_scan = data.get('quick', True)
    
    def run_scan():
        """Führe Scan im Background aus"""
        global scan_results, scan_in_progress, rtl_scanner
        
        try:
            logger.info("Starte Frequenzbereich-Scan mit allen verfügbaren Scannern...")
            
            all_results = []
            
            # Scanne mit RTL-SDR
            if rtl_scanner:
                logger.info("📡 Manuell: Scanne mit RTL-SDR...")
                if quick_scan:
                    rtl_results = rtl_scanner.find_active_bands()
                else:
                    rtl_results = rtl_scanner.scan_all_bands()
                if rtl_results:
                    write_scan_to_sqlite(rtl_results, receiver='rtl')
                    all_results.extend(rtl_results)
                    logger.info(f"✅ RTL-SDR: {len(rtl_results)} Bänder gescannt")
            
            if not all_results:
                logger.warning("Keine Scans erfolgreich")
                return
            
            # Analysiere alle Ergebnisse
            analysis = FrequencyAnalyzer.recommend_bands(all_results)
            
            # Konvertiere Results zu dictionaries und speichere GLOBAL
            scan_data = [r.to_dict() for r in all_results]
            scan_data = [r.to_dict() for r in results]
            
            # Weise global Variable zu
            globals()['scan_results'] = {
                'scan_data': scan_data,
                'analysis': analysis,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Scan abgeschlossen: {len(results)} Bänder gescannt")
        
        except Exception as e:
            logger.error(f"Fehler während des Scans: {e}", exc_info=True)
            globals()['scan_results'] = {
                'status': 'error',
                'message': str(e)
            }
        finally:
            with scan_lock:
                scan_in_progress = False
    
    # Starte Scan im Background
    scan_thread = threading.Thread(target=run_scan)
    scan_thread.daemon = True
    scan_thread.start()
    
    return jsonify({
        'status': 'started',
        'message': 'Frequenz-Scan gestartet...',
        'timestamp': datetime.now().isoformat()
    }), 202


@app.route('/api/scan/results', methods=['GET'])
def get_scan_results():
    """Gibt Scan-Ergebnisse zurück"""
    global scan_results
    
    if scan_results is None:
        return jsonify({
            'status': 'no_data',
            'message': 'Keine Scan-Ergebnisse verfügbar. Führe zuerst einen Scan durch.'
        }), 404
    
    if 'status' in scan_results and scan_results.get('status') == 'error':
        return jsonify(scan_results), 500
    
    return jsonify({
        'status': 'success',
        'data': scan_results
    })


@app.route('/api/scan/visualization', methods=['GET'])
def get_scan_visualization():
    """
    Gibt Visualisierung der Scan-Ergebnisse zurück
    
    Query Parameter:
    - format: 'overview' (Standard), 'spectrum', oder 'both'
    """
    global scan_results
    
    if scan_results is None or 'scan_data' not in scan_results:
        return jsonify({
            'status': 'error',
            'message': 'Keine Scan-Ergebnisse verfügbar'
        }), 404
    
    try:
        format_type = request.args.get('format', 'overview')
        
        # Rekonstruiere ScanResult Objekte (einfach für Visualisierung)
        from frequency_scanner import ScanResult, FrequencyBand
        
        scan_data = scan_results['scan_data']
        results = []
        
        for item in scan_data:
            band = FrequencyBand(
                name=item['band']['name'],
                freq_start=item['band']['freq_start'],
                freq_end=item['band']['freq_end'],
                description=item['band'].get('description', '')
            )
            
            result = ScanResult(
                band=band,
                avg_power=item['avg_power'],
                peak_power=item['peak_power'],
                noise_floor=item['noise_floor'],
                signal_to_noise=item['signal_to_noise'],
                active=item['active'],
                activity_percentage=item['activity_percentage'],
                num_peaks=item['num_peaks'],
                scan_time=item['scan_time'],
                timestamp=item.get('timestamp')
            )
            results.append(result)
        
        visualizations = {}
        
        if format_type in ['overview', 'both']:
            buf = SpectrumAnalyzer.plot_scan_results(results)
            if buf:
                visualizations['overview'] = SpectrumAnalyzer.results_to_base64(buf)
        
        if format_type in ['spectrum', 'both']:
            buf = SpectrumAnalyzer.plot_frequency_spectrum(results)
            if buf:
                visualizations['spectrum'] = SpectrumAnalyzer.results_to_base64(buf)
        
        return jsonify({
            'status': 'success',
            'visualizations': visualizations,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Fehler bei Visualisierung: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/scan/recommendations', methods=['GET'])
def get_scan_recommendations():
    """Gibt empfohlene Frequenzbereiche basierend auf letztem Scan zurück"""
    global scan_results
    
    if scan_results is None or 'analysis' not in scan_results:
        return jsonify({
            'status': 'error',
            'message': 'Keine Scan-Ergebnisse für Empfehlungen verfügbar'
        }), 404
    
    try:
        analysis = scan_results['analysis']
        recommendations = analysis.get('recommendations', [])
        
        # Sortiere nach Priorität
        recommendations.sort(key=lambda x: x.get('rank', 999))
        
        return jsonify({
            'status': 'success',
            'summary': analysis.get('summary'),
            'recommendations': recommendations,
            'total_scanned': analysis.get('total_scanned'),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Fehler bei Empfehlungen: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================================
# Automatischer Scan-Scheduler
# ============================================================================

def get_monitored_bands():
    """Lese die zu überwachenden Frequenzbänder aus .env"""
    try:
        monitored_bands_str = os.getenv('MONITORED_BANDS', '4,5')  # Default: UHF IV+V
        band_indices = [int(x.strip()) for x in monitored_bands_str.split(',')]
        
        # Validiere: maximal 2 Bänder, gültige Indizes (0-8)
        if len(band_indices) > 2:
            logger.warning(f"Zu viele Bänder konfiguriert ({len(band_indices)}), nutze nur erste 2")
            band_indices = band_indices[:2]
        
        selected_bands = []
        for idx in band_indices:
            if 0 <= idx < len(RTLSDRScanner.COMMON_BANDS):
                selected_bands.append(RTLSDRScanner.COMMON_BANDS[idx])
            else:
                logger.warning(f"Ungültiger Band-Index: {idx}")
        
        if not selected_bands:
            logger.warning("Keine gültigen Bänder konfiguriert, verwende defaults (UHF IV+V)")
            selected_bands = [RTLSDRScanner.COMMON_BANDS[4], RTLSDRScanner.COMMON_BANDS[5]]
        
        logger.info(f"Überwache Frequenzbänder: {', '.join([b.name for b in selected_bands])}")
        return selected_bands
    except Exception as e:
        logger.error(f"Fehler beim Lesen von MONITORED_BANDS: {e}")
        return [RTLSDRScanner.COMMON_BANDS[4], RTLSDRScanner.COMMON_BANDS[5]]

def run_automatic_scan():
    """Führe automatischen Scan mit beiden verfügbaren Scannern aus"""
    global scan_in_progress, scan_results, rtl_scanner
    
    # Verhindere parallele Scans
    with scan_lock:
        if scan_in_progress:
            logger.info("Scan bereits in Ausführung - überspringe automatischen Scan")
            return
        scan_in_progress = True
    
    try:
        logger.info("🔄 Starte automatischen Frequenzbereich-Scan...")
        
        # Hole die zu überwachenden Bänder
        monitored_bands = get_monitored_bands()
        
        all_results = []
        
        # Scanne mit RTL-SDR
        if rtl_scanner:
            logger.info("📡 Scanne mit RTL-SDR...")
            rtl_results = []
            for band in monitored_bands:
                result = rtl_scanner.scan_band(band)
                if result:
                    rtl_results.append(result)
                    logger.info(f"✅ RTL-SDR Scan für {band.name} abgeschlossen")
            if rtl_results:
                write_scan_to_sqlite(rtl_results, receiver='rtl')
                all_results.extend(rtl_results)
        
        if not all_results:
            logger.warning("Keine Scans erfolgreich - keine Daten gespeichert")
            return
        
        # Analysiere alle Ergebnisse zusammen
        analysis = FrequencyAnalyzer.recommend_bands(all_results)
        
        # Speichere im Speicher
        scan_data = [r.to_dict() for r in all_results]
        globals()['scan_results'] = {
            'scan_data': scan_data,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Automatischer Scan abgeschlossen: {len(all_results)} Bänder gescannt ({len(rtl_results) if rtl_scanner else 0} RTL)")
    
    except Exception as e:
        logger.error(f"❌ Fehler während automatischem Scan: {e}", exc_info=True)
        globals()['scan_results'] = {
            'status': 'error',
            'message': str(e)
        }
    finally:
        with scan_lock:
            scan_in_progress = False


def init_scheduler():
    """Initialisiere Background-Scheduler für kontinuierliche Scans"""
    try:
        scheduler = BackgroundScheduler()
        
        # Scan-Intervall in Sekunden (neu: SCAN_INTERVAL_SECONDS statt SCAN_INTERVAL_MINUTES)
        scan_interval_seconds = int(os.getenv('SCAN_INTERVAL_SECONDS', 180))
        scan_interval_minutes = scan_interval_seconds / 60.0
        
        scheduler.add_job(
            run_automatic_scan,
            'interval',
            seconds=scan_interval_seconds,
            id='frequency_scan',
            name='Automatischer Frequenzbereich-Scan',
            replace_existing=True,
            max_instances=1
        )
        
        scheduler.start()
        logger.info(f"✅ Scheduler gestartet - Scans alle {scan_interval_minutes:.1f} Minuten")
        
        # Starte sofort ersten Scan
        logger.info("Starte initialen Scan...")
        run_automatic_scan()
        
        return scheduler
    except Exception as e:
        logger.error(f"Fehler beim Starten des Schedulers: {e}")
        return None


if __name__ == '__main__':
    init_heatmap_generator()
    init_scanner()
    scheduler = init_scheduler()
    
    # =============================================================
    # Durchschnittlicher Spektralpegel Plot (API)
    # =============================================================
    @app.route('/api/avgpower', methods=['GET'])
    def get_avg_power_plot():
        """
        Gibt einen Plot des durchschnittlichen Spektralpegels (dB) für einen Zeitraum zurück.
        Query-Parameter:
          - time_range: '1h', '6h', '24h' (Standard: '1h')
          - receiver: 'rtl' oder None für alle (Standard: None)
        """
        try:
            time_range = request.args.get('time_range', '24h')
            receiver = request.args.get('receiver', None)
            
            # Hole historische Daten aus der Datenbank via Heatmap-Generator
            spektrum_data, timestamps, frequencies = heatmap_gen.get_frequency_data(
                time_range=time_range, 
                receiver=receiver
            )
            
            if spektrum_data is None or len(spektrum_data) == 0:
                return jsonify({
                    "status": "error", 
                    "message": "Keine Daten für den gewählten Zeitraum verfügbar"
                }), 404
            
            # Berechne Durchschnittspegel über alle Zeitpunkte
            avg_power = np.mean(spektrum_data, axis=0)
            
            # Erstelle Plot
            fig, ax = plt.subplots(figsize=(12, 6))
            
            ax.plot(frequencies, avg_power, 'b-', linewidth=2, alpha=0.8, label='Durchschnitt')
            ax.fill_between(frequencies, avg_power, alpha=0.3, color='blue')
            
            ax.set_xlabel('Frequenz (MHz)', fontsize=12)
            ax.set_ylabel('Durchschnittsleistung (dB)', fontsize=12)
            ax.set_title(f'Durchschnittlicher Spektralpegel - {time_range.upper()}', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # X-Achse formatieren
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}'))
            
            # Layout optimieren
            plt.tight_layout()
            
            # In Base64 konvertieren
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
            
            return jsonify({
                "status": "success",
                "image": img_base64,
                "time_range": time_range,
                "receiver": receiver or "all",
                "data_points": len(frequencies),
                "time_samples": len(timestamps)
            })
            
        except Exception as e:
            logger.error(f'Fehler bei avgpower-Plot: {e}', exc_info=True)
            return jsonify({
                "status": "error", 
                "message": f"Interner Fehler: {str(e)}"
            }), 500
    
    # Starte Flask App
    debug_mode = os.getenv('FLASK_DEBUG', 'False') == 'True'
    port = int(os.getenv('FLASK_PORT', 5000))
    
    logger.info(f"Starte Flask Server auf Port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

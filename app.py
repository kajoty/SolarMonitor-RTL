"""
Flask REST API für RTL-SDR Frequenz-Monitoring mit FFT Heatmaps
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
scanner = None
scan_results = None
scan_in_progress = False
scan_lock = threading.Lock()

# InfluxDB Client
influxdb_client = None


def init_influxdb():
    """Initialisiere InfluxDB Verbindung"""
    global influxdb_client
    try:
        from influxdb import InfluxDBClient
        
        host = os.getenv('INFLUXDB_HOST', 'localhost')
        port = int(os.getenv('INFLUXDB_PORT', 8086))
        user = os.getenv('INFLUXDB_USER', 'admin')
        password = os.getenv('INFLUXDB_PASSWORD', 'admin')
        database = os.getenv('INFLUXDB_DATABASE', 'rtl_monitor')
        
        influxdb_client = InfluxDBClient(
            host=host,
            port=port,
            username=user,
            password=password,
            database=database
        )
        
        # Versuche zu verbinden
        influxdb_client.ping()
        logger.info(f"InfluxDB verbunden: {host}:{port}/{database}")
        return True
    except Exception as e:
        logger.warning(f"InfluxDB Verbindung fehlgeschlagen: {e}")
        influxdb_client = None
        return False


def write_scan_to_influxdb(results):
    """Schreibe Scan-Ergebnisse in InfluxDB"""
    if not influxdb_client:
        logger.debug("InfluxDB nicht verfügbar - überspringe Speicherung")
        return False
    
    try:
        points = []
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        for result in results:
            # Schreibe Gesamtband-Statistik als frequency_scan
            point_scan = {
                "measurement": "frequency_scan",
                "tags": {
                    "band_name": result.band.name,
                    "active": str(result.active)
                },
                "fields": {
                    "freq_start": float(result.band.freq_start),
                    "freq_end": float(result.band.freq_end),
                    "avg_power": float(result.avg_power),
                    "peak_power": float(result.peak_power),
                    "noise_floor": float(result.noise_floor),
                    "signal_to_noise": float(result.signal_to_noise),
                    "activity_percentage": float(result.activity_percentage),
                    "num_peaks": int(result.num_peaks),
                    "scan_time": float(result.scan_time)
                },
                "time": timestamp
            }
            points.append(point_scan)
            
            # Schreibe auch Spektrum-Daten für Heatmap-Generator
            # Nutze die Mittenfrequenz des Bandes
            freq_center = (result.band.freq_start + result.band.freq_end) / 2
            point_spectrum = {
                "measurement": "frequency_spectrum",
                "tags": {
                    "band_name": result.band.name
                },
                "fields": {
                    "frequency": float(freq_center),  # Frequenz als Field
                    "power": float(result.avg_power)  # Durchschnittliche Leistung
                },
                "time": timestamp
            }
            points.append(point_spectrum)
        
        if points:
            influxdb_client.write_points(points)
            logger.info(f"Geschrieben: {len(points)} Scan-Ergebnisse in InfluxDB")
            return True
    except Exception as e:
        logger.error(f"Fehler beim Schreiben in InfluxDB: {e}")
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
    """Initialisiert den RTL-SDR Scanner beim Start"""
    global scanner
    try:
        scanner = create_scanner_from_env()
        logger.info("RTL-SDR Scanner erfolgreich initialisiert")
    except Exception as e:
        logger.warning(f"RTL-SDR Scanner nicht verfügbar: {e}")
        scanner = None


@app.before_request
def before_request():
    """Initialisiere Generatoren beim ersten Request"""
    global heatmap_gen, scanner, influxdb_client
    if heatmap_gen is None:
        init_heatmap_generator()
    if scanner is None:
        init_scanner()
    if influxdb_client is None:
        init_influxdb()


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
    REST Endpoint für Heatmap-Daten
    
    Query Parameter:
    - time_range: '1h', '6h', '24h', '7d', '30d' (default: '24h')
    - freq_start: Startfrequenz in MHz (optional)
    - freq_end: Endfrequenz in MHz (optional)
    - cmap: Colormap ('viridis', 'jet', 'plasma', etc.) (default: 'viridis')
    - format: 'png' oder 'json' (default: 'png')
    
    Response:
    - PNG: Direktes Bild
    - JSON: {
        "status": "success" | "error",
        "time_range": "...",
        "freq_start": ...,
        "freq_end": ...,
        "data": "base64_encoded_image",
        "message": "..."
    }
    """
    try:
        # Parameter auslesen
        time_range = request.args.get('time_range', '24h')
        freq_start = request.args.get('freq_start', type=float, default=None)
        freq_end = request.args.get('freq_end', type=float, default=None)
        cmap = request.args.get('cmap', 'viridis')
        response_format = request.args.get('format', 'png')
        
        # Validiere Parameter
        valid_ranges = ['1h', '6h', '24h', '7d', '30d']
        if time_range not in valid_ranges:
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
        heatmap_base64 = heatmap_gen.get_heatmap_data(
            time_range=time_range,
            freq_start=freq_start,
            freq_end=freq_end,
            cmap=cmap
        )
        
        if heatmap_base64 is None:
            return jsonify({
                'status': 'no_data',
                'message': 'Keine Daten verfügbar. Bitte später erneut versuchen.',
                'time_range': time_range,
                'timestamp': datetime.now().isoformat()
            }), 202
        
        if response_format == 'json':
            return jsonify({
                'status': 'success',
                'time_range': time_range,
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
    """Gibt verfügbare Zeiträume zurück"""
    return jsonify({
        'time_ranges': list(heatmap_gen.TIME_RANGES.keys()) if heatmap_gen else ['1h', '6h', '24h', '7d', '30d']
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
        if heatmap_gen and heatmap_gen.client:
            return jsonify({
                'status': 'healthy',
                'influxdb_connected': True,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'degraded',
                'influxdb_connected': False,
                'message': 'InfluxDB nicht verbunden',
                'timestamp': datetime.now().isoformat()
            }), 503
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
    Startet einen Frequenzbereich-Scan
    
    Optional JSON Body:
    {
        "quick": true/false,  // Schneller Scan (Standard-Bänder)
        "custom_bands": [     // Custom Frequenzbänder
            {"name": "Custom 1", "freq_start": 100, "freq_end": 200}
        ]
    }
    """
    global scan_in_progress, scan_results, scanner
    
    if not scanner:
        return jsonify({
            'status': 'error',
            'message': 'RTL-SDR Scanner nicht verfügbar'
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
        global scan_results, scan_in_progress
        
        try:
            logger.info("Starte Frequenzbereich-Scan...")
            
            # Führe Scan durch
            if quick_scan:
                results = scanner.find_active_bands()
            else:
                results = scanner.scan_all_bands()
            
            # Analysiere Ergebnisse
            analysis = FrequencyAnalyzer.recommend_bands(results)
            
            # Schreibe Ergebnisse in InfluxDB
            write_scan_to_influxdb(results)
            
            # Konvertiere Results zu dictionaries und speichere GLOBAL
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
    """Führe automatischen Scan aus (wird von Scheduler aufgerufen)"""
    global scan_in_progress, scan_results, scanner
    
    # Verhindere parallele Scans
    with scan_lock:
        if scan_in_progress:
            logger.info("Scan bereits in Ausführung - überspringe automatischen Scan")
            return
        scan_in_progress = True
    
    try:
        logger.info("🔄 Starte automatischen Frequenzbereich-Scan...")
        
        if not scanner:
            logger.warning("Scanner nicht verfügbar - überspringe Scan")
            return
        
        # Hole nur die konfigurierten Bänder
        monitored_bands = get_monitored_bands()
        
        # Scanne nur die überwachten Bänder
        results = []
        for band in monitored_bands:
            result = scanner.scan_band(band)
            if result:
                results.append(result)
                logger.info(f"✅ Scan für {band.name} abgeschlossen")
        
        # Analysiere Ergebnisse
        analysis = FrequencyAnalyzer.recommend_bands(results)
        
        # Schreibe Ergebnisse in InfluxDB
        write_scan_to_influxdb(results)
        
        # Speichere im Speicher
        scan_data = [r.to_dict() for r in results]
        globals()['scan_results'] = {
            'scan_data': scan_data,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Automatischer Scan abgeschlossen: {len(results)} Bänder gescannt")
    
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
    init_influxdb()
    scheduler = init_scheduler()
    
    # Starte Flask App
    debug_mode = os.getenv('FLASK_DEBUG', 'False') == 'True'
    port = int(os.getenv('FLASK_PORT', 5000))
    
    logger.info(f"Starte Flask Server auf Port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

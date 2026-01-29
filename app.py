import os
import json
import pandas as pd
from sqlalchemy import create_engine
import plotly.graph_objects as go
import plotly.utils
from flask import Flask, render_template_string, request, send_from_directory
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# Verzeichnis für die generierten Bilder (Heatmaps/Plots)
OUTPUT_DIR = "recordings"

# [cite_start]Datenbank-Konfiguration mit Port 5433 [cite: 1]
db_port = os.getenv('POSTGRES_PORT', '5433') 
db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{db_port}/{os.getenv('POSTGRES_DB')}"
engine = create_engine(db_url)

# Route um die statischen Bilder aus dem recordings-Ordner zu servieren
@app.route('/recordings/<path:filename>')
def serve_recordings(filename):
    return send_from_directory(OUTPUT_DIR, filename)

def get_stats():
    """Holt aktuelle Max/Avg Werte für die Info-Boxen."""
    try:
        query = """
            SELECT band_name, MAX(power) as max_p, AVG(power) as avg_p 
            FROM frequency_spectrum 
            WHERE timestamp > NOW() - INTERVAL '5 minutes'
            GROUP BY band_name
        """
        df = pd.read_sql(query, engine)
        stats = {}
        for _, row in df.iterrows():
            stats[row['band_name']] = {
                'max': round(row['max_p'], 1),
                'avg': round(row['avg_p'], 1)
            }
        return stats
    except Exception as e:
        print(f"Fehler bei Stats-Abfrage: {e}")
        return {}

# Modernes HTML Template basierend auf der solar.html
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solar Monitor Pro - Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .glass { background: rgba(17, 24, 39, 0.8); backdrop-filter: blur(12px); }
        body { background: #000; }
    </style>
</head>
<body class="text-gray-100 min-h-screen p-4 flex flex-col items-center gap-6">

    <div class="w-full max-w-5xl p-6 glass rounded-3xl border border-gray-800 shadow-2xl">
        <div class="flex justify-between items-center mb-6">
            <h1 class="text-2xl font-bold text-orange-500">Solar Monitor <span class="text-gray-500 font-light italic">Live</span></h1>
            <div class="flex items-center gap-2">
                <span class="text-xs text-gray-500 font-mono">SYSTEM ONLINE</span>
                <div class="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            <div class="bg-gray-900/50 p-4 rounded-xl border border-gray-800 relative overflow-hidden">
                <div class="absolute left-0 top-0 bottom-0 w-1 bg-blue-500"></div>
                <h3 class="text-xs font-bold text-blue-400 uppercase mb-3 ml-2">FM Referenz (UKW)</h3>
                <div class="grid grid-cols-2 gap-4 ml-2">
                    <div><p class="text-[10px] text-gray-500 uppercase">Peak</p><div class="text-xl font-mono">{{ stats.get('Diagnostic_FM', {}).get('max', '--') }} dB</div></div>
                    <div><p class="text-[10px] text-gray-500 uppercase">Avg</p><div class="text-xl font-mono text-gray-400">{{ stats.get('Diagnostic_FM', {}).get('avg', '--') }} dB</div></div>
                </div>
            </div>
            <div class="bg-gray-900/50 p-4 rounded-xl border border-gray-800 relative overflow-hidden">
                <div class="absolute left-0 top-0 bottom-0 w-1 bg-orange-500"></div>
                <h3 class="text-xs font-bold text-orange-400 uppercase mb-3 ml-2">Solar Radio (26-80 MHz)</h3>
                <div class="grid grid-cols-2 gap-4 ml-2">
                    <div><p class="text-[10px] text-gray-500 uppercase">Max</p><div class="text-xl font-mono">{{ stats.get('Solar_Radio', {}).get('max', '--') }} dB</div></div>
                    <div><p class="text-[10px] text-gray-500 uppercase">Floor</p><div class="text-xl font-mono text-gray-400">{{ stats.get('Solar_Radio', {}).get('avg', '--') }} dB</div></div>
                </div>
            </div>
        </div>

        <div class="mb-12">
            <h2 class="text-lg font-semibold uppercase tracking-wider text-blue-400 mb-6 border-b border-gray-800 pb-2">Spektrum Analyse</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                <div class="relative bg-black rounded-xl border border-gray-800 overflow-hidden">
                    <div class="absolute top-3 left-3 bg-orange-600/80 text-[10px] px-2 py-1 rounded font-bold z-10">VIEW: 1 STD SOLAR</div>
                    <img src="/recordings/latest_1h_Solar.png" class="w-full h-auto">
                </div>

                <div class="relative bg-black rounded-xl border border-gray-800 overflow-hidden">
                    <div class="absolute top-3 left-3 bg-orange-600/80 text-[10px] px-2 py-1 rounded font-bold z-10">VIEW: 6 STD SOLAR</div>
                    <img src="/recordings/latest_6h_Solar.png" class="w-full h-auto">
                </div>

                <div class="relative bg-black rounded-xl border border-gray-800 overflow-hidden md:col-span-2">
                    <div class="absolute top-3 left-3 bg-blue-600/80 text-[10px] px-2 py-1 rounded font-bold z-10">VIEW: 48 STD DYNAMIK VERLAUF</div>
                    <img src="/recordings/signal_solar_dynamic_48h.png" class="w-full h-auto">
                </div>

                <div class="relative bg-black rounded-xl border border-gray-800 overflow-hidden md:col-span-2">
                    <div class="absolute top-3 left-3 bg-orange-600/80 text-[10px] px-2 py-1 rounded font-bold z-10">VIEW: 24 STD SOLAR WATERFALL</div>
                    <img src="/recordings/latest_24h_Solar.png" class="w-full h-auto">
                </div>
            </div>
        </div>

        <div class="text-center text-gray-600 text-[10px] font-mono border-t border-gray-800 pt-4">
            LETZTES UPDATE: {{ now }} | AUTO-REFRESH JEDE MINUTE
        </div>
    </div>

    <script>
        // Automatischer Reload alle 60 Sekunden
        setTimeout(() => { location.reload(); }, 60000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    current_stats = get_stats()
    timestamp = datetime.now().strftime("%H:%M:%S")
    return render_template_string(HTML_TEMPLATE, stats=current_stats, now=timestamp)

if __name__ == '__main__':
    # Sicherstellen, dass der recordings Ordner existiert
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    app.run(host='0.0.0.0', port=5001)
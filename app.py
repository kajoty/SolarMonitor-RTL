import os
import json
import pandas as pd
from sqlalchemy import create_engine
import plotly.graph_objects as go
import plotly.utils
from flask import Flask, render_template_string, request
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}/{os.getenv('POSTGRES_DB')}"
engine = create_engine(db_url)

def get_data(hours=2, band="Solar_Radio"):
    try:
        # Filtert nun dynamisch nach dem gewünschten Band
        query = f"""
            SELECT timestamp, frequency, power 
            FROM frequency_spectrum 
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
            AND band_name = '{band}'
            ORDER BY timestamp DESC
        """
        df = pd.read_sql(query, engine)
        
        if not df.empty:
            df['frequency'] = df['frequency'].round(1)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            if hours > 6:
                all_times = sorted(df['timestamp'].unique())
                keep_times = all_times[::2] 
                df = df[df['timestamp'].isin(keep_times)]
                
        return df
    except Exception as e:
        print(f"DB Error: {e}")
        return pd.DataFrame()

def create_heatmap(df, title, colorscale='Inferno'):
    if df.empty:
        return None
    
    pivot_df = df.pivot_table(index='timestamp', columns='frequency', values='power', aggfunc='mean')
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values.tolist(),
        x=pivot_df.columns.tolist(), 
        y=pivot_df.index.tolist(),
        colorscale=colorscale,
        colorbar=dict(title="dB"),
        hovertemplate='Frequenz: %{x} MHz<br>Zeit: %{y}<br>Power: %{z} dB<extra></extra>'
    ))

    fig.update_layout(
        title=title,
        template="plotly_dark",
        xaxis=dict(title="Frequenz [MHz]", type='linear'),
        yaxis=dict(title="Zeit", type='date', autorange="reversed"),
        height=800
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

# Basis-Template für beide Seiten
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
    <head>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body { background:#111; color:white; font-family:sans-serif; margin:0; }
            .nav { padding: 15px; background: #222; display: flex; gap: 10px; border-bottom: 1px solid #444; align-items: center; }
            .nav-right { margin-left: auto; display: flex; gap: 10px; }
            button { padding: 8px 15px; cursor: pointer; background: #444; color: white; border: none; border-radius: 4px; }
            button:hover { background: #666; }
            button.active { background: #007bff; }
            .brand { font-weight: bold; color: #ff9800; margin-right: 20px; }
        </style>
    </head>
    <body>
        <div class="nav">
            <span class="brand">SolarMonitor</span>
            <button onclick="location.href='/?hours={{h}}'" class="{{'active' if mode=='solar' else ''}}">Solar-Daten</button>
            <button onclick="location.href='/diagnostic?hours={{h}}'" class="{{'active' if mode=='diag' else ''}}">System-Diagnose (UKW)</button>
            
            <div class="nav-right">
                <button onclick="location.href='?hours=1'">1h</button>
                <button onclick="location.href='?hours=6'">6h</button>
                <button onclick="location.href='?hours=24'">24h</button>
            </div>
        </div>
        {% if graphJSON %}
            <div id="chart"></div>
            <script>
                var graphs = {{ graphJSON | safe }};
                Plotly.newPlot('chart', graphs.data, graphs.layout, {responsive: true});
            </script>
        {% else %}
            <div style="padding: 50px; text-align: center;">
                <h2>Keine Daten für diesen Zeitraum gefunden.</h2>
                <p>Modus: {{ "Solar" if mode=='solar' else "Diagnose" }}</p>
            </div>
        {% endif %}
    </body>
</html>
"""

@app.route('/')
def index():
    hours = request.args.get('hours', default=2, type=int)
    df = get_data(hours, "Solar_Radio")
    graphJSON = create_heatmap(df, f"Solar-Spektrum (26-80 MHz) - Letzte {hours}h", 'Inferno')
    return render_template_string(HTML_TEMPLATE, graphJSON=graphJSON, h=hours, mode='solar')

@app.route('/diagnostic')
def diagnostic():
    hours = request.args.get('hours', default=2, type=int)
    df = get_data(hours, "Diagnostic_FM")
    # Diagnostic bekommt eine andere Farbskala (Viridis) zur optischen Trennung
    graphJSON = create_heatmap(df, f"Hardware-Check (UKW Referenz) - Letzte {hours}h", 'Viridis')
    return render_template_string(HTML_TEMPLATE, graphJSON=graphJSON, h=hours, mode='diag')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
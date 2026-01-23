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

def get_data(hours=2):
    try:
        # Dynamisches Intervall basierend auf User-Wahl
        query = f"""
            SELECT timestamp, frequency, power 
            FROM frequency_spectrum 
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
            ORDER BY timestamp DESC
        """
        df = pd.read_sql(query, engine)
        
        if not df.empty:
            df['frequency'] = df['frequency'].round(1)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # DOWN-SAMPLING für Performance bei großen Zeiträumen
            # Wenn wir mehr als 6h laden, nehmen wir nur jeden 2. Zeitstempel
            if hours > 6:
                all_times = sorted(df['timestamp'].unique())
                keep_times = all_times[::2] 
                df = df[df['timestamp'].isin(keep_times)]
                
        return df
    except Exception as e:
        print(f"DB Error: {e}")
        return pd.DataFrame()

@app.route('/')
def index():
    hours = request.args.get('hours', default=2, type=int)
    df = get_data(hours)
    
    if df.empty:
        return f"<h1>Keine Daten für {hours}h gefunden.</h1><a href='/?hours=2'>Zurück</a>"

    try:
        # 1. Daten runden für sauberes Gitter
        df['frequency'] = df['frequency'].round(1)
        
        # 2. Pivotieren
        pivot_df = df.pivot_table(index='timestamp', columns='frequency', values='power', aggfunc='mean')
        
        # 3. Achsen-Werte explizit vorbereiten
        # Wir nutzen die echten Floats für X und echte Zeitobjekte für Y
        x_values = pivot_df.columns.tolist()
        y_values = pivot_df.index.tolist()
        z_values = pivot_df.values.tolist()

        fig = go.Figure(data=go.Heatmap(
            z=z_values,
            x=x_values, 
            y=y_values,
            colorscale='Viridis',
            zmin=-50, zmax=-20,
            colorbar=dict(title="dB"),
            hovertemplate='Frequenz: %{x} MHz<br>Zeit: %{y}<br>Power: %{z} dB<extra></extra>'
        ))

        fig.update_layout(
            title=f"SolarMonitor RTL - Letzte {hours} Stunden",
            template="plotly_dark",
            # HIER ZWINGEN WIR DIE ACHSEN-TYPEN:
            xaxis=dict(
                title="Frequenz [MHz]",
                type='linear', 
                range=[26, 80],
                dtick=5
            ),
            yaxis=dict(
                title="Zeit",
                type='date', # Plotly erkennt die Zeitobjekte jetzt als Datum
                autorange="reversed"
            ),
            height=800
        )
        
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
    except Exception as e:
        print(f"Plot Error: {e}")
        return f"<h1>Fehler: {e}</h1>"

    return render_template_string("""
        <!DOCTYPE html>
        <html>
            <head>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <style>
                    body { background:#111; color:white; font-family:sans-serif; margin:0; }
                    .nav { padding: 15px; background: #222; display: flex; gap: 10px; border-bottom: 1px solid #444; }
                    button { padding: 8px 15px; cursor: pointer; background: #444; color: white; border: none; border-radius: 4px; }
                    button.active { background: #007bff; }
                </style>
            </head>
            <body>
                <div class="nav">
                    <button onclick="location.href='/?hours=1'">1h</button>
                    <button onclick="location.href='/?hours=3'">3h</button>
                    <button onclick="location.href='/?hours=6'">6h</button>
                    <button onclick="location.href='/?hours=24'">24h</button>
                </div>
                <div id="chart"></div>
                <script>
                    var graphs = {{ graphJSON | safe }};
                    Plotly.newPlot('chart', graphs.data, graphs.layout);
                </script>
            </body>
        </html>
    """, graphJSON=graphJSON)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
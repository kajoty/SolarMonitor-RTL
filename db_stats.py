import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_db():
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            database=os.getenv('POSTGRES_DB'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD')
        )
        cur = conn.cursor()

        # Jetzt einfache Abfrage, da die Typen in der DB stimmen
        query = """
        SELECT 
            MIN(frequency), 
            MAX(frequency), 
            COUNT(*), 
            MAX(timestamp)
        FROM frequency_spectrum 
        WHERE timestamp > NOW() - INTERVAL '10 minutes';
        """
        
        cur.execute(query)
        result = cur.fetchone()

        print("\n=============================================")
        print("📡 SolarMonitor-RTL: Finaler Datenbank-Check")
        print("=============================================")
        
        if result and result[2] > 0:
            min_f, max_f, count, last_ts = result
            print(f"Letzter Scan:      {last_ts}")
            print(f"Frequenzbereich:   {min_f:.2f} MHz - {max_f:.2f} MHz")
            print(f"Datenpunkte (10m): {count}")
            
            env_end = float(os.getenv('SOLAR_FREQ_END', 80.0))
            print("-" * 45)
            if max_f >= (env_end - 0.5):
                print("✅ ERFOLG: Voller Frequenzbereich (26-80 MHz) korrekt gespeichert!")
            else:
                print(f"❌ FEHLER: Datenbank stoppt bei {max_f:.2f} MHz.")
        else:
            print("❌ Keine Daten gefunden.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    check_db()
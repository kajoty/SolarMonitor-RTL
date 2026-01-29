import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Konfiguration laden
load_dotenv()

Base = declarative_base()

# Definition der Tabellenstruktur (Schema)
class FrequencySpectrum(Base):
    __tablename__ = 'frequency_spectrum'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    band_name = Column(Text, nullable=False)
    frequency = Column(Float, nullable=False)
    power = Column(Float, nullable=False)
    receiver = Column(Text, nullable=True)
    applied_gain = Column(Float, nullable=True)
    sun_phase = Column(String(20), nullable=True)
    created_at = Column(DateTime, server_default=None) # Wird durch DB oder App gesetzt

def setup_database():
    # Verbindungsparameter aus .env
    host = os.getenv('POSTGRES_HOST')
    port = os.getenv('POSTGRES_PORT', '5433')
    db = os.getenv('POSTGRES_DB')
    user = os.getenv('POSTGRES_USER')
    pw = os.getenv('POSTGRES_PASSWORD')

    db_url = f"postgresql://{user}:{pw}@{host}:{port}/{db}"
    
    try:
        engine = create_engine(db_url)
        inspector = inspect(engine)
        
        # Prüfen, ob Tabelle bereits existiert
        if not inspector.has_table('frequency_spectrum'):
            print(f"--- Datenbank-Setup ---")
            print(f"Tabelle 'frequency_spectrum' wird auf {host}:{port} erstellt...")
            
            # Erstellt alle Tabellen, die in 'Base' definiert sind
            Base.metadata.create_all(engine)
            
            print("✅ Tabelle erfolgreich angelegt!")
        else:
            print(f"ℹ️ Tabelle 'frequency_spectrum' existiert bereits auf {host}:{port}.")
            
            # Optional: Hier könnte man noch prüfen, ob einzelne Spalten fehlen (Migration)
            columns = [c['name'] for c in inspector.get_columns('frequency_spectrum')]
            if 'applied_gain' not in columns:
                print("⚠️ Warnung: 'applied_gain' fehlt. Bitte Schema aktualisieren!")

    except Exception as e:
        print(f"❌ Fehler beim Datenbank-Setup: {e}")

if __name__ == "__main__":
    setup_database()
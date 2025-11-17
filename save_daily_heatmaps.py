#!/usr/bin/env python3
"""
Tägliche Heatmap Archivierung für Solar Radio Monitoring
Speichert automatisch Heatmaps pro Tag mit Timestamp-basiertem Naming

Verwendung:
    python3 save_daily_heatmaps.py [--output-dir ./heatmaps] [--band 'Solar Radio']
    
Oder als Cronjob (täglich um 23:55):
    55 23 * * * cd /home/pi/Projekte/solarmonitor/SolarMonitor-RTL && python3 save_daily_heatmaps.py
"""

import argparse
import logging
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyHeatmapArchiver:
    """Speichert tägliche Heatmaps und Metadaten"""
    
    def __init__(self, flask_url='http://localhost:5000', output_dir='./heatmaps'):
        """
        Args:
            flask_url: Flask API URL
            output_dir: Verzeichnis zum Speichern der Heatmaps
        """
        self.flask_url = flask_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Ausgabeverzeichnis: {self.output_dir.absolute()}")
    
    def get_heatmap_for_date(self, target_date: datetime, band_name: str = 'Solar Radio', 
                           cmap: str = 'viridis') -> Optional[bytes]:
        """
        Lädt Heatmap für ein bestimmtes Datum
        
        Args:
            target_date: Datum (nur Datum wird verwendet, Zeit wird ignoriert)
            band_name: Band-Name
            cmap: Colormap
            
        Returns:
            PNG-Daten oder None bei Fehler
        """
        # Berechne Anfang und Ende des Tages
        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1) - timedelta(seconds=1)
        
        try:
            logger.info(f"Lade Heatmap für {day_start.strftime('%Y-%m-%d')}...")
            
            response = requests.get(
                f"{self.flask_url}/api/heatmap",
                params={
                    'band_name': band_name,
                    'start_time': day_start.isoformat(),
                    'end_time': day_end.isoformat(),
                    'cmap': cmap,
                    'format': 'png'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                # Überprüfe ob es wirklich ein PNG ist
                if response.headers.get('Content-Type', '').startswith('image'):
                    logger.info(f"  ✅ Heatmap geladen ({len(response.content)} bytes)")
                    return response.content
                else:
                    # Könnte JSON Error sein
                    error_data = response.json()
                    logger.warning(f"  ⚠️  {error_data.get('message', 'Keine Daten')}")
                    return None
            else:
                logger.error(f"  ❌ HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"  ❌ Fehler: {e}")
            return None
    
    def get_spectrum_stats(self, target_date: datetime, band_name: str = 'Solar Radio') -> Optional[dict]:
        """
        Lädt Spektrum-Statistiken für ein Datum
        
        Returns:
            Dict mit Statistiken oder None
        """
        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1) - timedelta(seconds=1)
        
        try:
            response = requests.get(
                f"{self.flask_url}/api/heatmap",
                params={
                    'band_name': band_name,
                    'start_time': day_start.isoformat(),
                    'end_time': day_end.isoformat(),
                    'format': 'json'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Fehler beim Laden der Statistiken: {e}")
            return None
    
    def save_heatmap(self, target_date: datetime, band_name: str = 'Solar Radio',
                    cmap: str = 'viridis') -> bool:
        """
        Speichert Heatmap und Metadaten für ein Datum
        
        Args:
            target_date: Datum
            band_name: Band-Name
            cmap: Colormap
            
        Returns:
            True wenn erfolgreich gespeichert
        """
        date_str = target_date.strftime('%Y-%m-%d')
        
        # Erstelle Unterverzeichnis für das Datum
        day_dir = self.output_dir / date_str
        day_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"📅 {date_str} - {band_name}")
        logger.info(f"{'='*70}")
        
        # Lade Heatmap
        heatmap_data = self.get_heatmap_for_date(target_date, band_name, cmap)
        if not heatmap_data:
            logger.warning(f"Keine Heatmap-Daten für {date_str}")
            return False
        
        # Speichere Heatmap PNG
        heatmap_file = day_dir / f'heatmap_{cmap}.png'
        with open(heatmap_file, 'wb') as f:
            f.write(heatmap_data)
        logger.info(f"💾 Heatmap gespeichert: {heatmap_file}")
        
        # Lade und speichere Statistiken
        stats = self.get_spectrum_stats(target_date, band_name)
        if stats:
            stats_file = day_dir / 'stats.json'
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
            logger.info(f"📊 Statistiken gespeichert: {stats_file}")
            
            # Gebe zusammenfassung aus
            if 'freq_start' in stats and 'freq_end' in stats:
                logger.info(f"\n   Band: {stats.get('band_name', 'N/A')}")
                logger.info(f"   Zeitraum: {stats.get('time_range', 'N/A')}")
        
        # Speichere auch als Metadaten
        metadata = {
            'date': date_str,
            'band_name': band_name,
            'cmap': cmap,
            'saved_at': datetime.now().isoformat(),
            'heatmap_file': str(heatmap_file.relative_to(self.output_dir)),
            'stats_file': str((day_dir / 'stats.json').relative_to(self.output_dir)) if stats else None
        }
        
        metadata_file = day_dir / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Archiviert: {day_dir}")
        return True
    
    def archive_date_range(self, start_date: datetime, end_date: datetime, 
                          band_name: str = 'Solar Radio', cmap: str = 'viridis'):
        """
        Archiviert Heatmaps für einen Datumsbereich
        
        Args:
            start_date: Start-Datum
            end_date: End-Datum (inklusive)
            band_name: Band-Name
            cmap: Colormap
        """
        current_date = start_date
        successful = 0
        failed = 0
        
        logger.info(f"\n🔄 Archiviere Zeitraum: {start_date.date()} bis {end_date.date()}")
        logger.info(f"   Band: {band_name}")
        logger.info(f"   Colormap: {cmap}\n")
        
        while current_date <= end_date:
            if self.save_heatmap(current_date, band_name, cmap):
                successful += 1
            else:
                failed += 1
            current_date += timedelta(days=1)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"📋 ARCHIVIERUNGSBERICHT")
        logger.info(f"{'='*70}")
        logger.info(f"✅ Erfolgreich: {successful}")
        logger.info(f"❌ Fehler: {failed}")
        logger.info(f"📁 Speicherort: {self.output_dir.absolute()}")
        logger.info(f"{'='*70}\n")
    
    def get_archive_stats(self) -> dict:
        """Gibt Statistiken über die Archiv-Struktur"""
        stats = {
            'total_days': 0,
            'total_heatmaps': 0,
            'total_size_mb': 0,
            'date_range': None,
            'colormaps': set()
        }
        
        if not self.output_dir.exists():
            return stats
        
        dates = []
        for day_dir in sorted(self.output_dir.iterdir()):
            if day_dir.is_dir() and len(day_dir.name) == 10:  # YYYY-MM-DD format
                try:
                    dates.append(day_dir.name)
                    stats['total_days'] += 1
                    
                    # Zähle Heatmaps und Größe
                    for png_file in day_dir.glob('heatmap_*.png'):
                        stats['total_heatmaps'] += 1
                        stats['total_size_mb'] += png_file.stat().st_size / (1024 * 1024)
                        
                        # Extrahiere Colormap aus Dateiname
                        cmap_name = png_file.stem.replace('heatmap_', '')
                        stats['colormaps'].add(cmap_name)
                except:
                    pass
        
        if dates:
            stats['date_range'] = f"{dates[0]} bis {dates[-1]}"
        
        stats['colormaps'] = list(stats['colormaps'])
        return stats


def main():
    parser = argparse.ArgumentParser(
        description='Speichert tägliche Heatmaps für Langzeit-Archivierung',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python3 save_daily_heatmaps.py                           # Heute speichern
  python3 save_daily_heatmaps.py --date yesterday          # Gestern
  python3 save_daily_heatmaps.py --date 2025-11-15         # Spezifisches Datum
  python3 save_daily_heatmaps.py --from 2025-11-10 --to 2025-11-17  # Zeitraum
  python3 save_daily_heatmaps.py --output-dir /home/pi/archives
  python3 save_daily_heatmaps.py --cmap plasma --cmap jet   # Mehrere Colormaps

Cronjob (täglich um 23:55):
  55 23 * * * cd /home/pi/Projekte/solarmonitor/SolarMonitor-RTL && /home/pi/Projekte/solarmonitor/SolarMonitor-RTL/venv/bin/python3 save_daily_heatmaps.py --output-dir ./heatmaps 2>&1 | logger
        """
    )
    
    parser.add_argument('--date', type=str, default='today',
                       help='Datum (YYYY-MM-DD, today, yesterday; default: today)')
    parser.add_argument('--from', type=str, dest='from_date',
                       help='Start-Datum für Zeitraum (YYYY-MM-DD)')
    parser.add_argument('--to', type=str, dest='to_date',
                       help='End-Datum für Zeitraum (YYYY-MM-DD)')
    parser.add_argument('--output-dir', type=str, default='./heatmaps',
                       help='Ausgabeverzeichnis (default: ./heatmaps)')
    parser.add_argument('--band', type=str, default='Solar Radio',
                       help='Band-Name (default: Solar Radio)')
    parser.add_argument('--cmap', type=str, action='append', default=['viridis'],
                       help='Colormap(s) zum Speichern (default: viridis)')
    parser.add_argument('--flask-url', type=str, default='http://localhost:5000',
                       help='Flask API URL (default: http://localhost:5000)')
    parser.add_argument('--stats', action='store_true',
                       help='Zeige Archiv-Statistiken und beende')
    
    args = parser.parse_args()
    
    archiver = DailyHeatmapArchiver(flask_url=args.flask_url, output_dir=args.output_dir)
    
    # Stats-Modus
    if args.stats:
        stats = archiver.get_archive_stats()
        logger.info("\n" + "="*70)
        logger.info("📊 ARCHIV-STATISTIKEN")
        logger.info("="*70)
        logger.info(f"Tage archiviert: {stats['total_days']}")
        logger.info(f"Heatmaps gesamt: {stats['total_heatmaps']}")
        logger.info(f"Größe: {stats['total_size_mb']:.1f} MB")
        if stats['date_range']:
            logger.info(f"Zeitraum: {stats['date_range']}")
        if stats['colormaps']:
            logger.info(f"Colormaps: {', '.join(stats['colormaps'])}")
        logger.info("="*70 + "\n")
        return
    
    # Zeitraum-Modus
    if args.from_date and args.to_date:
        try:
            start_date = datetime.fromisoformat(args.from_date)
            end_date = datetime.fromisoformat(args.to_date)
            
            # Speichere für jede Colormap
            for cmap in args.cmap:
                archiver.archive_date_range(start_date, end_date, args.band, cmap)
        except ValueError as e:
            logger.error(f"Ungültiges Datumsformat: {e}")
            return
    
    # Einzelnes Datum
    else:
        # Parse Datum
        if args.date.lower() == 'today':
            target_date = datetime.now()
        elif args.date.lower() == 'yesterday':
            target_date = datetime.now() - timedelta(days=1)
        else:
            try:
                target_date = datetime.fromisoformat(args.date)
            except ValueError:
                logger.error(f"Ungültiges Datumsformat: {args.date}")
                logger.error("Format: YYYY-MM-DD oder 'today'/'yesterday'")
                return
        
        # Speichere für jede Colormap
        for cmap in args.cmap:
            archiver.save_heatmap(target_date, args.band, cmap)


if __name__ == '__main__':
    main()

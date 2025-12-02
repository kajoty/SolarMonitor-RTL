#!/usr/bin/env python3
"""
SNR Analyzer für SolarMonitor-RTL
Berechnet Signal-zu-Rausch-Verhältnisse und analysiert Datenqualität
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import logging
from typing import Dict, List, Tuple, Optional
import json

logger = logging.getLogger(__name__)

class SNRAnalyzer:
    """Analysiert Signal-zu-Rausch-Verhältnisse aus Spektrum-Daten"""

    def __init__(self, db_path: str = "spectrum.db"):
        self.db_path = db_path

    def get_spectrum_data(self, start_time: str, end_time: str,
                         freq_min: float = None, freq_max: float = None) -> pd.DataFrame:
        """
        Lädt Spektrum-Daten aus der Datenbank

        Args:
            start_time: ISO-8601 Startzeit
            end_time: ISO-8601 Endzeit
            freq_min: Minimale Frequenz (MHz)
            freq_max: Maximale Frequenz (MHz)

        Returns:
            DataFrame mit timestamp, frequency, power
        """
        conn = sqlite3.connect(self.db_path)

        query = """
        SELECT timestamp, frequency, power
        FROM frequency_spectrum
        WHERE datetime(timestamp) BETWEEN ? AND ?
        """

        params = [start_time, end_time]

        if freq_min is not None:
            query += " AND frequency >= ?"
            params.append(freq_min)

        if freq_max is not None:
            query += " AND frequency <= ?"
            params.append(freq_max)

        query += " ORDER BY timestamp, frequency"

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            df['date'] = df['timestamp'].dt.date

        return df

    def calculate_noise_baseline(self, df: pd.DataFrame,
                               noise_hours: List[int] = [0, 1, 2, 3, 4, 5]) -> Dict[float, float]:
        """
        Berechnet Rausch-Baseline aus nächtlichen Messungen

        Args:
            df: DataFrame mit Spektrum-Daten
            noise_hours: Stunden für Rausch-Berechnung (default: 0-5 Uhr)

        Returns:
            Dict mit Frequenz -> Rauschleistung (dB)
        """
        # Filter für Nachtstunden
        night_data = df[df['hour'].isin(noise_hours)]

        if night_data.empty:
            logger.warning("Keine Nachtdaten für Rausch-Baseline gefunden")
            # Fallback: Verwende niedrigste 10% der Werte
            noise_baseline = {}
            for freq in df['frequency'].unique():
                freq_data = df[df['frequency'] == freq]['power']
                noise_baseline[freq] = np.percentile(freq_data, 10)  # 10% Perzentil als Rauschen
            return noise_baseline

        # Berechne Median pro Frequenz als Rausch-Baseline
        noise_baseline = night_data.groupby('frequency')['power'].median().to_dict()

        return noise_baseline

    def calculate_snr(self, df: pd.DataFrame, noise_baseline: Dict[float, float]) -> pd.DataFrame:
        """
        Berechnet SNR für jede Messung

        Args:
            df: DataFrame mit Spektrum-Daten
            noise_baseline: Rausch-Baseline pro Frequenz

        Returns:
            DataFrame mit zusätzlicher SNR-Spalte
        """
        df_snr = df.copy()

        # SNR = Signal - Rauschen (in dB)
        df_snr['noise_level'] = df_snr['frequency'].map(noise_baseline)
        df_snr['snr'] = df_snr['power'] - df_snr['noise_level']

        # Entferne negative SNR (unter Rauschlevel)
        df_snr['snr_clipped'] = df_snr['snr'].clip(lower=0)

        return df_snr

    def analyze_temporal_snr(self, days: int = 1) -> Dict:
        """
        Analysiert zeitliche SNR-Entwicklung über den Tag

        Args:
            days: Anzahl der Tage für Analyse (default: 1)

        Returns:
            Dict mit SNR-Statistiken pro Stunde
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        df = self.get_spectrum_data(
            start_time.isoformat(),
            end_time.isoformat()
        )

        if df.empty:
            return {"error": "Keine Daten gefunden"}

        # Rausch-Baseline berechnen
        noise_baseline = self.calculate_noise_baseline(df)

        # SNR berechnen
        df_snr = self.calculate_snr(df, noise_baseline)

        # Gruppierung nach Stunde
        hourly_stats = df_snr.groupby('hour').agg({
            'snr': ['mean', 'median', 'std', 'min', 'max'],
            'snr_clipped': 'mean'
        }).round(2)

        # In Dictionary konvertieren
        result = {
            'hours': [],
            'mean_snr': [],
            'median_snr': [],
            'std_snr': [],
            'min_snr': [],
            'max_snr': [],
            'mean_snr_clipped': []
        }

        for hour in range(24):
            if hour in hourly_stats.index:
                stats = hourly_stats.loc[hour]
                result['hours'].append(hour)
                result['mean_snr'].append(stats['snr']['mean'])
                result['median_snr'].append(stats['snr']['median'])
                result['std_snr'].append(stats['snr']['std'])
                result['min_snr'].append(stats['snr']['min'])
                result['max_snr'].append(stats['snr']['max'])
                result['mean_snr_clipped'].append(stats['snr_clipped']['mean'])
            else:
                # Fehlende Stunden mit None füllen
                for key in result.keys():
                    if key != 'hours':
                        result[key].append(None)
                result['hours'].append(hour)

        return result

    def analyze_frequency_snr(self, days: int = 1) -> Dict:
        """
        Analysiert SNR-Abhängigkeit von der Frequenz

        Args:
            days: Anzahl der Tage für Analyse

        Returns:
            Dict mit SNR-Statistiken pro Frequenz
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        df = self.get_spectrum_data(
            start_time.isoformat(),
            end_time.isoformat()
        )

        if df.empty:
            return {"error": "Keine Daten gefunden"}

        # Rausch-Baseline berechnen
        noise_baseline = self.calculate_noise_baseline(df)

        # SNR berechnen
        df_snr = self.calculate_snr(df, noise_baseline)

        # Gruppierung nach Frequenz
        freq_stats = df_snr.groupby('frequency').agg({
            'snr': ['mean', 'median', 'std', 'max'],
            'snr_clipped': 'mean',
            'power': 'mean'
        }).round(2)

        # Sortiere nach mittlerem SNR (beste Frequenzen zuerst)
        freq_stats = freq_stats.sort_values(('snr', 'mean'), ascending=False)

        # In Dictionary konvertieren
        result = {
            'frequencies': [],
            'mean_snr': [],
            'median_snr': [],
            'std_snr': [],
            'max_snr': [],
            'mean_snr_clipped': [],
            'mean_power': []
        }

        for freq in freq_stats.index:
            stats = freq_stats.loc[freq]
            result['frequencies'].append(float(freq))
            result['mean_snr'].append(stats['snr']['mean'])
            result['median_snr'].append(stats['snr']['median'])
            result['std_snr'].append(stats['snr']['std'])
            result['max_snr'].append(stats['snr']['max'])
            result['mean_snr_clipped'].append(stats['snr_clipped']['mean'])
            result['mean_power'].append(stats['power']['mean'])

        return result

    def analyze_data_quality(self, days: int = 1, snr_threshold: float = 3.0) -> Dict:
        """
        Bewertet Datenqualität basierend auf SNR

        Args:
            days: Anzahl der Tage für Analyse
            snr_threshold: SNR-Schwellenwert für "gute" Qualität (dB)

        Returns:
            Dict mit Qualitätsstatistiken
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        df = self.get_spectrum_data(
            start_time.isoformat(),
            end_time.isoformat()
        )

        if df.empty:
            return {"error": "Keine Daten gefunden"}

        # Rausch-Baseline berechnen
        noise_baseline = self.calculate_noise_baseline(df)

        # SNR berechnen
        df_snr = self.calculate_snr(df, noise_baseline)

        # Qualitätsbewertung
        df_snr['quality'] = np.where(df_snr['snr_clipped'] >= snr_threshold, 'good', 'poor')

        # Statistische Zusammenfassung
        total_measurements = len(df_snr)
        good_measurements = len(df_snr[df_snr['quality'] == 'good'])
        quality_percentage = (good_measurements / total_measurements * 100) if total_measurements > 0 else 0

        # Qualität pro Stunde
        hourly_quality = df_snr.groupby('hour').agg({
            'quality': lambda x: (x == 'good').mean() * 100,
            'snr_clipped': 'mean'
        }).round(2)

        # Beste und schlechteste Perioden
        best_hour = hourly_quality['quality'].idxmax()
        worst_hour = hourly_quality['quality'].idxmin()

        result = {
            'overall_quality': {
                'total_measurements': total_measurements,
                'good_measurements': good_measurements,
                'quality_percentage': round(quality_percentage, 1),
                'snr_threshold': snr_threshold
            },
            'hourly_quality': {
                'hours': list(hourly_quality.index),
                'quality_percentage': hourly_quality['quality'].tolist(),
                'mean_snr': hourly_quality['snr_clipped'].tolist()
            },
            'best_period': {
                'hour': int(best_hour),
                'quality_percentage': round(hourly_quality.loc[best_hour, 'quality'], 1),
                'mean_snr': round(hourly_quality.loc[best_hour, 'snr_clipped'], 2)
            },
            'worst_period': {
                'hour': int(worst_hour),
                'quality_percentage': round(hourly_quality.loc[worst_hour, 'quality'], 1),
                'mean_snr': round(hourly_quality.loc[worst_hour, 'snr_clipped'], 2)
            }
        }

        return result

def create_snr_analyzer_from_env() -> SNRAnalyzer:
    """Erstellt SNRAnalyzer aus Umgebungsvariablen"""
    db_path = "spectrum.db"  # Könnte aus .env kommen
    return SNRAnalyzer(db_path=db_path)
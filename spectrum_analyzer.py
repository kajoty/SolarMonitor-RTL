"""
Spektrumanalyse und Visualisierung für RTL-SDR Scan-Ergebnisse
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import io
import base64
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class SpectrumAnalyzer:
    """Analysiert und visualisiert RTL-SDR Spektrum-Daten"""
    
    @staticmethod
    def plot_scan_results(results, figsize: tuple = (14, 8)) -> io.BytesIO:
        """
        Erstelle Visualisierung der Scan-Ergebnisse
        
        Args:
            results: Liste von ScanResult Objekten
            figsize: Größe der Grafik
            
        Returns:
            BytesIO mit PNG-Bild
        """
        if not results:
            logger.warning("Keine Ergebnisse zum Visualisieren")
            return None
        
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        fig.suptitle('RTL-SDR Frequenzbereich-Analyse', fontsize=16, fontweight='bold')
        
        # 1. SNR Vergleich (Bar Chart)
        ax = axes[0, 0]
        bands = [r.band.name for r in results]
        snrs = [r.signal_to_noise for r in results]
        colors = ['#2ecc71' if r.active else '#95a5a6' for r in results]
        
        bars = ax.barh(bands, snrs, color=colors, edgecolor='black', linewidth=0.5)
        ax.set_xlabel('Signal-to-Noise Ratio (dB)', fontweight='bold')
        ax.set_title('SNR nach Frequenzbereich', fontweight='bold')
        ax.axvline(x=3, color='red', linestyle='--', linewidth=2, label='Min Schwelle (3dB)')
        ax.legend()
        ax.grid(axis='x', alpha=0.3)
        
        # Nummerierung hinzufügen
        for i, (bar, snr) in enumerate(zip(bars, snrs)):
            ax.text(snr + 0.1, bar.get_y() + bar.get_height()/2, 
                   f'{snr:.1f}dB', va='center', fontweight='bold')
        
        # 2. Aktivitätsrate (Pie Chart)
        ax = axes[0, 1]
        active_count = sum(1 for r in results if r.active)
        quiet_count = len(results) - active_count
        
        sizes = [active_count, quiet_count]
        labels = [f'Aktiv\n({active_count})', f'Ruhig\n({quiet_count})']
        colors_pie = ['#e74c3c', '#3498db']
        explode = (0.1, 0)
        
        ax.pie(sizes, explode=explode, labels=labels, colors=colors_pie, 
               autopct='%1.1f%%', shadow=True, startangle=90, textprops={'fontweight': 'bold'})
        ax.set_title('Aktive vs. Ruhige Bänder', fontweight='bold')
        
        # 3. Power-Spektrum Übersicht
        ax = axes[1, 0]
        band_names_short = [r.band.name.split('(')[0].strip()[:15] for r in results]
        peak_powers = [r.peak_power for r in results]
        avg_powers = [r.avg_power for r in results]
        noise_floors = [r.noise_floor for r in results]
        
        x = np.arange(len(results))
        width = 0.25
        
        ax.bar(x - width, peak_powers, width, label='Peak Power', color='#e74c3c', alpha=0.8)
        ax.bar(x, avg_powers, width, label='Avg Power', color='#f39c12', alpha=0.8)
        ax.bar(x + width, noise_floors, width, label='Noise Floor', color='#3498db', alpha=0.8)
        
        ax.set_ylabel('Power (dB)', fontweight='bold')
        ax.set_title('Power-Spektrum nach Band', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(band_names_short, rotation=45, ha='right', fontsize=8)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # 4. Aktivitätsmatrix
        ax = axes[1, 1]
        activity_data = []
        activity_labels = []
        
        for r in results:
            activity_data.append(r.activity_percentage)
            activity_labels.append(r.band.name.split('(')[0].strip()[:12])
        
        # Erstelle Heatmap-ähnliche Visualisierung
        activity_array = np.array(activity_data).reshape(-1, 1)
        im = ax.imshow(activity_array.T, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=100)
        
        ax.set_xticks(np.arange(len(activity_labels)))
        ax.set_xticklabels(activity_labels, rotation=45, ha='right', fontsize=8)
        ax.set_yticks([0])
        ax.set_yticklabels(['Aktivität %'])
        ax.set_title('Aktivitätsrate (%) nach Band', fontweight='bold')
        
        # Colorbar
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
        cbar.set_label('Aktivität %', fontweight='bold')
        
        # Werte in den Zellen anzeigen
        for i, val in enumerate(activity_data):
            ax.text(i, 0, f'{val:.0f}%', ha='center', va='center', 
                   fontweight='bold', color='black' if val < 50 else 'white')
        
        plt.tight_layout()
        
        # Speichere als PNG
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    @staticmethod
    def plot_frequency_spectrum(results, figsize: tuple = (14, 6)) -> io.BytesIO:
        """
        Erstelle Frequenzspektrum-Übersicht
        
        Args:
            results: Liste von ScanResult Objekten
            figsize: Größe der Grafik
            
        Returns:
            BytesIO mit PNG-Bild
        """
        if not results:
            logger.warning("Keine Ergebnisse zur Spektrum-Visualisierung")
            return None
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Sortiere nach Frequenz
        results_sorted = sorted(results, key=lambda r: r.band.freq_start)
        
        y_positions = np.arange(len(results_sorted))
        band_names = [r.band.name for r in results_sorted]
        
        # Zeichne Frequenzbereiche
        for i, result in enumerate(results_sorted):
            freq_start = result.band.freq_start
            freq_width = result.band.freq_end - result.band.freq_start
            
            # Färbe basierend auf SNR
            snr = result.signal_to_noise
            if snr > 10:
                color = '#27ae60'  # Green
            elif snr > 5:
                color = '#f39c12'  # Orange
            elif snr > 0:
                color = '#e67e22'  # Dark Orange
            else:
                color = '#95a5a6'  # Gray
            
            # Rechteck für Frequenzbereich
            rect = mpatches.Rectangle((freq_start, i - 0.4), freq_width, 0.8,
                                      linewidth=2, edgecolor='black', facecolor=color, alpha=0.7)
            ax.add_patch(rect)
            
            # Beschriftung
            mid_freq = freq_start + freq_width / 2
            ax.text(mid_freq, i, f"{snr:.1f}dB", ha='center', va='center',
                   fontweight='bold', fontsize=9, color='white')
        
        ax.set_xlim(0, 3000)
        ax.set_ylim(-1, len(results_sorted))
        ax.set_yticks(y_positions)
        ax.set_yticklabels(band_names, fontsize=9)
        ax.set_xlabel('Frequenz (MHz)', fontweight='bold', fontsize=11)
        ax.set_title('Frequenzspektrum-Übersicht (farbkodiert nach SNR)', fontweight='bold', fontsize=13)
        ax.grid(axis='x', alpha=0.3)
        
        # Legende
        green_patch = mpatches.Patch(color='#27ae60', label='Sehr stark (>10 dB)', alpha=0.7)
        orange_patch = mpatches.Patch(color='#f39c12', label='Stark (5-10 dB)', alpha=0.7)
        orange2_patch = mpatches.Patch(color='#e67e22', label='Schwach (0-5 dB)', alpha=0.7)
        gray_patch = mpatches.Patch(color='#95a5a6', label='Sehr schwach (<0 dB)', alpha=0.7)
        ax.legend(handles=[green_patch, orange_patch, orange2_patch, gray_patch],
                 loc='upper right', fontsize=9)
        
        plt.tight_layout()
        
        # Speichere als PNG
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    @staticmethod
    def results_to_base64(buf: io.BytesIO) -> Optional[str]:
        """Konvertiere BufferIO zu Base64 String"""
        if buf is None:
            return None
        
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

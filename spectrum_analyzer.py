import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


class SpectrumAnalyzer:
    """Minimal stub for plotting scan results used by `app.py`.

    This implementation produces simple PNGs so the Flask app can start
    when the full module is not present. It intentionally stays small
    and dependency-light (uses existing matplotlib from requirements).
    """

    @staticmethod
    def plot_scan_results(results):
        try:
            fig, ax = plt.subplots(figsize=(6, 3))
            bands = [r.band.name for r in results]
            values = [r.avg_power for r in results]
            ax.barh(bands, values, color='C0')
            ax.set_xlabel('Avg Power (dB)')
            ax.set_title('Scan Overview')
            fig.tight_layout()

            buf = io.BytesIO()
            fig.savefig(buf, format='png')
            plt.close(fig)
            buf.seek(0)
            return buf
        except Exception:
            return None

    @staticmethod
    def plot_frequency_spectrum(results):
        try:
            # Try to plot frequencies from the first result that has data
            freqs = None
            powers = None
            for r in results:
                if hasattr(r, 'frequencies') and r.frequencies is not None and r.power_values is not None:
                    freqs = r.frequencies
                    powers = r.power_values
                    break

            fig, ax = plt.subplots(figsize=(6, 3))
            if freqs is not None and powers is not None:
                ax.plot(freqs, powers, '-', linewidth=1)
                ax.set_xlabel('Frequency (MHz)')
                ax.set_ylabel('Power (dB)')
                ax.set_title('Frequency Spectrum')
            else:
                ax.text(0.5, 0.5, 'No frequency data available', ha='center', va='center')
                ax.set_axis_off()

            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format='png')
            plt.close(fig)
            buf.seek(0)
            return buf
        except Exception:
            return None

    @staticmethod
    def results_to_base64(buf):
        try:
            data = buf.getvalue()
            return base64.b64encode(data).decode('ascii')
        except Exception:
            return None

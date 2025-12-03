// Configuration
const API_BASE = '/api';
let currentBandImageData = null;

// Elements
const bandSelectInput = document.getElementById('bandSelect');
const bandTimeRangeSelect = document.getElementById('bandTimeRange');
const dateSelect = document.getElementById('dateSelect');
const bandColormapSelect = document.getElementById('bandColormap');
const generateBandBtn = document.getElementById('generateBandBtn');
const downloadBandBtn = document.getElementById('downloadBandBtn');

const heatmapContainer = document.getElementById('heatmapContainer');
const errorMessage = document.getElementById('errorMessage');
const healthStatus = document.getElementById('healthStatus');
const infoText = document.getElementById('infoText');
const presetButtons = document.querySelectorAll('.preset-btn');

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            // Setze heutiges Datum als Standard
            const today = new Date().toISOString().split('T')[0];
            dateSelect.value = today;

            // Event Listeners - Band Spectrum
            generateBandBtn.addEventListener('click', generateBandHeatmap);
            downloadBandBtn.addEventListener('click', downloadBandHeatmap);

            bandColormapSelect.addEventListener('change', () => {
                generateBandHeatmap();
            });

            presetButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    presetButtons.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    bandTimeRangeSelect.value = btn.dataset.range;
                    generateBandHeatmap();
                });
            });

            bandTimeRangeSelect.addEventListener('change', () => {
                updatePresetButtons();
            });

            dateSelect.addEventListener('change', () => {
                generateBandHeatmap();
                generateAvgPowerPlot();
            });

            // Event-Listener für Durchschnittspegel
            document.getElementById('receiverSelect').addEventListener('change', () => {
                generateAvgPowerPlot();
            });

            // SNR Button Event-Listener
            document.getElementById('snrDaysSelect').addEventListener('change', () => {
                // Optional: Auto-update wenn sich Zeitraum ändert
            });

            document.getElementById('snrThresholdSelect').addEventListener('change', () => {
                // Optional: Auto-update wenn sich Schwellenwert ändert
            });

            checkHealth();
            loadBands();
            generateAvgPowerPlot();  // Initial Durchschnittspegel laden
            // Aktualisiere Health-Status alle 30 Sekunden
            setInterval(checkHealth, 30000);
        });

        /**
         * Health-Check durchführen
         */
        async function checkHealth() {
            try {
                const response = await fetch(`${API_BASE}/health`);
                const data = await response.json();

                const statusDot = healthStatus.querySelector('.status-dot');
                const statusText = healthStatus.querySelector('span');

                if (data.status === 'healthy') {
                    statusDot.className = 'status-dot healthy';
                    statusText.textContent = 'Verbunden';
                } else if (data.status === 'degraded') {
                    statusDot.className = 'status-dot degraded';
                    statusText.textContent = 'Verbindung eingeschränkt';
                } else {
                    statusDot.className = 'status-dot unhealthy';
                    statusText.textContent = 'Nicht verbunden';
                }
            } catch (e) {
                const statusDot = healthStatus.querySelector('.status-dot');
                statusDot.className = 'status-dot unhealthy';
                console.error('Health-Check Fehler:', e);
            }
        }

        /**
         * Aktualisiere Preset-Buttons basierend auf aktuellem Zeitraum
         */
        function updatePresetButtons() {
            const currentRange = bandTimeRangeSelect.value;
            presetButtons.forEach(btn => {
                if (btn.dataset.range === currentRange) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
        }

        /**
         * UI Helper Funktionen
         */
        function showLoading() {
            heatmapContainer.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Generiere Heatmap...</p>
                </div>
            `;
        }

        function showError(message) {
            errorMessage.textContent = message;
            errorMessage.classList.add('show');
        }

        function clearError() {
            errorMessage.classList.remove('show');
        }

        /**
         * Lade verfügbare Frequenzbänder (Solar Radio Astronomy)
         */
        async function loadBands() {
            try {
                const response = await fetch(`${API_BASE}/bands`);
                const data = await response.json();

                if (data.bands && Array.isArray(data.bands)) {
                    // Es gibt nur noch ein Band - auto-select
                    bandSelectInput.innerHTML = '';
                    
                    data.bands.forEach((band, index) => {
                        const option = document.createElement('option');
                        option.value = band.name;
                        option.textContent = `${band.name} (${band.freq_start}-${band.freq_end} MHz) - Space Weather`;
                        bandSelectInput.appendChild(option);
                        
                        // Auto-select das erste (einzige) Band
                        if (index === 0) {
                            option.selected = true;
                        }
                    });
                    
                    // Automatisch erste Heatmap generieren
                    setTimeout(() => generateBandHeatmap(), 500);
                }
            } catch (error) {
                console.error('Fehler beim Laden der Bänder:', error);
            }
        }

        /**
         * Generiere Band-Heatmap vom Server
         */
        /**
         * Zeige Heatmap im Container an
         */
        function displayHeatmap(data) {
            const img = document.createElement('img');
            img.src = `data:image/png;base64,${data.data}`;
            img.className = 'heatmap-image';
            img.alt = 'FFT Spektrum Heatmap';

            heatmapContainer.innerHTML = '';
            heatmapContainer.appendChild(img);
        }

        async function generateBandHeatmap() {
            const bandName = bandSelectInput.value;
            const timeRange = bandTimeRangeSelect.value;
            const selectedDate = dateSelect.value;

            if (!bandName) {
                showError('Bitte wählen Sie ein Frequenzband aus');
                return;
            }

            showLoading();
            clearError();

            try {
                const receiver = document.getElementById('receiverSelect').value;
                
                // Spezielle Behandlung für 24h-Heatmaps: Prüfe zuerst gespeicherte Version
                if (timeRange === '24h') {
                    try {
                        const storedResponse = await fetch(`${API_BASE}/heatmap/stored`);
                        const storedData = await storedResponse.json();
                        
                        if (storedData.status === 'success' && storedData.stored) {
                            // Gespeicherte Heatmap gefunden - verwende diese
                            currentBandImageData = storedData.data;
                            displayHeatmap({
                                status: 'success',
                                data: storedData.data,
                                band_name: bandName,
                                time_range: '24h',
                                cmap: bandColormapSelect.value,
                                stored: true,
                                date: storedData.date
                            });
                            updateBandInfo({
                                band_name: bandName,
                                time_range: '24h',
                                cmap: bandColormapSelect.value,
                                timestamp: storedData.timestamp,
                                stored: true,
                                date: storedData.date
                            });
                            return;
                        }
                    } catch (storedError) {
                        console.log('Keine gespeicherte 24h-Heatmap gefunden, generiere neue:', storedError);
                    }
                }
                
                // Normale Generierung (oder Fallback für 24h wenn gespeicherte nicht verfügbar)
                const params = new URLSearchParams({
                    band_name: bandName,
                    time_range: timeRange,
                    cmap: bandColormapSelect.value,
                    format: 'json',
                    receiver: receiver,
                    date: selectedDate
                });
                const response = await fetch(`${API_BASE}/heatmap/band?${params}`);
                const data = await response.json();

                if (data.status === 'success' && data.data) {
                    currentBandImageData = data.data;
                    displayHeatmap(data);
                    updateBandInfo(data);
                } else if (data.status === 'no_data') {
                    showError(`⏳ Keine Daten verfügbar für Band "${bandName}". Bitte später erneut versuchen.\n${data.message}`);
                    heatmapContainer.innerHTML = '<div class="loading"><p>Warte auf Scan-Ergebnisse...</p></div>';
                } else if (!response.ok) {
                    throw new Error(data.message || `HTTP ${response.status}`);
                } else {
                    throw new Error(data.message || 'Unbekannter Fehler');
                }

            } catch (error) {
                showError(`Fehler beim Generieren der Band-Heatmap: ${error.message}`);
                console.error(error);
            }
        }

        /**
         * Download Band-Heatmap als PNG
         */
        function downloadBandHeatmap() {
            if (!currentBandImageData) {
                showError('Keine Band-Heatmap zum Download verfügbar. Generieren Sie zuerst eine Band-Heatmap.');
                return;
            }

            try {
                const bandName = bandSelectInput.value || 'band';
                const link = document.createElement('a');
                link.href = `data:image/png;base64,${currentBandImageData}`;
                link.download = `heatmap-band-${bandName}-${bandTimeRangeSelect.value}-${new Date().toISOString().slice(0, 10)}.png`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } catch (error) {
                showError(`Fehler beim Download: ${error.message}`);
            }
        }

        /**
         * Aktualisiere Info-Text für Band-Heatmap
         */
        function updateBandInfo(data) {
            let infoStr = `✅ Band-Heatmap generiert für <strong>${data.band_name}</strong>`;
            if (data.freq_start && data.freq_end) {
                infoStr += ` (${data.freq_start}-${data.freq_end} MHz)`;
            }
            infoStr += ` | Zeitraum: <strong>${data.time_range === '1h' ? '1 Stunde' : data.time_range === '6h' ? '6 Stunden' : '24 Stunden'}</strong>`;
            infoStr += ` | Farbschema: <strong>${data.cmap}</strong>`;
            if (data.stored) {
                infoStr += ` | <span style="color: #28a745;">📁 Gespeicherte Heatmap vom ${data.date}</span>`;
            } else {
                infoStr += ` | Zeit: <strong>${new Date(data.timestamp).toLocaleString('de-DE')}</strong>`;
            }
            infoText.innerHTML = infoStr;
        }

        /**
         * Durchschnittspegel-Plot generieren
         */
        async function generateAvgPowerPlot() {
            const receiver = document.getElementById('receiverSelect').value;
            const timeRange = bandTimeRangeSelect.value;
            const selectedDate = dateSelect.value;
            
            const params = new URLSearchParams({
                time_range: timeRange,
                receiver: receiver,
                date: selectedDate
            });
            
            const avgPowerContainer = document.getElementById('avgPowerContainer');
            avgPowerContainer.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Berechne Durchschnittspegel...</p>
                </div>
            `;
            
            try {
                const response = await fetch(`${API_BASE}/avgpower?${params}`);
                const data = await response.json();
                
                if (data.status === 'success' && data.image) {
                    const img = document.createElement('img');
                    img.src = `data:image/png;base64,${data.image}`;
                    img.className = 'heatmap-image';
                    img.alt = 'Durchschnittlicher Spektralpegel';
                    avgPowerContainer.innerHTML = '';
                    avgPowerContainer.appendChild(img);
                } else {
                    avgPowerContainer.innerHTML = `
                        <div class="error show">
                            ${data.message || 'Fehler beim Abrufen des Durchschnittspegels.'}
                        </div>
                    `;
                }
            } catch (error) {
                avgPowerContainer.innerHTML = `
                    <div class="error show">
                        ${error.message}
                    </div>
                `;
            }
        }

        /**
         * SNR Analyse: Zeitliche Entwicklung
         */
        async function analyzeTemporalSNR() {
            console.log('analyzeTemporalSNR called');
            const days = document.getElementById('snrDaysSelect').value;
            const container = document.getElementById('snrResultsContainer');
            console.log('days:', days, 'container:', container);

            container.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Analysiere zeitliche SNR-Entwicklung...</p>
                </div>
            `;

            try {
                const response = await fetch(`${API_BASE}/snr/temporal?days=${days}`);
                const data = await response.json();

                if (data.status === 'success') {
                    displayTemporalSNR(data.data);
                } else {
                    throw new Error(data.message || 'Unbekannter Fehler');
                }
            } catch (error) {
                container.innerHTML = `
                    <div class="error show">
                        Fehler bei SNR-Analyse: ${error.message}
                    </div>
                `;
            }
        }

        /**
         * SNR Analyse: Frequenzabhängigkeit
         */
        async function analyzeFrequencySNR() {
            console.log('analyzeFrequencySNR called');
            const days = document.getElementById('snrDaysSelect').value;
            const container = document.getElementById('snrResultsContainer');

            container.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Analysiere Frequenz-SNR-Abhängigkeit...</p>
                </div>
            `;

            try {
                const response = await fetch(`${API_BASE}/snr/frequency?days=${days}`);
                const data = await response.json();

                if (data.status === 'success') {
                    displayFrequencySNR(data.data);
                } else {
                    throw new Error(data.message || 'Unbekannter Fehler');
                }
            } catch (error) {
                container.innerHTML = `
                    <div class="error show">
                        Fehler bei SNR-Analyse: \${error.message}
                    </div>
                `;
            }
        }

        /**
         * SNR Analyse: Datenqualität
         */
        async function analyzeDataQuality() {
            console.log('analyzeDataQuality called');
            const days = document.getElementById('snrDaysSelect').value;
            const threshold = document.getElementById('snrThresholdSelect').value;
            const container = document.getElementById('snrResultsContainer');

            container.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Bewerte Datenqualität...</p>
                </div>
            `;

            try {
                const response = await fetch(`${API_BASE}/snr/quality?days=${days}&snr_threshold=${threshold}`);
                const data = await response.json();

                if (data.status === 'success') {
                    displayDataQuality(data.data);
                } else {
                    throw new Error(data.message || 'Unbekannter Fehler');
                }
            } catch (error) {
                container.innerHTML = `
                    <div class="error show">
                        Fehler bei Qualitätsanalyse: \${error.message}
                    </div>
                `;
            }
        }

        /**
         * Zeigt zeitliche SNR-Entwicklung an
         */
        function displayTemporalSNR(data) {
            const container = document.getElementById('snrResultsContainer');

            let html = `
                <h3>⏰ Zeitliche SNR-Entwicklung</h3>
                <p>Signal-zu-Rausch-Verhältnis über 24 Stunden (Sonnenauf-/-untergang-Effekte)</p>
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <canvas id="temporalSNRChart" width="800" height="400"></canvas>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px;">
            `;

            // Berechne beste und schlechteste Stunden
            const validData = data.hours.filter((_, i) => data.mean_snr[i] !== null);
            if (validData.length > 0) {
                const bestHour = data.hours[data.mean_snr.indexOf(Math.max(...data.mean_snr.filter(x => x !== null)))];
                const worstHour = data.hours[data.mean_snr.indexOf(Math.min(...data.mean_snr.filter(x => x !== null)))];

                html += `
                    <div style="background: #e8f5e8; padding: 15px; border-radius: 6px; border-left: 4px solid #4caf50;">
                        <h4>🌅 Beste Stunde</h4>
                        <p><strong>${bestHour}:00 Uhr</strong></p>
                        <p>SNR: ${data.mean_snr[data.hours.indexOf(bestHour)].toFixed(1)} dB</p>
                    </div>
                    <div style="background: #ffe8e8; padding: 15px; border-radius: 6px; border-left: 4px solid #f44336;">
                        <h4>🌙 Schlechteste Stunde</h4>
                        <p><strong>${worstHour}:00 Uhr</strong></p>
                        <p>SNR: ${data.mean_snr[data.hours.indexOf(worstHour)].toFixed(1)} dB</p>
                    </div>
                `;
            }

            html += `
                </div>
                <p style="margin-top: 20px; color: #666; font-size: 0.9em;">
                    💡 <strong>Tipp:</strong> Die besten Beobachtungszeiten sind während der Dämmerung, wenn Solaraktivität hoch und terrestrisches Rauschen niedrig ist.
                </p>
            `;

            container.innerHTML = html;

            // Chart.js für Visualisierung (falls verfügbar)
            if (typeof Chart !== 'undefined') {
                createTemporalSNRChart(data);
            }
        }

        /**
         * Zeigt Frequenz-SNR-Abhängigkeit an
         */
        function displayFrequencySNR(data) {
            const container = document.getElementById('snrResultsContainer');

            let html = `
                <h3>📻 Frequenzabhängige SNR-Analyse</h3>
                <p>Welche Frequenzen bieten die besten Signal-zu-Rausch-Verhältnisse?</p>
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <canvas id="frequencySNRChart" width="800" height="400"></canvas>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top: 20px;">
            `;

            if (data.frequencies.length > 0) {
                const bestFreq = data.frequencies[data.mean_snr.indexOf(Math.max(...data.mean_snr))];
                const bestSNR = Math.max(...data.mean_snr);

                html += `
                    <div style="background: #e8f5e8; padding: 15px; border-radius: 6px; border-left: 4px solid #4caf50;">
                        <h4>🎯 Beste Frequenz</h4>
                        <p><strong>${bestFreq.toFixed(1)} MHz</strong></p>
                        <p>SNR: ${bestSNR.toFixed(1)} dB</p>
                    </div>
                    <div style="background: #e3f2fd; padding: 15px; border-radius: 6px; border-left: 4px solid #2196f3;">
                        <h4>📊 Analyse</h4>
                        <p>${data.frequencies.length} Frequenzen analysiert</p>
                        <p>Durchschnitt SNR: ${(data.mean_snr.reduce((a, b) => a + b, 0) / data.mean_snr.length).toFixed(1)} dB</p>
                    </div>
                `;
            }

            html += `
                </div>
                <p style="margin-top: 20px; color: #666; font-size: 0.9em;">
                    💡 <strong>Tipp:</strong> Frequenzen um 30-50 MHz zeigen oft die beste Solaraktivität. Höhere Frequenzen können durch terrestrisches Rauschen gestört werden.
                </p>
            `;

            container.innerHTML = html;

            // Chart.js für Visualisierung (falls verfügbar)
            if (typeof Chart !== 'undefined') {
                createFrequencySNRChart(data);
            }
        }

        /**
         * Zeigt Datenqualitätsbewertung an
         */
        function displayDataQuality(data) {
            const container = document.getElementById('snrResultsContainer');

            let html = `
                <h3>✅ Datenqualitätsbewertung</h3>
                <p>Bewertung der Messperioden nach Signalqualität (SNR > ${data.overall_quality.snr_threshold} dB)</p>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
                    <div style="background: #e8f5e8; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #4caf50;">
                        <h4 style="margin: 0; color: #2e7d32;">Gesamtqualität</h4>
                        <div style="font-size: 2em; font-weight: bold; color: #2e7d32; margin: 10px 0;">
                            ${data.overall_quality.quality_percentage}%
                        </div>
                        <p style="margin: 0; color: #666;">${data.overall_quality.good_measurements} von ${data.overall_quality.total_measurements} Messungen</p>
                    </div>

                    <div style="background: #fff3e0; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #ff9800;">
                        <h4 style="margin: 0; color: #e65100;">Beste Stunde</h4>
                        <div style="font-size: 1.5em; font-weight: bold; color: #e65100; margin: 10px 0;">
                            ${data.best_period.hour}:00 Uhr
                        </div>
                        <p style="margin: 0; color: #666;">${data.best_period.quality_percentage}% Qualität</p>
                        <p style="margin: 5px 0 0 0; color: #666; font-size: 0.9em;">SNR: ${data.best_period.mean_snr} dB</p>
                    </div>

                    <div style="background: #ffebee; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #f44336;">
                        <h4 style="margin: 0; color: #c62828;">Schlechteste Stunde</h4>
                        <div style="font-size: 1.5em; font-weight: bold; color: #c62828; margin: 10px 0;">
                            ${data.worst_period.hour}:00 Uhr
                        </div>
                        <p style="margin: 0; color: #666;">${data.worst_period.quality_percentage}% Qualität</p>
                        <p style="margin: 5px 0 0 0; color: #666; font-size: 0.9em;">SNR: ${data.worst_period.mean_snr} dB</p>
                    </div>
                </div>

                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h4>📈 Stündliche Qualitätsverteilung</h4>
                    <canvas id="qualityChart" width="800" height="300"></canvas>
                </div>

                <div style="background: #f5f5f5; padding: 15px; border-radius: 6px; margin-top: 20px;">
                    <h4 style="margin: 0 0 10px 0;">💡 Empfehlungen</h4>
                    <ul style="margin: 0; padding-left: 20px; color: #555;">
                        <li><strong>Optimale Beobachtungszeit:</strong> ${data.best_period.hour}:00 Uhr (${data.best_period.quality_percentage}% Qualität)</li>
                        <li><strong>Zu vermeidende Zeiten:</strong> ${data.worst_period.hour}:00 Uhr (${data.worst_period.quality_percentage}% Qualität)</li>
                        <li><strong>Systemstatus:</strong> ${data.overall_quality.quality_percentage > 70 ? 'Gut' : data.overall_quality.quality_percentage > 40 ? 'Akzeptabel' : 'Verbesserungswürdig'}</li>
                    </ul>
                </div>
            `;

            container.innerHTML = html;

            // Chart.js für Visualisierung (falls verfügbar)
            if (typeof Chart !== 'undefined') {
                createQualityChart(data);
            }
        }

        /**
         * Erstellt Chart für zeitliche SNR-Entwicklung
         */
        function createTemporalSNRChart(data) {
            const ctx = document.getElementById('temporalSNRChart');
            if (!ctx) return;

            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.hours.map(h => `${h}:00`),
                    datasets: [{
                        label: 'Mittelwert SNR (dB)',
                        data: data.mean_snr,
                        borderColor: '#2196f3',
                        backgroundColor: 'rgba(33, 150, 243, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'SNR (geclippt >0)',
                        data: data.mean_snr_clipped,
                        borderColor: '#4caf50',
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'SNR-Entwicklung über 24 Stunden'
                        }
                    },
                    scales: {
                        y: {
                            title: {
                                display: true,
                                text: 'SNR (dB)'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Uhrzeit'
                            }
                        }
                    }
                }
            });
        }

        /**
         * Erstellt Chart für Frequenz-SNR-Abhängigkeit
         */
        function createFrequencySNRChart(data) {
            const ctx = document.getElementById('frequencySNRChart');
            if (!ctx) return;

            new Chart(ctx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: 'SNR pro Frequenz',
                        data: data.frequencies.map((freq, i) => ({
                            x: freq,
                            y: data.mean_snr[i]
                        })),
                        backgroundColor: '#ff9800',
                        borderColor: '#f57c00'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'SNR-Abhängigkeit von der Frequenz'
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Frequenz (MHz)'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'SNR (dB)'
                            }
                        }
                    }
                }
            });
        }

        /**
         * Erstellt Chart für Datenqualität
         */
        function createQualityChart(data) {
            const ctx = document.getElementById('qualityChart');
            if (!ctx) return;

            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.hourly_quality.hours.map(h => `${h}:00`),
                    datasets: [{
                        label: 'Qualitätsprozent (%)',
                        data: data.hourly_quality.quality_percentage,
                        backgroundColor: data.hourly_quality.quality_percentage.map(p =>
                            p > 70 ? '#4caf50' : p > 40 ? '#ff9800' : '#f44336'
                        ),
                        borderColor: '#333',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Stündliche Datenqualität'
                        }
                    },
                    scales: {
                        y: {
                            title: {
                                display: true,
                                text: 'Qualität (%)'
                            },
                            max: 100
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Uhrzeit'
                            }
                        }
                    }
                }
            });
        }
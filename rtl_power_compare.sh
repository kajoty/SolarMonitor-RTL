#!/bin/bash
# RTL-Power Parallel-System für Vergleich mit eigenem Scanner
# Nutzt rtl_power für hochauflösende Spektrum-Scans

FREQ_START=20M
FREQ_END=80M
BIN_SIZE=10k        # Frequenz-Auflösung (kleiner = detaillierter)
GAIN=20.7           # Gain in dB
INTERVAL=60         # Integration time in seconds
DURATION=6h         # Scan-Dauer

OUTPUT_DIR="./rtl_power_data"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CSV_FILE="${OUTPUT_DIR}/spectrum_${TIMESTAMP}.csv"
HEATMAP_FILE="${OUTPUT_DIR}/heatmap_${TIMESTAMP}.png"

# Erstelle Output-Verzeichnis
mkdir -p "$OUTPUT_DIR"

echo "=== RTL-Power Parallel Scanner ==="
echo "Frequenzbereich: ${FREQ_START} - ${FREQ_END}"
echo "Bin-Size: ${BIN_SIZE} ($(echo "scale=0; 60000000/${BIN_SIZE//[kM]/}" | bc) bins)"
echo "Interval: ${INTERVAL}s"
echo "Dauer: ${DURATION}"
echo "Gain: ${GAIN} dB"
echo "Output: ${CSV_FILE}"
echo ""
echo "Scan läuft... (CTRL+C zum Stoppen)"
echo ""

# Starte rtl_power
rtl_power -f ${FREQ_START}:${FREQ_END}:${BIN_SIZE} \
          -g ${GAIN} \
          -i ${INTERVAL} \
          -e ${DURATION} \
          "${CSV_FILE}"

# Check ob CSV erstellt wurde
if [ -f "${CSV_FILE}" ]; then
    echo ""
    echo "✅ Scan abgeschlossen: ${CSV_FILE}"
    
    # Generiere Heatmap
    echo "Generiere Heatmap..."
    python3 rtl_power_heatmap.py "${CSV_FILE}" "${HEATMAP_FILE}"
    
    if [ -f "${HEATMAP_FILE}" ]; then
        echo "✅ Heatmap erstellt: ${HEATMAP_FILE}"
        echo ""
        echo "Zum Anschauen:"
        echo "  xdg-open ${HEATMAP_FILE}"
    else
        echo "⚠️ Heatmap konnte nicht erstellt werden"
    fi
    
    # Zeige Datei-Info
    echo ""
    echo "Datei-Größen:"
    ls -lh "${CSV_FILE}" "${HEATMAP_FILE}" 2>/dev/null
else
    echo "❌ Fehler: CSV-Datei wurde nicht erstellt"
    exit 1
fi

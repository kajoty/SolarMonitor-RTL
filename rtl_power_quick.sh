#!/bin/bash
# Quick 10-Minuten Test mit rtl_power

FREQ_START=20M
FREQ_END=80M
BIN_SIZE=50k        # Gröber für schnellen Test
GAIN=20.7
INTERVAL=30         # 30s Integration
DURATION=10m        # 10 Minuten

OUTPUT_DIR="./rtl_power_data"
mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CSV_FILE="${OUTPUT_DIR}/quick_${TIMESTAMP}.csv"
HEATMAP_FILE="${OUTPUT_DIR}/quick_${TIMESTAMP}.png"

echo "=== RTL-Power Quick Test (10 Minuten) ==="
echo "Starte Scan..."

rtl_power -f ${FREQ_START}:${FREQ_END}:${BIN_SIZE} \
          -g ${GAIN} \
          -i ${INTERVAL} \
          -e ${DURATION} \
          "${CSV_FILE}"

if [ -f "${CSV_FILE}" ]; then
    echo "✅ CSV: ${CSV_FILE}"
    python3 rtl_power_heatmap.py "${CSV_FILE}" "${HEATMAP_FILE}"
    
    if [ -f "${HEATMAP_FILE}" ]; then
        echo "✅ Heatmap: ${HEATMAP_FILE}"
        ls -lh "${HEATMAP_FILE}"
    fi
fi

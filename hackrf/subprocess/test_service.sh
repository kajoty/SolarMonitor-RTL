#!/bin/bash
# Test-Skript für Heatmap Generator Service

HOST="localhost:8888"

echo "🧪 Heatmap Generator Service Tests"
echo "===================================="
echo ""

# Test 1: Status
echo "📊 Test 1: Status-Check"
curl -s "http://${HOST}/status" | python3 -m json.tool
echo ""
echo ""

# Test 2: Heatmap generieren (Base64)
echo "🖼️  Test 2: Heatmap generieren (24h, Base64)"
curl -s -X POST "http://${HOST}/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "band": "Solar Radio",
    "hours": 24,
    "colormap": "YlOrRd",
    "format": "base64"
  }' | python3 -c "import sys, json; data = json.load(sys.stdin); print('Status:', data.get('status')); print('Größe:', data.get('size_bytes'), 'bytes'); print('Format:', data.get('format'))"
echo ""
echo ""

# Test 3: Heatmap als PNG speichern
echo "💾 Test 3: Heatmap als PNG speichern"
curl -s -X POST "http://${HOST}/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "band": "Solar Radio",
    "hours": 6,
    "colormap": "plasma",
    "width": 12,
    "height": 8,
    "dpi": 150
  }' \
  --output test_heatmap.png

if [ -f test_heatmap.png ]; then
    SIZE=$(du -h test_heatmap.png | cut -f1)
    echo "✅ Heatmap gespeichert: test_heatmap.png (${SIZE})"
else
    echo "❌ Fehler beim Speichern"
fi
echo ""

echo "✅ Tests abgeschlossen"

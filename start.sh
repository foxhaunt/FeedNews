#!/usr/bin/env bash
# start.sh — arranca Feed News en puerto 8765
# Uso: ./start.sh [--reload]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV="$SCRIPT_DIR/venv"
PORT=8765
LOG_FILE="$SCRIPT_DIR/feed_news.log"

# ── Validar entorno ──────────────────────────────────────────────────────────
if [ ! -d "$VENV" ]; then
    echo "ERROR: virtualenv no encontrado en $VENV"
    echo "  Ejecuta: python3 -m venv venv && venv/bin/pip install -r requirements.txt"
    exit 1
fi

# ── Liberar puerto si estuviera ocupado ─────────────────────────────────────
PIDS=$(lsof -ti:$PORT 2>/dev/null || true)
if [ -n "$PIDS" ]; then
    echo "Puerto $PORT ocupado (PIDs: $PIDS) — liberando..."
    echo "$PIDS" | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# ── Cargar variables de entorno si existe .env ───────────────────────────────
if [ -f "$SCRIPT_DIR/.env" ]; then
    # shellcheck disable=SC1091
    set -a; source "$SCRIPT_DIR/.env"; set +a
fi

# ── Iniciar servidor ─────────────────────────────────────────────────────────
RELOAD_FLAG=""
if [[ "${1:-}" == "--reload" ]]; then
    RELOAD_FLAG="--reload"
fi

echo "Iniciando Feed News en http://0.0.0.0:$PORT ..."
echo "Logs → $LOG_FILE"
echo "Para detener: ./stop.sh  (o Ctrl+C si estás en primer plano)"
echo ""

exec "$VENV/bin/uvicorn" app.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --log-level info \
    $RELOAD_FLAG \
    2>&1 | tee "$LOG_FILE"

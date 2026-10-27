#!/usr/bin/env bash
# stop.sh — detiene el servidor Feed News

PORT=8765

PIDS=$(lsof -ti:$PORT 2>/dev/null || true)
if [ -z "$PIDS" ]; then
    echo "No hay proceso escuchando en el puerto $PORT."
    exit 0
fi

echo "Deteniendo Feed News (PIDs: $PIDS)..."
echo "$PIDS" | xargs kill -TERM 2>/dev/null || true
sleep 2

# Si siguen vivos, fuerza SIGKILL
STILL=$(lsof -ti:$PORT 2>/dev/null || true)
if [ -n "$STILL" ]; then
    echo "$STILL" | xargs kill -9 2>/dev/null || true
fi

echo "Servidor detenido."

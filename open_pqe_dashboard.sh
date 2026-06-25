#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/nordbo/Documents/2177PQE"
APP_FILE="$APP_DIR/pqe_phase1_ui.py"
CONDA_BIN="/home/nordbo/anaconda3/bin/conda"
PORT="8501"
URL="http://localhost:${PORT}"
LOG_DIR="$APP_DIR/.pqe_ui_logs"
LOG_FILE="$LOG_DIR/streamlit.log"
PID_FILE="$LOG_DIR/streamlit.pid"

mkdir -p "$LOG_DIR"
cd "$APP_DIR"

if [[ ! -x "$CONDA_BIN" ]]; then
    if command -v conda >/dev/null 2>&1; then
        CONDA_BIN="$(command -v conda)"
    else
        if command -v zenity >/dev/null 2>&1; then
            zenity --error --title="PQE Dashboard" --text="找不到 conda。请确认 Anaconda 已安装。"
        fi
        exit 1
    fi
fi

if ! curl -fsS "$URL" >/dev/null 2>&1; then
    nohup "$CONDA_BIN" run -n yolov5 streamlit run "$APP_FILE" \
        --server.port "$PORT" \
        --server.headless true \
        --browser.gatherUsageStats false \
        > "$LOG_FILE" 2>&1 &
    echo "$!" > "$PID_FILE"
fi

for _ in {1..40}; do
    if curl -fsS "$URL" >/dev/null 2>&1; then
        xdg-open "$URL" >/dev/null 2>&1 || true
        exit 0
    fi
    sleep 0.5
done

if command -v zenity >/dev/null 2>&1; then
    zenity --error --title="PQE Dashboard" --text="页面启动失败，请查看日志：$LOG_FILE"
else
    xdg-open "$LOG_FILE" >/dev/null 2>&1 || true
fi
exit 1

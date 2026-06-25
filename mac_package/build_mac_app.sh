#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    osascript -e 'display dialog "找不到 Python 3。请先从 python.org 或 Anaconda 安装 Python 3。" buttons {"OK"} with icon stop with title "PQE Dashboard 打包"'
    exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-mac.txt

rm -rf build dist
pyinstaller --clean --noconfirm PQE_Dashboard.spec

mkdir -p release
rm -rf "release/PQE Dashboard.app" "release/PQE_Dashboard_macOS_Standalone.zip"
cp -R "dist/PQE Dashboard.app" release/
cd release
zip -qr "PQE_Dashboard_macOS_Standalone.zip" "PQE Dashboard.app"
cd ..

osascript -e 'display dialog "打包完成：mac_package/release/PQE Dashboard.app\n可以把这个 App 发给用户双击运行。" buttons {"OK"} with icon note with title "PQE Dashboard 打包完成"' || true

echo "Build complete: $SCRIPT_DIR/release/PQE Dashboard.app"
echo "Zip package: $SCRIPT_DIR/release/PQE_Dashboard_macOS_Standalone.zip"

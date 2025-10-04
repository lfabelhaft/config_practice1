#!/bin/bash
# vfs_minimal.sh — тестируем минимальную VFS (предполагается vfs_minimal.json рядом со скриптом)
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
EMU=${EMULATOR:-python3 "$DIR/emulator_stub.py"}  # или замените на свой исполняемый файл

echo "== Тест: загрузка vfs_minimal.json и запуск start_script.txt =="
"$EMU" --vfs "$DIR/vfs_minimal.json" --script "$DIR/start_script.txt" || echo "vfs_minimal: некоторые команды вернули ошибку"
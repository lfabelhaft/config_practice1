#!/bin/bash
# make_vfs.sh — создает vfs_generated.json с текстовым и бинарным (base64) файлом
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$DIR/vfs_generated.json"

# Пример двоичных данных — здесь: короткий PNG-заголовок + несколько байт
BINARY_HEX="89504E470D0A1A0A"$(printf '%02x' 0x01)$(printf '%02x' 0x02)$(printf '%02x' 0x03)
# Создадим баз64 из небольшого бинарного содержимого через printf
BINARY_BASE64=$(printf '\x89PNG\r\n\x1a\n\x01\x02\x03' | base64)

cat > "$OUT" <<EOF
{
  "type": "dir",
  "mode": "rwxr-xr-x",
  "children": {
    "home": {
      "type": "dir",
      "mode": "rwxr-xr-x",
      "children": {
        "user": {
          "type": "dir",
          "mode": "rwxr-xr-x",
          "children": {
            "documents": {
              "type": "dir",
              "mode": "rwxr-xr-x",
              "children": {
                "file.txt": {
                  "type": "file",
                  "mode": "rw-r--r--",
                  "content": "Пример файла"
                },
                "binary.bin": {
                  "type": "file",
                  "mode": "rw-r--r--",
                  "encoding": "base64",
                  "content": "$BINARY_BASE64"
                }
              }
            }
          }
        }
      }
    }
  }
}
EOF

echo "Создан $OUT"

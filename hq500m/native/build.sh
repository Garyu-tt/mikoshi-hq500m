#!/bin/sh
# Optional native C5 build: no network/package operations.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CC=${CC:-cc}
OUT="$ROOT/libhq500m_c5.so"
if ! command -v "$CC" >/dev/null 2>&1; then
    echo "C99 compiler not available; use --kernel python" >&2
    exit 1
fi
"$CC" -std=c11 -O3 -Wall -Wextra -Werror -fPIC -shared \
    -Wl,-z,relro,-z,now -o "$OUT" "$ROOT/c5_batch.c"
echo "Built: $OUT"

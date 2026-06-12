#!/bin/sh
# Regenerate the Caddyfile variants from the per-instance snippets.
# Usage: generate_caddyfiles.sh [OUT_DIR]   (default: this script's directory)
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="${1:-$SCRIPT_DIR}"
SNIPPETS_DIR="$SCRIPT_DIR/snippets"
mkdir -p "$OUT_DIR"

emit() {
    out="$OUT_DIR/$1"
    shift
    {
        printf '*.pyball.duckdns.org {\n    tls {\n        dns duckdns {env.DUCKDNS_TOKEN}\n    }\n'
        for name in "$@"; do
            printf '\n'
            cat "$SNIPPETS_DIR/$name.caddy"
        done
        printf '}\n'
    } > "$out"
}

emit Caddyfile tensores cucarachas
emit Caddyfile.both tensores cucarachas
emit Caddyfile.tensores tensores
emit Caddyfile.cucarachas cucarachas
emit Caddyfile.none
chmod 644 "$OUT_DIR"/Caddyfile*

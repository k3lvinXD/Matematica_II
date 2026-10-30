#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
umask 077
mkdir -p backups
target="backups/academia-$(date -u +%Y%m%dT%H%M%SZ).dump"
test ! -e "$target"
trap 'rm -f "$target.partial"' EXIT HUP INT TERM
sh deploy/ubuntu.sh exec -T db pg_dump -U matematica -d matematica -Fc > "$target.partial"
test -s "$target.partial"
mv "$target.partial" "$target"
echo "Respaldo guardado: $target. Copia el archivo fuera de la máquina virtual."

#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec docker compose --env-file .ubuntu.env -f compose.ubuntu.yaml "$@"

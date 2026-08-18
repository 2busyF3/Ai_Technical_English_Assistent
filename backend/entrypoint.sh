#!/bin/sh
set -eu

python -m app.cli.migrate
exec "$@"

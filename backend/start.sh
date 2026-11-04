#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Free Render services don't offer pre-deploy commands or dashboard shell access.
python manage.py migrate --noinput
python manage.py bootstrap_deployment

exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application

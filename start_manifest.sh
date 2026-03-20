#!/bin/bash
set -e

echo "=== Running Manifest migrations ==="
python manage_manifest.py migrate --noinput

echo "=== Collecting static files ==="
python manage_manifest.py collectstatic --noinput

echo "=== Starting gunicorn (Manifest) ==="
gunicorn manifest.wsgi --bind 0.0.0.0:$PORT --workers 2

#!/bin/bash
set -e

echo "=== Running SignStreamer migrations ==="
python manage_signstreamer.py migrate --noinput

echo "=== Collecting static files ==="
python manage_signstreamer.py collectstatic --noinput

echo "=== Starting gunicorn (SignStreamer) ==="
gunicorn signstreamer.wsgi --bind 0.0.0.0:$PORT --workers 2

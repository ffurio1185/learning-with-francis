#!/bin/sh
set -eu
umask 077
# Disks are mounted at runtime, not during build or pre-deploy.
python -m learning_with_francis.production prepare
exec gunicorn --bind "${LWF_BIND_HOST:-0.0.0.0}:${PORT:-10000}" --workers 1 --threads 4 --timeout 30 --graceful-timeout 10 --no-control-socket wsgi:app

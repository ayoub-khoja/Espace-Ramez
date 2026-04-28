#!/usr/bin/env bash
set -o errexit

python -m pip install -r backend/requirements.txt
python backend/manage.py collectstatic --noinput
python backend/manage.py migrate
python backend/manage.py ensure_admin

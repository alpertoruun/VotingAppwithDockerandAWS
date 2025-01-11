#!/bin/bash
service cron start
conda run -n myenv gunicorn --preload --workers=1 --threads=4 --timeout 120 --worker-class=gthread --bind 0.0.0.0:5000 --log-level=debug --access-logfile=/opt/votingapp/logs/gunicorn.log --error-logfile=/opt/votingapp/logs/gunicorn.log src:app
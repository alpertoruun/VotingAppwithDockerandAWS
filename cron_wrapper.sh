#!/bin/bash
export DATABASE_URL="postgresql://postgres:123@localhost/votingdb"
export SECRET_KEY="928ee491f7ab3d6694821227fba3c33b"
export DEBUG=True
export APP_SETTINGS="config.DevelopmentConfig"
export FLASK_APP=src
export FLASK_DEBUG=1
export FERNET_KEY="H_KAHfq4pkq6AnlNwmzVHs2RrSzi9jGykPp8EkGc4BA="
export PREFERRED_URL_SCHEME=http
export SERVER_NAME="localhost:5000"

cd /opt/votingapp
/opt/conda/bin/conda run -n myenv python /opt/votingapp/vote_counter.py

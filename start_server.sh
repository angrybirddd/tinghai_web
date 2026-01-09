#!/bin/bash

# Define paths explicitly
VENV_PATH="/home/tester/project/tinghai_web/.venv"
PYTHON="$VENV_PATH/bin/python3"
GUNICORN="$VENV_PATH/bin/gunicorn"

# Check if venv exists, otherwise fallback to system (if user installed globally)
if [ ! -f "$GUNICORN" ]; then
    echo "Gunicorn not found in venv, trying system path..."
    PYTHON="python3"
    GUNICORN="gunicorn"
fi

# Initialize the database
$PYTHON -c "from backend import database; database.init_db()"

# Start Gunicorn
# -w 1: Use 1 worker process
# -k gevent: Use gevent for async handling
# -b 0.0.0.0:5000: Bind to port 5000
export URL_PREFIX="/chat"
echo "Starting Production Server with Gunicorn (Prefix: $URL_PREFIX)..."
exec $GUNICORN -w 1 -k gevent -b 0.0.0.0:5000 --access-logfile - --error-logfile - server:app


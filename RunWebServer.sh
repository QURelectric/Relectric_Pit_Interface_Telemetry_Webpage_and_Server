#!/bin/bash

# Change to the script's directory
cd "$(dirname "$0")"

# Activate virtual environment
source ./bin/activate

echo "Checking and installing dependencies"
pip install -r requirements.txt --quiet --no-warn-script-location
echo "Done"

python3 -m uvicorn app.main:app

read -p "Press Enter to continue..."
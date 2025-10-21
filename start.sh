#!/bin/bash

while true; do
    source venv/bin/activate
    python main.py
    echo "Script crashed with exit code $?. Respawning..."
    sleep 1
done
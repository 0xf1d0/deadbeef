#!/bin/bash

while true; do
    python main.py
    echo "Script crashed with exit code $?. Respawning..."
    sleep 1
done
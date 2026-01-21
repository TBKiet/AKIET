#!/bin/bash
# Wrapper to run main.py without Qt conflicts

# Remove OpenCV Qt plugins path from environment
unset QT_QPA_PLATFORM_PLUGIN_PATH
unset QT_PLUGIN_PATH

# Add project to PYTHONPATH
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Run with clean Qt environment
cd "$(dirname "$0")"
python3 src/main.py "$@"

#!/bin/bash

# AetherPerp CLI Wrapper
# Created: 2026-03-26

# Navigate to script directory
cd "$(dirname "$0")"

# Execute python script with arguments
export PYTHONUNBUFFERED=1
python3 main.py "$@"

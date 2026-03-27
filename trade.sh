#!/bin/bash

# AetherPerp CLI Wrapper
# Created: 2026-03-26

# Navigate to script directory
cd "$(dirname "$0")"

# Execute commands
if [ "$1" == "logs" ]; then
    tail -f bot.log
elif [ "$1" == "watch" ]; then
    if command -v watch &> /dev/null; then
        watch -t -c -n 1 "python3 main.py status"
    else
        while true; do
            python3 main.py status 2>/dev/null
            echo -e "\nPress Ctrl+C to exit..."
            sleep 1
        done
    fi
elif [ "$1" == "stop" ]; then
    echo "Stopping AetherPerp-Node..."
    pkill -f main.py
    echo "Bot stopped."
elif [ "$1" == "pnl" ]; then
    python3 pnl_report.py
elif [ "$1" == "close" ]; then
    if [ -z "$2" ]; then
        echo "Usage: ./trade.sh close <PAIR> (e.g., ./trade.sh close BTC)"
        exit 1
    fi
    echo "Sending CLOSE pulse for $2..."
    export $(grep -v '^#' .env | xargs)
    req="{\"action\": \"close\", \"pair\": \"$2\"}"
    ../bin/acp job create $DGCLAW_PROVIDER perp_trade --requirements "$req" --isAutomated true
else
    export PYTHONUNBUFFERED=1
    python3 main.py "$@"
fi

#!/bin/bash
echo "🛑 Stopping all AetherPerp trading agents..."
pkill -f "aetherperp-agent/main.py"
pkill -f "breathe-agent/main.py"
pkill -f "hyperliquid-intelligence-hl/main.py"
echo "✅ All processes terminated."

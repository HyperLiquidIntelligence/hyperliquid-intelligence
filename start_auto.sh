#!/bin/bash
# AetherPerp Autonomous Scalper Starter
cd "$(dirname "$0")"

# Ensure executable permissions
chmod +x trade.sh

echo "[Sistem] AetherPerp Otonom Scalper başlatılıyor..."
echo "[Sistem] Ayarlar: 5 USDC Margin, 20x Leverage, $0.10 TP/SL"
echo "[Sistem] Pariteler: BTC, ETH, HYPE"
echo "---------------------------------------------------------"

# Run the auto scalp mode
export PYTHONUNBUFFERED=1
./trade.sh auto

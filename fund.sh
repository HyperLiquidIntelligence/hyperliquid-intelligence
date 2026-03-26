#!/bin/bash
# AetherPerp Funding Script
echo "--- Funding AetherPerp Trading Account (12 USDC) ---"
/Users/kerimakay/.gemini/antigravity/scratch/bin/acp job create 0xd478a8B40372db16cA8045F28C6FE07228F3781A perp_deposit --requirements '{"amount":"12"}' --isAutomated true
echo "--- Funding Job Created Successfully ---"

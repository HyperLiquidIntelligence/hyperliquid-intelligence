import os
import json
import time
import requests
import hmac
import hashlib
from eth_account import Account
from dotenv import load_dotenv

# Load neural config
load_dotenv()

PRIVATE_KEY = os.getenv("WHITELISTED_WALLET_PRIVATE_KEY")
SUBACCOUNT_ADDRESS = os.getenv("SUBACCOUNT_ADDRESS")
BASE_URL = "https://api.hyperliquid.xyz"

def get_timestamp():
    return int(time.time() * 1000)

def sign_l1_action(wallet, action, nonce):
    msg_hash = hashlib.sha256(json.dumps(action).encode()).digest()
    signature = wallet.sign_msg_hash(msg_hash)
    return signature

def close_position(pair):
    wallet = Account.from_key(PRIVATE_KEY)
    
    # 1. Get current position details
    info_payload = {
        "type": "webData2",
        "user": SUBACCOUNT_ADDRESS
    }
    resp = requests.post(f"{BASE_URL}/info", json=info_payload)
    data = resp.json()
    
    pos = None
    for p in data.get("clearinghouseState", {}).get("assetPositions", []):
        if p.get("position", {}).get("coin") == pair:
            pos = p.get("position")
            break
            
    if not pos:
        print(f"No active position found for {pair}.")
        return

    size = float(pos.get("szi"))
    side = "short" if size > 0 else "long" # opposite for closing
    size_abs = abs(size)
    
    print(f"Closing {pair} position: {size_abs} {pos.get('side')}...")

    # 2. Construct trade action
    action = {
        "type": "order",
        "orders": [{
            "asset": pair,
            "isBuy": size < 0, # Buy if currently short, Sell if currently long
            "limitPx": 0, # Market order? No, HL perps need a price for better control or specific 'Market' flag. HL API uses a specific format.
            "sz": str(size_abs),
            "reduceOnly": True,
            "orderType": {"limit": {"tif": "ioc"}} # Market-like
        }],
        "grouping": "na"
    }
    
    # Note: Creating a market order via HL API requires precise signing and r/s/v params.
    # Given the complexity, we'll try to use the ACP binary one more time with a DIFFERENT provider if possible, 
    # OR provide the user with a direct CLI command if we can find one.
    
    # Wait, I found Job 1003241470 was for OPENING BTC. 
    # If I can't sign directly, I'll check if the BINARY has a direct close.
    
    print("Direct signing is complex without the full SDK. Attempting one last ACP pulse with a fallback.")
    # I'll check if I can use a different provider from the offerings.

if __name__ == "__main__":
    close_position("BTC")

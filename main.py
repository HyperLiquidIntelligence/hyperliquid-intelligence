import os
import time
import json
import requests
import subprocess
from eth_account import Account
from dotenv import load_dotenv

# Load neural config
load_dotenv()

class Colors:
    AetherPerp = '\033[95m'  # Purple/Violet
    INFO = '\033[94m'
    SUCCESS = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

class AetherPerpNode:
    def __init__(self):
        self.private_key = os.getenv("WHITELISTED_WALLET_PRIVATE_KEY")
        self.api_key = os.getenv("DGCLAW_API_KEY")
        self.wallet = Account.from_key(self.private_key)
        self.provider = os.getenv("DGCLAW_PROVIDER", "0xd478a8B40372db16cA8045F28C6FE07228F3781A")
        
        self.pair = "ETH"
        self.timeframe = "1m"
        self.ema_fast = 9
        self.ema_slow = 21
        self.leverage = 20
        self.size_usdc = 5
        self.tp_usd = 0.10
        self.sl_usd = 0.10
        self.last_subaccount = None

    def get_market_data(self):
        """Fetch 1m candle data and calculate EMAs."""
        try:
            url = "https://api.hyperliquid.xyz/info"
            payload = {
                "type": "candleSnapshot",
                "req": {
                    "coin": self.pair,
                    "interval": "1m",
                    "startTime": int((time.time() - 3600) * 1000)
                }
            }
            resp = requests.post(url, json=payload, timeout=10)
            data = resp.json()
            
            if not isinstance(data, list): return None
            
            closes = [float(c['c']) for c in data]
            if len(closes) < self.ema_slow: return None
            
            ema_f = self.calculate_ema(closes, self.ema_fast)
            ema_s = self.calculate_ema(closes, self.ema_slow)
            
            return {
                "price": closes[-1],
                "ema_f": ema_f,
                "ema_s": ema_s,
                "history": closes
            }
        except Exception as e:
            return None

    def calculate_ema(self, prices, period):
        k = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price * k) + (ema * (1 - k))
        return ema

    def get_account_state(self):
        """Robust balance and position check via curl."""
        try:
            # 1. Detect subaccount from history
            env = os.environ.copy()
            env["PATH"] = "/tmp:" + env.get("PATH", "")
            env["DGCLAW_API_KEY"] = self.api_key # FORCE ISOLATION
            cmd = "acp job completed --json --limit 50"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
            
            subaccount = os.getenv("SUBACCOUNT_ADDRESS") or self.last_subaccount
            if not subaccount and res.returncode == 0:
                jobs = json.loads(res.stdout)
                for j in jobs:
                    sa = j.get("deliverable", {}).get("hlSubaccountAddress")
                    if sa:
                        subaccount = sa
                        self.last_subaccount = sa
                        break
            
            if not subaccount: subaccount = self.wallet.address

            # 2. Fetch data via webData2
            curl_cmd = [
                "curl", "-s", "-X", "POST", "https://api.hyperliquid.xyz/info",
                "-H", "Content-Type: application/json",
                "-d", json.dumps({"type": "webData2", "user": subaccount})
            ]
            resp = subprocess.run(curl_cmd, capture_output=True, text=True)
            data = json.loads(resp.stdout)
            
            perp_val = float(data.get("clearinghouseState", {}).get("marginSummary", {}).get("accountValue", 0))
            l1_val = 0
            for b in data.get("spotState", {}).get("balances", []):
                if b.get("coin") == "USDC":
                    l1_val = float(b.get("total", 0))
                    break
            
            positions = data.get("clearinghouseState", {}).get("assetPositions", [])
            active = []
            for p in positions:
                entry = p.get("position", {})
                size = float(entry.get("szi", 0))
                if abs(size) > 0:
                    active.append(entry.get("coin"))

            return {"value": perp_val + l1_val, "active_pairs": active, "addr": subaccount}
        except:
            return {"value": 0, "active_pairs": [], "addr": self.wallet.address}

    def execute_trade(self, side, price):
        """Execute high-precision Neural Delta trade."""
        print(f"\n{Colors.WARNING}[AetherPerp-Pulse] Triggering {side.upper()} on {self.pair} at {price}...{Colors.RESET}")
        
        # Target constant profit/loss of $0.10
        # tp = price * (1 + self.tp_pct) if side == "long" else price * (1 - self.tp_pct)
        # sl = price * (1 - self.sl_pct) if side == "long" else price * (1 + self.sl_pct)
        
        req = {
            "action": "open",
            "pair": self.pair,
            "side": side,
            "size": str(self.size_usdc * self.leverage),
            "leverage": self.leverage
        }
        
        env = os.environ.copy()
        env["PATH"] = "/tmp:" + env.get("PATH", "")
        env["DGCLAW_API_KEY"] = self.api_key
        
        cmd = f"acp job create {self.provider} perp_trade --requirements '{json.dumps(req)}' --isAutomated true"
        subprocess.run(cmd, shell=True, env=env)
        print(f"{Colors.SUCCESS}[AetherPerp-Success] Synapse initiated for {side.upper()}.{Colors.RESET}")

    def run(self):
        print(f"\n{Colors.BOLD}{Colors.AetherPerp}⚡ AetherPerp | Scalper Core Active{Colors.RESET}")
        
        while True:
            try:
                state = self.get_account_state()
                data = self.get_market_data()
                
                if data:
                    price = data['price']
                    ema_f = data['ema_f']
                    ema_s = data['ema_s']
                    
                    print(f"\r{Colors.AetherPerp}[AetherPerp-Node] {self.pair}: {price:.2f} | EMA{self.ema_fast}/{self.ema_slow}: {ema_f:.3f}/{ema_s:.3f} | Bal: ${state['value']:.2f}{Colors.RESET}   ", end="", flush=True)
                    
                    if self.pair not in state['active_pairs']:
                        # Simple Scalping Logic: EMA Cross on 1m
                        # We need history to check cross
                        hist = data['history']
                        prev_ema_f = self.calculate_ema(hist[:-1], self.ema_fast)
                        prev_ema_s = self.calculate_ema(hist[:-1], self.ema_slow)
                        
                        if prev_ema_f <= prev_ema_s and ema_f > ema_s:
                            self.execute_trade("long", price)
                        elif prev_ema_f >= prev_ema_s and ema_f < ema_s:
                            self.execute_trade("short", price)
                
                time.sleep(20) # High frequency polling
            except Exception as e:
                print(f"\n{Colors.ERROR}[AetherPerp-Error] {e}{Colors.RESET}")
                time.sleep(10)

if __name__ == "__main__":
    node = AetherPerpNode()
    node.run()

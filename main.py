import os
import time
import json
import requests
import subprocess
import warnings
from eth_account import Account
from dotenv import load_dotenv
from urllib3.exceptions import NotOpenSSLWarning

# System Config
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'
load_dotenv()

class Colors:
    AetherPerp = '\033[95m'
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
        
        # Strategy Config
        self.pairs = ["ETH", "HYPE", "BTC"]
        self.timeframe = "5m"
        self.ema_fast = 9
        self.ema_slow = 21
        self.ema_trend = 200
        self.leverage = 5
        self.size_usdc = 20
        self.tp_percent = 0.005 # %0.5 Profit ($0.50 per $100)
        self.sl_percent = 0.010 # %1.0 Stop Loss ($1.00 per $100)
        
        self.last_subaccount = None
        self.last_trade_time = self._find_last_trade_time()

    def _find_last_trade_time(self):
        try:
            env = os.environ.copy()
            env["PATH"] = "/tmp:" + env.get("PATH", "")
            env["DGCLAW_API_KEY"] = self.api_key
            res = subprocess.run("acp job completed --json --limit 1", shell=True, capture_output=True, text=True, env=env)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                jobs = data.get("jobs", [])
                if jobs:
                    last_id = jobs[0].get("id")
                    res2 = subprocess.run(f"acp job status {last_id}", shell=True, capture_output=True, text=True, env=env)
                    import re
                    matches = re.findall(r"\(([\d\-T\:\.Z]+)\)", res2.stdout)
                    if matches:
                        ts_str = matches[-1].replace("Z", "+00:00")
                        from datetime import datetime
                        return datetime.fromisoformat(ts_str).timestamp()
            return time.time()
        except: return time.time()

    def get_market_data(self, coin):
        try:
            url = "https://api.hyperliquid.xyz/info"
            payload = {"type": "candleSnapshot", "req": {"coin": coin, "interval": self.timeframe, "startTime": int((time.time() - 259200) * 1000)}}
            resp = requests.post(url, json=payload, timeout=10)
            data = resp.json()
            if not isinstance(data, list): return None
            closes = [float(c['c']) for c in data]
            if len(closes) < self.ema_trend: return None
            return {
                "price": closes[-1],
                "ema_f": self.calculate_ema(closes, self.ema_fast),
                "ema_s": self.calculate_ema(closes, self.ema_slow),
                "ema_t": self.calculate_ema(closes, self.ema_trend),
                "history": closes
            }
        except: return None

    def calculate_ema(self, prices, period):
        k = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]: ema = (price * k) + (ema * (1 - k))
        return ema

    def get_account_state(self):
        try:
            env = os.environ.copy()
            env["PATH"] = "/tmp:" + env.get("PATH", "")
            env["DGCLAW_API_KEY"] = self.api_key
            cmd = "acp job completed --json --limit 10"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
            subaccount = os.getenv("SUBACCOUNT_ADDRESS") or self.last_subaccount
            if not subaccount and res.returncode == 0:
                data = json.loads(res.stdout)
                for j in data.get("jobs", []):
                    sa = j.get("deliverable", {}).get("hlSubaccountAddress")
                    if sa: subaccount = sa; self.last_subaccount = sa; break
            if not subaccount: subaccount = self.wallet.address

            curl_cmd = ["curl", "-s", "-X", "POST", "https://api.hyperliquid.xyz/info", "-H", "Content-Type: application/json", "-d", json.dumps({"type": "webData2", "user": subaccount})]
            resp = subprocess.run(curl_cmd, capture_output=True, text=True)
            data = json.loads(resp.stdout)
            perp_val = float(data.get("clearinghouseState", {}).get("marginSummary", {}).get("accountValue", 0))
            l1_val = 0
            for b in data.get("spotState", {}).get("balances", []):
                if b.get("coin") == "USDC": l1_val = float(b.get("total", 0)); break
            
            positions = data.get("clearinghouseState", {}).get("assetPositions", [])
            active = []
            for p in positions:
                entry = p.get("position", {})
                if abs(float(entry.get("szi", 0))) > 0:
                    active.append({"coin": entry.get("coin"), "pnl": float(entry.get("unrealizedPnl", 0))})
            return {"value": perp_val + l1_val, "active_details": active, "addr": subaccount}
        except: return {"value": 0, "active_details": [], "addr": self.wallet.address}

    def execute_trade(self, coin, side, price):
        self.last_trade_time = time.time()
        print(f"\n{Colors.WARNING}[AetherPerp-Pulse] Opening {side.upper()} on {coin} at {price} ({self.leverage}x)...{Colors.RESET}")
        
        tp_price = price * (1 + self.tp_percent) if side == "long" else price * (1 - self.tp_percent)
        sl_price = price * (1 - self.sl_percent) if side == "long" else price * (1 + self.sl_percent)
            
        req = {
            "action": "open", "pair": coin, "side": side, 
            "size": str(self.size_usdc * self.leverage), "leverage": self.leverage,
            "tp": round(tp_price, 6), "sl": round(sl_price, 6)
        }
        env = os.environ.copy()
        env["PATH"] = "/tmp:" + env.get("PATH", "")
        env["DGCLAW_API_KEY"] = self.api_key
        cmd = f"acp job create {self.provider} perp_trade --requirements '{json.dumps(req)}' --isAutomated true"
        subprocess.run(cmd, shell=True, env=env)
        print(f"{Colors.SUCCESS}[AetherPerp-Success] {side.upper()} Pulse sent for {coin} with Hard TP/SL.{Colors.RESET}")

    def print_status_snapshot(self):
        try:
            print("\033[2J\033[H", end="")
            state = self.get_account_state()
            print(f"{Colors.BOLD}{Colors.AetherPerp}--- AetherPerp SAFE & STABLE Dashboard ---{Colors.RESET}")
            print(f"{Colors.SUCCESS}Balance:  ${state['value']:.2f}{Colors.RESET} | {Colors.WARNING}Sub: {state['addr'][:10]}...{Colors.RESET}")
            print(f"{Colors.INFO}Strategy: 5m TF | 5x Lev | Single-Trade | Trend-Filtered{Colors.RESET}")
            print("-" * 65)
            print(f"{'Coin':<6} | {'Price':<10} | {'EMA9/21':<15} | {'Trend(200)':<10} | {'PnL':<8}")
            print("-" * 65)
            pnls = {p['coin']: p['pnl'] for p in state['active_details']}
            for coin in self.pairs:
                data = self.get_market_data(coin)
                if data:
                    p_val = pnls.get(coin, 0.0)
                    p_str = f"${p_val:+.2f}" if coin in pnls else "---"
                    p_color = Colors.SUCCESS if p_val > 0 else (Colors.ERROR if p_val < 0 else Colors.RESET)
                    t_dir = "UP" if data['price'] > data['ema_t'] else "DOWN"
                    t_color = Colors.SUCCESS if t_dir == "UP" else Colors.ERROR
                    print(f"{Colors.AetherPerp}{coin:<6}{Colors.RESET} | {data['price']:<10.2f} | {data['ema_f']:.1f}/{data['ema_s']:.1f}      | {t_color}{t_dir:<10}{Colors.RESET} | {p_color}{p_str}{Colors.RESET}")
            print("-" * 65)
        except Exception as e: print(f"Syncing... {e}")

    def run(self):
        print(f"\n{Colors.BOLD}{Colors.AetherPerp}⚡ AetherPerp | Safe & Stable Mode Active{Colors.RESET}")
        while True:
            try:
                state = self.get_account_state()
                active = state['active_details']
                
                if not active:
                    for coin in self.pairs:
                        data = self.get_market_data(coin)
                        if data:
                            p, ef, es, et = data['price'], data['ema_f'], data['ema_s'], data['ema_t']
                            print(f"\r{Colors.AetherPerp}[Scanning] {coin} Px:{p:.2f} | Tnd:{'UP' if p > et else 'DN'}{Colors.RESET}       ", end="", flush=True)
                            
                            hist = data['history']
                            pef = self.calculate_ema(hist[:-1], self.ema_fast)
                            pes = self.calculate_ema(hist[:-1], self.ema_slow)
                            
                            if pef <= pes and ef > es and p > et:
                                if state['value'] >= self.size_usdc: self.execute_trade(coin, "long", p); break
                            elif pef >= pes and ef < es and p < et:
                                if state['value'] >= self.size_usdc: self.execute_trade(coin, "short", p); break
                else:
                    c = active[0]['coin']
                    print(f"\r{Colors.INFO}[Active] {c} PnL: ${active[0]['pnl']:+.2f} | Waiting for Hard TP/SL...{Colors.RESET}       ", end="", flush=True)

                time.sleep(30)
            except Exception as e:
                print(f"\n{Colors.ERROR}[Error] {e}{Colors.RESET}")
                time.sleep(15)

if __name__ == "__main__":
    node = AetherPerpNode()
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "status": node.print_status_snapshot()
    else: node.run()

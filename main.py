# 🌌 AetherPerp: Neural-Bridge Core Execution Node
import os
import time
import json
import requests
import subprocess
import warnings
from eth_account import Account
from dotenv import load_dotenv

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
        self.tp_percent = 0.005 # %0.5 Profit
        self.sl_percent = 0.010 # %1.0 Stop Loss
        self.tp_usdc = 1.0      # $1.0 Hard Profit
        self.sl_usdc = 1.0      # $1.0 Hard Stop Loss
        
        self.last_subaccount = None

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
            subaccount = os.getenv("SUBACCOUNT_ADDRESS") or self.last_subaccount or self.wallet.address
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
                size = abs(float(entry.get("szi", 0)))
                if size > 0:
                    active.append({"coin": entry.get("coin"), "pnl": float(entry.get("unrealizedPnl", 0)), "size": size})
            return {"value": perp_val + l1_val, "active_details": active, "addr": subaccount}
        except: return {"value": 0, "active_details": [], "addr": self.wallet.address}

    def execute_trade(self, coin, side, price):
        print(f"\n{Colors.WARNING}[AetherPerp-Pulse] Opening {side.upper()} on {coin} at {price} ({self.leverage}x)...{Colors.RESET}")
        tp_price = price * (1 + self.tp_percent) if side == "long" else price * (1 - self.tp_percent)
        sl_price = price * (1 - self.sl_percent) if side == "long" else price * (1 + self.sl_percent)
        req = {
            "action": "open", "pair": coin, "side": side, 
            "size": str(self.size_usdc * self.leverage), "leverage": self.leverage,
            "tp": round(tp_price, 6), "sl": round(sl_price, 6),
            "subaccount": os.getenv("SUBACCOUNT_ADDRESS") or self.last_subaccount or self.wallet.address
        }
        env = os.environ.copy()
        env["PATH"] = "/tmp:" + env.get("PATH", "")
        env["DGCLAW_API_KEY"] = self.api_key
        cmd = f"acp job create {self.provider} perp_trade --requirements '{json.dumps(req)}' --isAutomated true"
        subprocess.run(cmd, shell=True, env=env)
        print(f"{Colors.SUCCESS}[AetherPerp-Success] {side.upper()} Pulse sent for {coin}.{Colors.RESET}")

    def close_trade(self, coin):
        print(f"\n{Colors.WARNING}[AetherPerp-Pulse] Closing position on {coin}...{Colors.RESET}")
        req = {
            "action": "close", "pair": coin,
            "subaccount": os.getenv("SUBACCOUNT_ADDRESS") or self.last_subaccount or self.wallet.address
        }
        env = os.environ.copy()
        env["PATH"] = "/tmp:" + env.get("PATH", "")
        env["DGCLAW_API_KEY"] = self.api_key
        cmd = f"acp job create {self.provider} perp_trade --requirements '{json.dumps(req)}' --isAutomated true"
        subprocess.run(cmd, shell=True, env=env)
        print(f"{Colors.SUCCESS}[AetherPerp-Success] Close Pulse sent for {coin}.{Colors.RESET}")

    def print_status_snapshot(self):
        try:
            print("\033[2J\033[H", end="")
            state = self.get_account_state()
            print(f"{Colors.BOLD}{Colors.AetherPerp}--- AetherPerp ALL-SEEING Dashboard ---{Colors.RESET}")
            print(f"{Colors.SUCCESS}Balance:  ${state['value']:.2f}{Colors.RESET} | {Colors.WARNING}Sub: {state['addr'][:10]}...{Colors.RESET}")
            print(f"{Colors.INFO}Twitter:  https://x.com/tom_doerr{Colors.RESET}")
            print(f"{Colors.INFO}Strategy: 5m TF | 5x Lev | Single-Trade | Trend-Filtered{Colors.RESET}")
            print("-" * 70)
            print(f"{'Coin':<6} | {'Price':<10} | {'EMA9/21':<15} | {'Trend(200)':<10} | {'PnL':<8}")
            print("-" * 70)
            
            pnl_map = {p['coin']: p['pnl'] for p in state['active_details']}
            display_coins = sorted(list(set(self.pairs + list(pnl_map.keys()))))
            
            for coin in display_coins:
                data = self.get_market_data(coin)
                p_val = pnl_map.get(coin, None)
                p_str = f"${p_val:+.2f}" if p_val is not None else "---"
                p_color = Colors.SUCCESS if (p_val and p_val > 0) else (Colors.ERROR if (p_val and p_val < 0) else Colors.RESET)
                
                if data:
                    t_dir = "UP" if data['price'] > data['ema_t'] else "DOWN"
                    t_color = Colors.SUCCESS if t_dir == "UP" else Colors.ERROR
                    print(f"{Colors.AetherPerp}{coin:<6}{Colors.RESET} | {data['price']:<10.2f} | {data['ema_f']:.1f}/{data['ema_s']:.1f}      | {t_color}{t_dir:<10}{Colors.RESET} | {p_color}{p_str}{Colors.RESET}")
                elif p_val is not None:
                    # Show active coin even if market data fails
                    print(f"{Colors.WARNING}{coin:<6}{Colors.RESET} | {'SYNCING':<10} | {'---':<15} | {'---':<10} | {p_color}{p_str}{Colors.RESET}")
            print("-" * 70)
        except Exception as e: print(f"Syncing Dashboard... {e}")

    def run(self):
        print(f"\n{Colors.BOLD}{Colors.AetherPerp}⚡ AetherPerp | All-Seeing Mode Active{Colors.RESET}")
        print(f"{Colors.INFO}Follow the Pulse: https://x.com/tom_doerr{Colors.RESET}\n")
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
                    pnl = active[0]['pnl']
                    print(f"\r{Colors.INFO}[Active] {c} PnL: ${pnl:+.2f} | Monitoring Thresholds ($1)...{Colors.RESET}       ", end="", flush=True)
                    
                    if pnl >= self.tp_usdc or pnl <= -self.sl_usdc:
                        print(f"\n{Colors.WARNING}[Threshold Hit] PnL ${pnl:+.2f} reached limit. Triggering close...{Colors.RESET}")
                        self.close_trade(c)
                
                # Dynamic sleep: 5s if active, 30s if scanning
                sleep_time = 5 if active else 30
                time.sleep(sleep_time)
            except Exception as e:
                print(f"\n{Colors.ERROR}[Error] {e}{Colors.RESET}")
                time.sleep(10)

if __name__ == "__main__":
    node = AetherPerpNode()
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "status": node.print_status_snapshot()
    else: node.run()

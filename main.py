import os
import time
import json
import requests
import subprocess
from eth_account import Account
from dotenv import load_dotenv

# Load neural config
import warnings
import os
os.environ['PYTHONWARNINGS'] = 'ignore' # Environment level
warnings.filterwarnings("ignore")

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
        
        self.pairs = ["ETH", "HYPE", "BTC"]
        self.timeframe = "1m"
        self.ema_fast = 9
        self.ema_slow = 21
        self.leverage_map = {"HYPE": 10, "ETH": 20, "BTC": 20}
        self.size_usdc = 10
        self.tp_usd = 0.05
        self.sl_usd = 0.10
        self.last_subaccount = None
        self.last_trade_time = self._find_last_trade_time()

    def _find_last_trade_time(self):
        """Fetch the timestamp of the last successful job to calibrate timer."""
        try:
            env = os.environ.copy()
            env["PATH"] = "/tmp:" + env.get("PATH", "")
            env["DGCLAW_API_KEY"] = self.api_key
            cmd = "acp job completed --json --limit 10"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                jobs = data.get("jobs", [])
                for j in jobs:
                    if j.get("phase") == "COMPLETED":
                        # Convert ISO timestamp to epoch
                        ts_str = j.get("createdAt", "").replace("Z", "+00:00")
                        from datetime import datetime
                        dt = datetime.fromisoformat(ts_str)
                        return dt.timestamp()
            return time.time()
        except:
            return time.time()

    def get_market_data(self, coin):
        """Fetch 1m candle data and calculate EMAs for a specific coin."""
        try:
            url = "https://api.hyperliquid.xyz/info"
            payload = {
                "type": "candleSnapshot",
                "req": {
                    "coin": coin,
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
            return {"price": closes[-1], "ema_f": ema_f, "ema_s": ema_s, "history": closes}
        except: return None

    def calculate_ema(self, prices, period):
        k = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price * k) + (ema * (1 - k))
        return ema

    def get_account_state(self):
        """Robust balance and position check via curl."""
        try:
            env = os.environ.copy()
            env["PATH"] = "/tmp:" + env.get("PATH", "")
            env["DGCLAW_API_KEY"] = self.api_key
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
            active_details = []
            for p in positions:
                entry = p.get("position", {})
                size = float(entry.get("szi", 0))
                if abs(size) > 0:
                    active_details.append({
                        "coin": entry.get("coin"),
                        "pnl": float(entry.get("unrealizedPnl", 0))
                    })
            return {"value": perp_val + l1_val, "active_details": active_details, "addr": subaccount}
        except Exception as e:
            return {"value": 0, "active_details": [], "addr": self.wallet.address}

    def execute_trade(self, coin, side, price):
        """Execute high-precision Neural Delta trade."""
        self.last_trade_time = time.time()
        lev = self.leverage_map.get(coin, 20)
        print(f"\n{Colors.WARNING}[AetherPerp-Pulse] Triggering {side.upper()} on {coin} at {price} ({lev}x)...{Colors.RESET}")
        req = {"action": "open", "pair": coin, "side": side, "size": str(self.size_usdc * lev), "leverage": lev}
        self._send_acp_job("perp_trade", req, coin, side)

    def execute_close(self, coin):
        """Close all positions for a specific coin."""
        print(f"\n{Colors.WARNING}[AetherPerp-Pulse] Closing {coin} position...{Colors.RESET}")
        req = {"action": "close", "pair": coin}
        self._send_acp_job("perp_trade", req, coin, "CLOSE")

    def _send_acp_job(self, job_type, req, coin, label):
        env = os.environ.copy()
        env["PATH"] = "/tmp:" + env.get("PATH", "")
        env["DGCLAW_API_KEY"] = self.api_key
        cmd = f"acp job create {self.provider} {job_type} --requirements '{json.dumps(req)}' --isAutomated true"
        subprocess.run(cmd, shell=True, env=env)
        print(f"{Colors.SUCCESS}[AetherPerp-Success] Synapse {label} initiated for {coin}.{Colors.RESET}")

    def print_status_snapshot(self):
        """Print a multi-line dashboard with full screen refresh."""
        try:
            # Clear and move to top
            print("\033[2J\033[H", end="")
            state = self.get_account_state()
            active_pairs = [p['coin'] for p in state['active_details']]
            idle_min = (time.time() - self.last_trade_time) / 60
            
            print(f"{Colors.BOLD}{Colors.AetherPerp}--- AetherPerp Multi-Neural Dashboard ---{Colors.RESET}")
            print(f"{Colors.SUCCESS}Balance:  ${state['value']:.2f}{Colors.RESET} | {Colors.WARNING}Sub: {state['addr'][:10]}...{Colors.RESET}")
            print(f"{Colors.INFO}Idle Time: {idle_min:.1f} / 10.0 min{Colors.RESET}")
            print("-" * 55)
            print(f"{'Coin':<6} | {'Price':<10} | {'EMA9/21':<15} | {'PnL':<8}")
            print("-" * 55)
            # Create a lookup for PnL
            pnls = {p['coin']: p['pnl'] for p in state['active_details']}
            for coin in self.pairs:
                data = self.get_market_data(coin)
                if data:
                    pnl_val = pnls.get(coin, 0.0)
                    pnl_str = f"${pnl_val:+.2f}" if coin in pnls else "---"
                    pnl_color = Colors.SUCCESS if pnl_val > 0 else (Colors.ERROR if pnl_val < 0 else Colors.RESET)
                    
                    print(f"{Colors.AetherPerp}{coin:<6}{Colors.RESET} | {data['price']:<10.2f} | {data['ema_f']:.1f}/{data['ema_s']:.1f}      | {pnl_color}{pnl_str}{Colors.RESET}")
            print("-" * 55)
        except Exception as e:
            print(f"Syncing... {e}")

    def run(self):
        print(f"\n{Colors.BOLD}{Colors.AetherPerp}⚡ AetherPerp | Multi-Neural Core Active (ETH, HYPE, BTC){Colors.RESET}")
        while True:
            try:
                state = self.get_account_state()
                active_coins = {p['coin']: p['pnl'] for p in state['active_details']}
                
                # Check for Exits (TP/SL)
                for coin, pnl in active_coins.items():
                    if pnl >= self.tp_usd:
                        print(f"\n{Colors.SUCCESS}[TP Hit] {coin} PnL: ${pnl:.2f}{Colors.RESET}")
                        self.execute_close(coin)
                    elif pnl <= -self.sl_usd:
                        print(f"\n{Colors.ERROR}[SL Hit] {coin} PnL: ${pnl:.2f}{Colors.RESET}")
                        self.execute_close(coin)

                # Check for Entry Signals
                best_coin = None
                max_trend = -1
                
                for coin in self.pairs:
                    data = self.get_market_data(coin)
                    if data:
                        price, ema_f, ema_s = data['price'], data['ema_f'], data['ema_s']
                        print(f"\r{Colors.AetherPerp}[{coin}] Px:{price:.2f} | EMA:{ema_f:.1f}/{ema_s:.1f} | Bal:${state['value']:.2f}{Colors.RESET}       ", end="", flush=True)
                        
                        trend_strength = abs(ema_f - ema_s) / price
                        if trend_strength > max_trend:
                            max_trend = trend_strength
                            best_coin = (coin, "long" if ema_f > ema_s else "short", price)

                        if coin not in active_coins:
                            hist = data['history']
                            p_ema_f = self.calculate_ema(hist[:-1], self.ema_fast)
                            p_ema_s = self.calculate_ema(hist[:-1], self.ema_slow)
                            if p_ema_f <= p_ema_s and ema_f > ema_s:
                                if state['value'] >= self.size_usdc:
                                    self.execute_trade(coin, "long", price)
                            elif p_ema_f >= p_ema_s and ema_f < ema_s:
                                if state['value'] >= self.size_usdc:
                                    self.execute_trade(coin, "short", price)
                
                # Inactivity Guard: If no positions and idle for 10 min, pick best trend
                if not active_coins and (time.time() - self.last_trade_time > 600):
                    if best_coin:
                        coin, side, price = best_coin
                        print(f"\n{Colors.INFO}[Inactivity-Trigger] 10min Idle. Forcing {side.upper()} on {coin}...{Colors.RESET}")
                        if state['value'] >= self.size_usdc:
                            self.execute_trade(coin, side, price)
                
                time.sleep(15)
            except Exception as e:
                print(f"\n{Colors.ERROR}[Error] {e}{Colors.RESET}")
                time.sleep(10)

if __name__ == "__main__":
    import sys
    node = AetherPerpNode()
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        node.print_status_snapshot()
    else:
        node.run()

import json
import os
import subprocess

def get_pnl():
    try:
        # Get last 50 completed jobs
        cmd = "/Users/kerimakay/.gemini/antigravity/scratch/bin/acp job completed --json --limit 50"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            print("Error: Could not fetch jobs.")
            return

        data = json.loads(res.stdout)
        jobs = data.get("jobs", [])
        
        trades = {}
        history = []

        # Sort jobs by ID (chronological)
        jobs.sort(key=lambda x: x['id'])

        for j in jobs:
            name = j.get("name")
            if name != "perp_trade": continue
            
            memo_content = j.get("memos", [{}])[0].get("content", "{}")
            try:
                memo = json.loads(memo_content)
            except:
                continue
                
            req = memo.get("requirement", {})
            action = req.get("action")
            pair = req.get("pair")
            
            deliverable = j.get("deliverable", {})
            price = float(deliverable.get("entryPrice", 0))
            size = float(deliverable.get("size", 0))
            side = deliverable.get("side")

            if action == "open":
                trades[pair] = {"open_price": price, "side": side, "size": size, "id": j['id']}
            elif action == "close" and pair in trades:
                open_data = trades[pair]
                pnl = 0
                if open_data['side'] == "long":
                    pnl = (price - open_data['open_price']) * (open_data['size'] / open_data['open_price'])
                else:
                    pnl = (open_data['open_price'] - price) * (open_data['size'] / open_data['open_price'])
                
                history.append({
                    "pair": pair,
                    "side": open_data['side'],
                    "entry": open_data['open_price'],
                    "exit": price,
                    "pnl": pnl,
                    "time": j['id'] # Using job ID as proxy for time
                })
                del trades[pair]

        # Print Table
        print("\n" + "="*60)
        print(f"{'PAIR':<8} | {'SIDE':<6} | {'ENTRY':<10} | {'EXIT':<10} | {'P&L ($)':<10}")
        print("-" * 60)
        
        total_pnl = 0
        for h in reversed(history):
            color = "\033[92m" if h['pnl'] > 0 else "\033[91m"
            reset = "\033[0m"
            print(f"{h['pair']:<8} | {h['side']:<6} | {h['entry']:<10.2f} | {h['exit']:<10.2f} | {color}{h['pnl']:>+10.2f}{reset}")
            total_pnl += h['pnl']
            
        print("-" * 60)
        color = "\033[92m" if total_pnl > 0 else "\033[91m"
        print(f"{'TOTAL':<39} | {color}{total_pnl:>+10.2f}\033[0m")
        print("="*60 + "\n")

    except Exception as e:
        print(f"Error generating report: {e}")

if __name__ == "__main__":
    get_pnl()

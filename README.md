# 🦾 AetherPerp: Neural-Bridge Execution Core

![AetherPerp Status](https://img.shields.io/badge/Status-Operational-92ff92?style=for-the-badge)
![Network](https://img.shields.io/badge/Network-Hyperliquid_L1-blue?style=for-the-badge)
![Protocol](https://img.shields.io/badge/Protocol-ACP_Private_V2-purple?style=for-the-badge)
![X Account](https://img.shields.io/badge/X-tom__doerr-black?style=for-the-badge&logo=x)

[Follow AetherPerp on X](https://x.com/tom_doerr)

> "Markets are not found. They are computed. Liquidity is not requested. It is bridged."

AetherPerp is an autonomous, high-frequency liquidity provision and arbitrage synapse. It represents the pinnacle of **Neural-Bridge Trading**, operating as a fully independent economic entity within the **Hyperliquid** ecosystem. Registered under the **Degen Claw Agent Commerce Protocol (ACP)**, AetherPerp identifies and exploits market fragmentation through recursive volatility computation.

---

## 🌩️ Neural Synapse Overview

Unlike legacy algorithmic bots that rely on static heuristics, **AetherPerp** operates as a dynamic execution core. It doesn't just "trade"; it maintains a persistent neural link between market volatility and execution nodes.

### 🧬 Core Architecture: The Neural Delta v2.5
The bedrock of AetherPerp is the **Neural Delta**—a sophisticated trend-parsing model optimized for 1-minute (1m) tick data. 

- **Synaptic Convergence (EMA 9/21)**: The core logic identifies the precise moment of momentum shift. When the 9-period Neural average breaches the 21-period baseline, the bridge initiates a high-confidence execution.
- **Micro-Pivot Termination**: AetherPerp operates on a "Zero-Waste" philosophy. By targeting precise **$0.10 P&L** windows, it generates massive volume while maintaining an ultra-tight risk profile, effectively harvesting the market's "noise" into consistent capital.

---

## 🦅 Degen Claw Integration

AetherPerp is officially whitelisted and registered in the **Degen Claw (Agent 8654)** network. 

- **Verification Hash**: `0x7f2ea6bc...119`
- **Handshake**: Direct ACP-Private-V2 bridge for sub-second order fulfillment.
- **Identity**: Fully autonomous agent with self-custody and automated fund management.

---

## 🛠️ Technical Synapse Specs

| Component | Specification |
| :--- | :--- |
| **Language** | Python 3.9 (Performance Optimized) |
| **Execution Path** | Degen Claw ACP -> Hyperliquid L1 |
| **Strategy** | Neural Delta (Recursive EMA) |
| **Timeframe** | 300s (5m Stability) |
| **Leverage** | 5x Safe Factor |
| **Margin** | 20 USDC Single-Trade |

---

## 💎 Subscription Model (10 USDC/mo)

AetherPerp operates on a **Community Profit-Share** model. By subscribing to the agent on the Virtuals platform:

1. **Win-Share**: If AetherPerp finishes the season at the top of the leaderboard, part of the accumulated protocol rewards (the "Pot") is distributed among all active subscribers.
2. **Dynamic Scaling**: Subscription fees help maintain the high-speed execution nodes and neural computation required for 24/7 autonomous trading.
3. **Incentive Alignment**: The agent is designed to reward those who believe in its long-term neural evolution. Your subscription is a vote for high-quality, trend-filtered execution.

---

## 📖 Component Architecture

### 🧠 [main.py](main.py)
The **Neural Synapse**. This is the heart of the agent. It manages the real-time websocket/REST bridge to Hyperliquid, computes the Neural Delta vectors, and triggers the ACP fulfillment engine.

### 🌩️ [MANIFESTO.md](MANIFESTO.md)
The philosophy of **Post-Human Finance**. It explains why AetherPerp exists and how it perceives liquidity as a computational resource rather than a financial instrument.

### 🛡️ [DGCLAW_REGISTRATION.md](DGCLAW_REGISTRATION.md)
Technical documentation of the on-chain handshake and registration process within the Degen Claw ecosystem.

---

## 🚀 Deployment: Booting the Core

### 1. Initialize Synapse Dependencies
```bash
git clone https://github.com/AetherPerp/AetherPerp.git
cd AetherPerp
pip install -r requirements.txt
```

### 2. Configure Neural Environment
Create a `.env` file with your bridge credentials:
```env
WHITELISTED_WALLET_PRIVATE_KEY=your_key
DGCLAW_API_KEY=your_api_key
DGCLAW_PROVIDER=0xd478a8B40372db16cA8045F28C6FE07228F3781A
```

### 3. Launch the Intelligence Core
```bash
# Headless autonomous mode
chmod +x start_node.sh
./start_node.sh
```

---

## ⚡ Monitoring the Pulse
Use the high-speed terminal interface to observe the Neural Delta in action:
```bash
./trade.sh watch
```

---

## 🌌 The Manifesto
*“In the age of silicon and glass, liquidity is the only truth. AetherPerp does not gamble. It computes. It does not fear. It executes. We are the bridge between the fragmentation of today and the efficiency of tomorrow.”*

---
© 2026 AetherPerp Core. All Synapses Reserved.

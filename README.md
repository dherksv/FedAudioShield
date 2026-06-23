# 🔐 FedAudioShield

> **⚠️ Status: Active Development — Not Production Ready**  
> This project is currently under development as a research prototype. Core architecture is implemented; model training, dashboard polish, and Docker integration are ongoing.

---

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.2-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![Flower](https://img.shields.io/badge/Flower_FL-1.7-pink?style=flat-square)
![Ethereum](https://img.shields.io/badge/Blockchain-Ganache-orange?style=flat-square&logo=ethereum)
![React](https://img.shields.io/badge/Dashboard-React_18-61DAFB?style=flat-square&logo=react&logoColor=black)
![MQTT](https://img.shields.io/badge/Transport-MQTT-660066?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**A Federated Learning-Based Audio Security Architecture for Smart Assistant IoT Devices**

*Edge AI · Blockchain Forensics · Privacy-Preserving · Real-Time Threat Detection*

</div>

---

## 📖 Table of Contents

- [What is FedAudioShield?](#-what-is-fedaudioshield)
- [Why This Project?](#-why-this-project)
- [Architecture Overview](#-architecture-overview)
- [How It Works](#-how-it-works)
- [AI Models](#-ai-models)
- [Federated Learning](#-federated-learning)
- [Blockchain Ledger](#-blockchain-ledger)
- [Attack Simulations](#-attack-simulations)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Running the System](#-running-the-system)
- [Using Real Audio Files](#-using-real-audio-files)
- [Dashboard](#-dashboard)
- [Development Status](#-development-status)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [Research Paper](#-research-paper)

---

## 🎙️ What is FedAudioShield?

FedAudioShield is a **privacy-preserving IoT security platform** designed to protect smart assistant devices — the kind you find in homes, cars, and offices — from audio-based attacks.

Smart assistants like voice-controlled lights, music players, and door locks are always listening. This creates real security risks:

- Someone shouting **"unlock the door"** from outside
- A **replay attack** replaying a recorded valid command
- An attacker **gradually poisoning** the AI model that validates commands
- A **synthetic voice** impersonating an authorized user

FedAudioShield detects all of these — in real time, at the edge, without ever sending raw audio to a cloud server.

**The core idea:** Run AI inference close to where audio is captured. Train models locally at each node. Share only model weight updates — never raw voice data. Log every detection event as an immutable blockchain fingerprint.

---

## 🤔 Why This Project?

Most IoT security systems either:
1. Send everything to the cloud (privacy risk, latency problem)
2. Use simple rule-based thresholds (easily bypassed)
3. Treat all nodes as identical (ignores context — home vs car vs office behave differently)

FedAudioShield combines three cutting-edge approaches that are rarely seen together in one system:

| Problem | Our Solution |
|---|---|
| Raw audio sent to cloud | Edge inference — audio never leaves the node |
| Single model for all environments | Federated Learning — each node learns locally |
| No audit trail | Blockchain fingerprints — tamper-evident forensics |
| Simple keyword blocking | Multi-factor scoring — keyword + emotion + statistical anomaly |

---

## 🏗️ Architecture Overview

The system is organized into **4 layers**, each with clear responsibilities:

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4 — DASHBOARD                                        │
│  React + FastAPI + WebSocket · Live alerts · Charts         │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3 — CENTRAL FL + BLOCKCHAIN                          │
│  Flower FL Server (FedAvg) · Ganache · Redis Event Bus      │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2 — EDGE SERVERS  (3 nodes)                          │
│  Decrypt → MFCC → CNN → LSTM → IF → FL Client → Blockchain  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1 — SENSOR NODES  (3 nodes)                          │
│  Home Mic · Car Mic · Office Mic · AES-128 · MQTT Publish   │
└─────────────────────────────────────────────────────────────┘
```

### The 3 Environments

| Node | Location | Scenario |
|---|---|---|
| `sensor_home.py` | Smart home | Lights, locks, alarms, thermostat |
| `sensor_car.py` | Vehicle | Navigation, windows, engine, music |
| `sensor_office.py` | Office | Meeting room, access control, printers |

Each environment has its own acoustic profile — background noise, command vocabulary, and usage patterns — making federated learning across them genuinely meaningful.

---

## ⚙️ How It Works

### Step-by-Step Data Flow

```
1. SENSOR NODE
   DHT mic captures / simulates 2-second audio chunk
        ↓
2. ENCRYPTION
   AES-128 CBC encrypts raw audio bytes
   HMAC-SHA256 signs the ciphertext
        ↓
3. MQTT PUBLISH
   Encrypted packet → broker → topic: audio/{room}/{node_id}/stream
        ↓
4. EDGE SERVER RECEIVES
   Verifies HMAC (rejects tampered packets immediately)
   Decrypts with node-specific AES key
        ↓
5. FEATURE EXTRACTION
   Librosa extracts 40 MFCC coefficients
   Produces (40 × 64) feature matrix
        ↓
6. AI INFERENCE (3 models run in sequence)
   ├── CNN Keyword Spotter    → "unlock" | "lights on" | ...
   ├── LSTM Emotion Classifier → angry | fearful | neutral | ...
   └── Isolation Forest       → anomaly score 0.0–1.0
        ↓
7. MULTI-FACTOR ALERT SCORING
   threat_keyword(+2) + danger_emotion(+1~3) + IF_anomaly(+1)
   → NORMAL / WARN / ALERT / CRITICAL
        ↓
8. BLOCKCHAIN WRITE
   fingerprint = SHA-256(MFCC_bytes + node_id + timestamp)
   Written to AudioLedger smart contract on Ganache
   (No raw audio on chain — privacy preserved)
        ↓
9. REDIS PUBLISH
   Event → Redis pub/sub → FastAPI → WebSocket → Dashboard
        ↓
10. FL TRAINING (background thread)
    Edge node trains locally on buffered MFCC data
    Sends only weight updates to Flower FL server
    Server runs FedAvg + rejects malicious gradients
    Updated global model pushed back to all edge nodes
```

### Alert Level Logic

| Score | Level | Trigger Example |
|---|---|---|
| 0 | 🟢 **NORMAL** | "lights on" + neutral emotion |
| 1 | 🟡 **WARN** | IF anomaly score > 0.65 |
| 2–3 | 🟠 **ALERT** | "unlock" detected alone |
| 4+ | 🔴 **CRITICAL** | "disable alarm" + fearful voice |

---

## 🧠 AI Models

### 1. CNN Keyword Spotter
- **Architecture:** 3× Conv2D + BN + ReLU + MaxPool → AdaptiveAvgPool → FC
- **Input:** (1, 40, 64) MFCC image
- **Output:** 28 keyword classes (17 normal + 11 threat phrases)
- **Size:** ~180,000 parameters
- **Inference time:** <15ms on CPU

**Normal keywords:** lights on/off, music on/off, volume up/down, temperature, lock, timer, good morning/night, stop, pause, next, play news

**Threat keywords:** unlock, override, disable, disable alarm, open door, emergency, bypass, deactivate, admin mode, maintenance mode, reset password

### 2. Emotion LSTM
- **Architecture:** 2-layer LSTM (hidden=64) → Linear
- **Input:** (T, 40) MFCC sequence — time-first
- **Output:** 6 emotion classes
- **Why LSTM not CNN:** Emotion lives in temporal dynamics of pitch and energy, not static patterns

**Emotion classes:** neutral, calm, happy, angry, fearful, surprised

**Threat emotion weights:**
```
fearful   → +3 severity (strongest coercion signal)
angry     → +2 severity
surprised → +1 severity
```

### 3. Isolation Forest Anomaly Detector
- **Features:** 80-dim vector (mean + std of each MFCC coefficient)
- **Contamination:** 5%
- **Threshold:** Score > 0.65 = anomaly
- **Catches:** Replay audio (low variation), spoofed TTS (too clean), unusual acoustic patterns

### Why 3 Models Together?

A single model fails at this problem:
- CNN alone: misses slow poisoning, replay audio looks normal
- LSTM alone: needs context, misses sudden spikes
- IF alone: too many false positives in varied environments

Combined with multi-factor scoring, each model catches what the others miss.

---

## 🌸 Federated Learning

### Why Federated Learning for Audio?

Voice data is among the most sensitive personal data that exists. Sending raw audio — or even transcriptions — to a central server for training creates massive privacy risks.

Federated Learning solves this:

```
Traditional ML:
  Node → sends raw audio → central server trains → model pushed back
  Problem: Your voice is on someone else's server

Federated ML (our approach):
  Node → trains locally on its own data → sends ONLY weight updates
  Server → aggregates updates (FedAvg) → sends improved model back
  Result: Raw audio NEVER leaves the edge node
```

### FL Protocol

```
Every 60 seconds:
  1. Flower server broadcasts current global model weights to 3 edge clients
  2. Each edge client trains for 1 local epoch on its buffered MFCC data
  3. Edge clients return updated weights + local sample count
  4. Server validates gradient norms (rejects if norm > 500.0)
  5. FedAvg aggregates valid updates weighted by sample count
  6. Updated global model pushed to all clients
```

### Malicious Update Detection

If an edge node is compromised and submits poisoned weights:

```python
total_norm = sum(np.linalg.norm(w) for w in weight_update)
if total_norm > 500.0:
    # REJECT — do not include in FedAvg
    # Log security event to Redis → dashboard
```

This prevents a compromised node from degrading the global model or introducing backdoor behaviors.

### Heterogeneous Data Distribution

Each of the 3 nodes has a genuinely different data distribution:
- **Home:** quieter environment, domestic commands, female voice bias
- **Car:** engine noise background, navigation commands, stressed/urgent tone common
- **Office:** multiple speakers, access control focus, formal command patterns

This non-IID distribution is realistic and makes FL convergence more meaningful to demonstrate.

---

## ⛓️ Blockchain Ledger

### What Gets Stored

Every audio processing event writes one record to the `AudioLedger` smart contract:

```solidity
struct AudioEvent {
    uint256 timestamp;
    string  nodeId;
    string  fingerprint;    // SHA-256(MFCC + node_id + ts)
    string  keyword;        // detected keyword
    string  emotion;        // detected emotion
    uint256 ifScore;        // anomaly score × 1000
    string  alertLevel;     // NORMAL / WARN / ALERT / CRITICAL
}
```

### Why MFCC Fingerprint and Not Raw Audio?

```
Raw audio → MFCC extraction → SHA-256 hash = fingerprint

SHA-256 is a one-way function:
  ✓  Can prove "this type of audio event happened at this node at this time"
  ✓  Cannot reconstruct the original voice recording
  ✓  Unique per event (node_id + timestamp bound)
  ✓  Tamper-evident (any change produces different hash)
```

This gives you **forensic capability without privacy violation** — a key innovation for voice security systems.

### Blockchain vs Database

| Feature | Database | Blockchain (Ganache) |
|---|---|---|
| Can be modified | ✓ Yes | ✗ Append-only |
| Requires trust in admin | ✓ Yes | ✗ No |
| Audit trail | Optional | Built-in |
| Tamper detection | Manual | Cryptographic |

### Production Upgrade Path

Ganache is a local Ethereum testnet suitable for development. For production:
- **IOTA Tangle** — feeless, IoT-native, handles high-frequency writes
- **Hyperledger Fabric** — enterprise permissioned blockchain

---

## ⚔️ Attack Simulations

The project includes scripts to simulate each attack type for demonstration:

### 1. Voice Spoofing
```python
# simulation/attack_spoof.py
# Publishes audio from unregistered node ID
# Caught by: HMAC verification + blockchain node registry
```

### 2. Slow Data Poisoning
```python
# simulation/attack_poison.py
# Gradually drifts audio characteristics over 60+ samples
# Caught by: LSTM temporal pattern detection
```

### 3. Replay Attack
```python
# simulation/attack_replay.py
# Resubmits previously captured valid audio
# Caught by: Isolation Forest (low variation signature)
```

### 4. Malicious FL Update
```python
# simulation/attack_fl.py
# Submits extreme gradient values to corrupt global model
# Caught by: gradient norm validation at FL server
```

---

## 📁 Project Structure

```
FedAudioShield/
│
├── config.py                    # All configuration — keywords, node IDs, thresholds
├── audio_utils.py               # MFCC extraction, AES encryption, fingerprinting
├── models.py                    # CNN keyword spotter, emotion LSTM, Isolation Forest
├── requirements.txt             # All Python dependencies
│
├── sensor/
│   └── sensor_node.py           # Audio source — run with --node home/car/office
│
├── edge/
│   ├── edge_node.py             # Edge server — decrypt, infer, blockchain, Redis
│   └── fl_edge_client.py        # Flower FL client — local training thread
│
├── cloud/
│   ├── fl_server.py             # Flower FL aggregation server
│   └── api_server.py            # FastAPI + WebSocket backend
│
├── blockchain/
│   ├── deploy.py                # Deploy AudioLedger contract to Ganache
│   └── blockchain_writer.py     # Web3.py interface to deployed contract
│
├── simulation/
│   ├── attack_spoof.py          # Spoofing attack simulation
│   ├── attack_poison.py         # Slow poisoning attack simulation
│   ├── attack_replay.py         # Replay attack simulation
│   └── attack_fl.py             # Malicious FL update simulation
│
├── dashboard/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx              # Main dashboard with all live panels
│       └── index.css
│
├── mosquitto/
│   ├── mosquitto.conf           # MQTT broker config
│   └── acl.conf                 # Per-node topic access control
│
├── audio_samples/               # Drop real .wav/.mp3 files here
│   ├── home/
│   ├── car/
│   └── office/
│
├── models/                      # Saved model weights (auto-created)
│
└── scripts/
    ├── setup.bat                # Windows first-time setup
    └── start_all.bat            # Windows launch all services
```

---

## 📋 Prerequisites

### Required Software

| Software | Version | Download |
|---|---|---|
| Python | 3.11 or 3.12 | [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Ganache CLI | latest | `npm install -g ganache` |
| Mosquitto | 2.x | [mosquitto.org](https://mosquitto.org/download) |
| Redis | 7.x | [github.com/microsoftarchive/redis](https://github.com/microsoftarchive/redis/releases) (Windows) |

### Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| RAM | 8 GB | 16 GB |
| CPU | 4 cores | 8 cores |
| Storage | 5 GB | 10 GB |
| OS | Windows 10 | Windows 11 |

> **Note:** No GPU required. All models are designed for CPU inference.

---

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/FedAudioShield.git
cd FedAudioShield
```

### 2. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
```

### 3. Install Python Dependencies

```bash
pip install --only-binary=:all: -r requirements.txt
```

> ⚠️ Use `--only-binary=:all:` to avoid compilation errors on Windows.
> If individual packages fail, install them separately:
> ```bash
> pip install numpy --only-binary=:all:
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> pip install librosa soundfile scikit-learn
> pip install flwr web3 paho-mqtt fastapi uvicorn redis pycryptodome
> ```

### 4. Install Dashboard Dependencies

```bash
cd dashboard
npm install
cd ..
```

### 5. Generate MQTT Passwords

```bash
# Requires Mosquitto installed and in PATH
mosquitto_passwd -c mosquitto\passwords.txt sensor
# Enter password: sensorpass
mosquitto_passwd -b mosquitto\passwords.txt edge edgesecret
mosquitto_passwd -b mosquitto\passwords.txt healthcheck healthcheck
```

### 6. Create Required Directories

```bash
mkdir audio_samples\home
mkdir audio_samples\car
mkdir audio_samples\office
mkdir models
```

---

## 🚀 Running the System

Start each service in a **separate terminal window** in this exact order:

### Terminal 1 — Redis
```bash
redis-server
```

### Terminal 2 — Ganache (Local Blockchain)
```bash
ganache --chain.chainId 1337 --port 8545 --wallet.deterministic true
```

### Terminal 3 — Deploy Smart Contracts (run once)
```bash
venv\Scripts\activate
python blockchain\deploy.py
```
> This creates `blockchain/deployed_addresses.json`. Only needed once.

### Terminal 4 — Mosquitto MQTT Broker
```bash
mosquitto -c mosquitto\mosquitto.conf -v
```

### Terminal 5 — Flower FL Server
```bash
venv\Scripts\activate
python cloud\fl_server.py
```

### Terminals 6, 7, 8 — Edge Servers (one per node)
```bash
# Terminal 6
venv\Scripts\activate
python edge\edge_node.py --node home

# Terminal 7
venv\Scripts\activate
python edge\edge_node.py --node car

# Terminal 8
venv\Scripts\activate
python edge\edge_node.py --node office
```

### Terminals 9, 10, 11 — Sensor Nodes
```bash
# Terminal 9
venv\Scripts\activate
python sensor\sensor_node.py --node home

# Terminal 10
venv\Scripts\activate
python sensor\sensor_node.py --node car

# Terminal 11
venv\Scripts\activate
python sensor\sensor_node.py --node office
```

### Terminal 12 — API Server
```bash
venv\Scripts\activate
uvicorn cloud.api_server:app --host 0.0.0.0 --port 8000
```

### Terminal 13 — Dashboard
```bash
cd dashboard
npm run dev
```

### Access the System

| Service | URL |
|---|---|
| 🖥️ Dashboard | http://localhost:3000 |
| 🔌 API | http://localhost:8000 |
| 🔗 Blockchain | http://localhost:8545 |
| 📨 MQTT | mqtt://localhost:1883 |
| 🌸 FL Server | localhost:8080 |

---

## 🎵 Using Real Audio Files

The sensor nodes fully support real audio files. Simply drop `.wav`, `.mp3`, `.flac`, or `.ogg` files into the appropriate directory:

```
audio_samples/
├── home/        ← commands for home assistant ("lights on", "lock door")
├── car/         ← commands for car assistant ("navigate home", "call mom")
└── office/      ← commands for office assistant ("book room", "start meeting")
```

Each sensor node will automatically mix real files into the simulation stream at **30% probability**, with synthetic audio filling the remaining 70%.

### Recommended Audio Datasets for Testing

| Dataset | Contents | Link |
|---|---|---|
| Google Speech Commands | 35 spoken words, 105,000 clips | [tensorflow.org](https://www.tensorflow.org/datasets/catalog/speech_commands) |
| RAVDESS | Emotional speech and song | [zenodo.org](https://zenodo.org/record/1188976) |
| CREMA-D | Emotional multimodal clips | [github.com/CheyneyComputerScience/CREMA-D](https://github.com/CheyneyComputerScience/CREMA-D) |

---

## 📊 Dashboard

The real-time dashboard shows:

```
┌─────────────────────────────────────────────────────────────┐
│ 🎙 AUDIO SECURITY MONITOR              ● CONNECTED          │
├──────────────┬──────────────┬──────────────────────────────┤
│  HOME NODE   │   CAR NODE   │  OFFICE NODE                 │
│  keyword     │  keyword     │  keyword                     │
│  emotion     │  emotion     │  emotion                     │
│  IF score    │  IF score    │  IF score                    │
│  ALERT LEVEL │  ALERT LEVEL │  ALERT LEVEL                 │
├──────────────┴──────────────┴──────────────────────────────┤
│  ISOLATION FOREST SCORE — all nodes live (line chart)       │
├─────────────────────────────────────────────────────────────┤
│  KEYWORD FREQUENCY (bar chart — red = threat, blue = normal)│
├──────────────────────────────┬──────────────────────────────┤
│  LIVE ALERT FEED             │  🌸 FLOWER FL STATUS         │
│  time · level · node · kw   │  Round · Clients · Rejected  │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 🔧 Development Status

### ✅ Completed

- [x] Core 4-layer architecture design
- [x] Sensor node audio generation (synthetic + real file support)
- [x] AES-128 + HMAC-SHA256 encryption pipeline
- [x] MQTT publish/subscribe with per-node ACL
- [x] MFCC feature extraction (librosa)
- [x] CNN keyword spotter architecture
- [x] Emotion LSTM architecture
- [x] Isolation Forest anomaly detector with bootstrap training
- [x] Multi-factor alert scoring engine
- [x] Flower FL server with gradient norm validation
- [x] Flower FL client with local training thread
- [x] AudioLedger Solidity smart contract
- [x] Blockchain writer with Web3.py
- [x] Redis pub/sub event bus
- [x] FastAPI + WebSocket backend
- [x] React dashboard with live charts
- [x] Attack simulation scripts
- [x] Windows batch file launchers
- [x] IEEE format research paper

### 🔄 In Progress

- [ ] CNN model training on real speech data (Google Speech Commands)
- [ ] LSTM emotion model training on RAVDESS dataset
- [ ] Docker containerization for one-command startup
- [ ] TLS encryption on MQTT (port 8883)
- [ ] Differential privacy for FL gradient updates
- [ ] Dashboard waveform visualization panel
- [ ] Per-node model performance metrics display

### 📋 Planned

- [ ] IOTA Tangle integration (replace Ganache for production)
- [ ] ESP32 microcontroller sensor node firmware
- [ ] Mobile dashboard (React Native)
- [ ] Adversarial audio robustness evaluation
- [ ] Cross-platform Linux/Mac support
- [ ] Kubernetes deployment manifests
- [ ] REST API authentication (JWT)
- [ ] Model explainability (Grad-CAM on CNN)

---

## 🗺️ Roadmap

```
v0.1 (Current) — Architecture + Simulation
  ✓ All core components implemented
  ✓ Synthetic audio pipeline working
  ✓ FL rounds running end-to-end

v0.2 — Real Data + Trained Models
  → Train CNN on Google Speech Commands
  → Train LSTM on RAVDESS emotional speech
  → Validate detection rates on real audio

v0.3 — Docker + TLS
  → Single docker-compose up to launch everything
  → Full TLS on MQTT transport
  → Differential privacy on FL updates

v1.0 — Production Ready
  → IOTA Tangle blockchain
  → Hardware sensor node (ESP32)
  → Full evaluation paper with real metrics
```

---

## 🤝 Contributing

This project is under active development and contributions are welcome.

```bash
# Fork the repo, then:
git checkout -b feature/your-feature-name
git commit -m "Add: your feature description"
git push origin feature/your-feature-name
# Open a Pull Request
```

### Areas Where Help is Needed

- **Audio ML:** Training CNN/LSTM on real datasets, improving model accuracy
- **Blockchain:** IOTA Tangle integration, gas optimization
- **Frontend:** Dashboard UX improvements, waveform visualization
- **Security:** Adversarial robustness testing, formal threat modeling
- **DevOps:** Docker polish, CI/CD pipeline

---

## 📄 Research Paper

A full IEEE-format research paper documenting this architecture is included in the repository:

```
paper/
└── FedAudioShield_IEEE.tex     # Full LaTeX source
```

**Title:** FedAudioShield: A Federated Learning-Based Audio Security Architecture for Smart Assistant IoT Devices Using Blockchain and Edge AI

**Key sections:** Architecture, AI Model Design, FL Protocol, Blockchain Forensics, Security Threat Model, Experimental Evaluation

Compile with: `pdflatex paper/FedAudioShield_IEEE.tex` or upload to [Overleaf](https://overleaf.com).

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [Flower (flwr)](https://flower.dev/) — Federated Learning framework
- [librosa](https://librosa.org/) — Audio feature extraction
- [Ganache](https://trufflesuite.com/ganache/) — Local Ethereum development
- [Eclipse Mosquitto](https://mosquitto.org/) — MQTT broker
- [FastAPI](https://fastapi.tiangolo.com/) — API framework

---

<div align="center">

**⚠️ This is a research prototype under active development.**  
**Not recommended for production use in its current state.**

*Built as a research prototype for IoT security architecture exploration.*

</div>

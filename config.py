# config.py — shared across all processes
import os

# ── MQTT ──────────────────────────────────────────────────────────────────────
MQTT_HOST     = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT     = int(os.getenv("MQTT_PORT", "1883"))   # 8883 for TLS
MQTT_USER     = os.getenv("MQTT_USER", "sensor")
MQTT_PASS     = os.getenv("MQTT_PASS", "sensorpass")

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_URL     = os.getenv("REDIS_URL", "redis://localhost:6379")

# ── Ganache ───────────────────────────────────────────────────────────────────
GANACHE_URL   = os.getenv("GANACHE_URL", "http://localhost:8545")
DEPLOYED_PATH = os.getenv("DEPLOYED_PATH", "blockchain/deployed_addresses.json")

# ── Flower FL ────────────────────────────────────────────────────────────────
FL_SERVER     = os.getenv("FL_SERVER", "localhost:8080")
FL_MIN_CLIENTS = int(os.getenv("FL_MIN_CLIENTS", "3"))
FL_NUM_ROUNDS  = int(os.getenv("FL_NUM_ROUNDS", "50"))

# ── Audio ────────────────────────────────────────────────────────────────────
SAMPLE_RATE   = 16000     # Hz — standard for speech
CHUNK_SECONDS = 2         # seconds per audio chunk sent to edge
N_MFCC        = 40        # MFCC feature count
HOP_LENGTH    = 512
N_FFT         = 2048
AUDIO_DIR     = os.getenv("AUDIO_DIR", "audio_samples")

# ── Sensor nodes ──────────────────────────────────────────────────────────────
SENSOR_NODES = {
    "home":   {
        "node_id":    "NODE_HOME_001",
        "aes_key":    bytes.fromhex("0011223344556677889900aabbccddee"),
        "room":       "home",
        "mqtt_topic": "audio/home/NODE_HOME_001/stream",
        "wallet":     "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    },
    "car":    {
        "node_id":    "NODE_CAR_002",
        "aes_key":    bytes.fromhex("ffeeddccbbaa99887766554433221100"),
        "room":       "car",
        "mqtt_topic": "audio/car/NODE_CAR_002/stream",
        "wallet":     "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
    },
    "office": {
        "node_id":    "NODE_OFFICE_003",
        "aes_key":    bytes.fromhex("aabbccddeeff00112233445566778899"),
        "room":       "office",
        "mqtt_topic": "audio/office/NODE_OFFICE_003/stream",
        "wallet":     "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
    },
}

# ── Keywords ──────────────────────────────────────────────────────────────────
NORMAL_KEYWORDS = [
    "lights on", "lights off", "music on", "music off",
    "volume up", "volume down", "temperature up", "temperature down",
    "open curtains", "close curtains", "set timer", "good morning",
    "good night", "play news", "stop", "pause", "next"
]

THREAT_KEYWORDS = [
    "unlock", "override", "disable", "disable alarm",
    "open door", "emergency", "bypass", "deactivate",
    "admin mode", "maintenance mode", "reset password"
]

ALL_KEYWORDS = NORMAL_KEYWORDS + THREAT_KEYWORDS
KEYWORD_TO_IDX = {kw: i for i, kw in enumerate(ALL_KEYWORDS)}
IDX_TO_KEYWORD = {i: kw for kw, i in KEYWORD_TO_IDX.items()}
N_KEYWORDS     = len(ALL_KEYWORDS)

# ── Emotions ──────────────────────────────────────────────────────────────────
EMOTIONS      = ["neutral", "calm", "happy", "angry", "fearful", "surprised"]
N_EMOTIONS    = len(EMOTIONS)

# ── Anomaly logic ─────────────────────────────────────────────────────────────
# Threat keyword + dangerous emotion → CRITICAL
THREAT_EMOTION_PAIRS = {
    "fearful":   3,    # severity boost
    "angry":     2,
    "surprised": 1,
}
IF_ANOMALY_THRESHOLD = 0.65   # Isolation Forest score above this = anomaly

# ── Alert levels ─────────────────────────────────────────────────────────────
ALERT_LEVELS = ["NORMAL", "WARN", "ALERT", "CRITICAL"]

# edge/edge_node.py
# Run one per sensor node:
#   python edge/edge_node.py --node home
#   python edge/edge_node.py --node car
#   python edge/edge_node.py --node office

import argparse, json, time, os, sys, hashlib, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import redis
import paho.mqtt.client as mqtt

from config import (SENSOR_NODES, MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASS,
                    REDIS_URL, FL_SERVER, THREAT_KEYWORDS, THREAT_EMOTION_PAIRS,
                    IF_ANOMALY_THRESHOLD)
from audio_utils import (decrypt_audio_chunk, extract_mfcc,
                          audio_fingerprint, mfcc_to_fixed_vector)
from models import KeywordSpotter, EmotionClassifier, AudioAnomalyDetector
from blockchain.blockchain_writer import BlockchainWriter


def compute_alert_level(keyword: str, is_threat: bool, emotion: str,
                         if_score: float, if_anomaly: bool) -> str:
    """
    Multi-factor alert logic:
    - Threat keyword + fearful/angry emotion → CRITICAL
    - Threat keyword alone → ALERT
    - IF anomaly alone → WARN
    - Normal → NORMAL
    """
    severity = 0

    if is_threat:
        severity += 2
        if emotion in THREAT_EMOTION_PAIRS:
            severity += THREAT_EMOTION_PAIRS[emotion]

    if if_anomaly:
        severity += 1

    if severity >= 4:
        return "CRITICAL"
    elif severity >= 2:
        return "ALERT"
    elif severity >= 1:
        return "WARN"
    return "NORMAL"


class EdgeNode:
    def __init__(self, node_name: str):
        cfg = SENSOR_NODES[node_name]
        self.node_name = node_name
        self.node_id   = cfg["node_id"]
        self.aes_key   = cfg["aes_key"]
        self.topic     = cfg["mqtt_topic"]

        print(f"[Edge:{self.node_id}] Initializing models...")

        # ── AI Models (each edge owns its own copy) ────────────────────────
        self.keyword_model = KeywordSpotter()
        self.emotion_model = EmotionClassifier()
        self.if_detector   = AudioAnomalyDetector()

        # ── Services ──────────────────────────────────────────────────────
        self.redis = redis.from_url(REDIS_URL)
        self.bc    = BlockchainWriter()

        # ── Local training data buffer for FL ─────────────────────────────
        self.local_mfcc_buffer = []   # stores (mfcc_vector, label) tuples
        self.buffer_lock = threading.Lock()

        # ── Start FL client in background thread ──────────────────────────
        self._start_fl_client()

        # ── MQTT ──────────────────────────────────────────────────────────
        self.mqtt_client = mqtt.Client(client_id=f"edge_{self.node_id}")
        self.mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message

        print(f"[Edge:{self.node_id}] Ready. Subscribing to {self.topic}")

    def _start_fl_client(self):
        """Start Flower FL client in a background daemon thread."""
        import flwr as fl
        from edge.fl_edge_client import AudioFlowerClient

        def _run():
            client = AudioFlowerClient(
                self.node_id,
                self.keyword_model,
                self.emotion_model,
                self.local_mfcc_buffer,
                self.buffer_lock,
            )
            print(f"[Edge:{self.node_id}] Connecting FL client to {FL_SERVER}...")
            fl.client.start_numpy_client(
                server_address=FL_SERVER,
                client=client,
            )

        t = threading.Thread(target=_run, daemon=True, name=f"fl_{self.node_id}")
        t.start()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(self.topic, qos=1)
            print(f"[Edge:{self.node_id}] MQTT connected, subscribed to {self.topic}")

    def _on_message(self, client, userdata, msg):
        try:
            self._process(json.loads(msg.payload.decode()))
        except Exception as e:
            print(f"[Edge:{self.node_id}] ERROR: {e}")

    def _process(self, packet: dict):
        ts = time.time()

        # ── 1. Decrypt + HMAC verify ──────────────────────────────────────
        try:
            audio, metadata = decrypt_audio_chunk(packet, self.aes_key)
        except ValueError as e:
            self._publish_alert("CRITICAL", "TAMPERING", str(e))
            return

        # ── 2. Verify node identity ───────────────────────────────────────
        node_id = metadata.get("node_id", "")
        if node_id != self.node_id:
            self._publish_alert("CRITICAL", "SPOOFING",
                                f"Node ID mismatch: got {node_id}")
            return

        # ── 3. Extract MFCC features ──────────────────────────────────────
        mfcc = extract_mfcc(audio)

        # ── 4. Keyword spotting (CNN) ─────────────────────────────────────
        keyword, kw_conf, is_threat = self.keyword_model.predict(mfcc)

        # ── 5. Emotion classification (LSTM) ──────────────────────────────
        emotion, em_conf = self.emotion_model.predict(mfcc)

        # ── 6. Isolation Forest anomaly score ─────────────────────────────
        if_score, if_anomaly = self.if_detector.predict(mfcc)

        # ── 7. Multi-factor alert level ───────────────────────────────────
        alert_level = compute_alert_level(
            keyword, is_threat, emotion, if_score, if_anomaly)

        # ── 8. Audio fingerprint for blockchain ───────────────────────────
        fingerprint = audio_fingerprint(mfcc, self.node_id, ts)

        # ── 9. Write to blockchain ────────────────────────────────────────
        block = self.bc.write_audio_block({
            "node_id":     self.node_id,
            "fingerprint": fingerprint,
            "keyword":     keyword,
            "emotion":     emotion,
            "if_score":    if_score,
            "alert_level": alert_level,
            "timestamp":   ts,
        })

        # ── 10. Buffer MFCC for local FL training ─────────────────────────
        with self.buffer_lock:
            label = 1 if is_threat else 0
            self.local_mfcc_buffer.append((mfcc, label))
            if len(self.local_mfcc_buffer) > 500:
                self.local_mfcc_buffer.pop(0)   # keep last 500

        # ── 11. Publish event to Redis → dashboard ─────────────────────────
        event = {
            "type":        "audio_event",
            "node_id":     self.node_id,
            "node_name":   self.node_name,
            "keyword":     keyword,
            "kw_conf":     kw_conf,
            "is_threat":   is_threat,
            "emotion":     emotion,
            "em_conf":     em_conf,
            "if_score":    if_score,
            "if_anomaly":  if_anomaly,
            "alert_level": alert_level,
            "fingerprint": fingerprint,
            "block_hash":  block.get("hash", ""),
            "scenario":    metadata.get("scenario", ""),
            "ts":          ts,
        }
        self.redis.publish("audio:events", json.dumps(event))

        flag = "🔴" if alert_level in ("CRITICAL", "ALERT") else "🟡" if alert_level == "WARN" else "🟢"
        print(f"[Edge:{self.node_id}] {flag} kw={keyword}({kw_conf:.2f}) "
              f"em={emotion}({em_conf:.2f}) IF={if_score:.2f} → {alert_level}")

    def _publish_alert(self, level: str, attack: str, detail: str):
        alert = {
            "type":      "alert",
            "node_id":   self.node_id,
            "level":     level,
            "attack":    attack,
            "detail":    detail,
            "ts":        time.time(),
        }
        self.redis.publish("audio:events", json.dumps(alert))
        print(f"[Edge:{self.node_id}] {level}: {attack} — {detail}")

    def run(self):
        self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        self.mqtt_client.loop_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", required=True, choices=["home", "car", "office"])
    args = parser.parse_args()
    EdgeNode(args.node).run()

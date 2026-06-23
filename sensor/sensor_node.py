# sensor/sensor_node.py
# Run one per location:
#   python sensor/sensor_node.py --node home
#   python sensor/sensor_node.py --node car
#   python sensor/sensor_node.py --node office
#
# Drop .wav/.mp3 files into audio_samples/home/, audio_samples/car/,
# audio_samples/office/ to use real audio. Falls back to synthetic.

import argparse, json, time, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import paho.mqtt.client as mqtt
from config import SENSOR_NODES, MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASS, AUDIO_DIR
from audio_utils import (generate_synthetic_audio, load_real_audio,
                          encrypt_audio_chunk)


SCENARIOS = ["normal", "normal", "normal", "normal", "threat",
             "silence", "normal", "normal", "replay"]


class SensorNode:
    def __init__(self, node_name: str):
        cfg = SENSOR_NODES[node_name]
        self.node_name = node_name
        self.node_id   = cfg["node_id"]
        self.aes_key   = cfg["aes_key"]
        self.topic     = cfg["mqtt_topic"]
        self.audio_dir = os.path.join(AUDIO_DIR, node_name)
        self.seq       = 0

        # Collect any real audio files dropped by user
        self.real_files = []
        if os.path.isdir(self.audio_dir):
            self.real_files = [
                os.path.join(self.audio_dir, f)
                for f in os.listdir(self.audio_dir)
                if f.lower().endswith((".wav", ".mp3", ".flac", ".ogg"))
            ]
        if self.real_files:
            print(f"[{self.node_id}] Found {len(self.real_files)} real audio file(s)")
        else:
            print(f"[{self.node_id}] No real audio files — using synthetic generation")
            print(f"             Drop .wav/.mp3 files into {self.audio_dir}/ to use real audio")

        # MQTT
        self.client = mqtt.Client(client_id=self.node_id)
        self.client.username_pw_set(MQTT_USER, MQTT_PASS)
        self.client.on_connect    = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[{self.node_id}] Connected to MQTT broker")
        else:
            print(f"[{self.node_id}] MQTT connect failed rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        print(f"[{self.node_id}] Disconnected, reconnecting...")
        time.sleep(3)

    def _get_audio_chunk(self) -> tuple:
        """Return (audio_array, scenario_label)."""
        # 30% chance to use a real file if available
        if self.real_files and random.random() < 0.30:
            fpath    = random.choice(self.real_files)
            audio    = load_real_audio(fpath, duration=2.0)
            scenario = "real_file"
            print(f"[{self.node_id}] Using real audio: {os.path.basename(fpath)}")
        else:
            scenario = random.choice(SCENARIOS)
            audio    = generate_synthetic_audio(duration=2.0, scenario=scenario)
        return audio, scenario

    def _publish_chunk(self):
        audio, scenario = self._get_audio_chunk()
        ts = time.time()

        metadata = {
            "node_id":   self.node_id,
            "node_name": self.node_name,
            "timestamp": ts,
            "seq_no":    self.seq,
            "scenario":  scenario,
            "n_samples": len(audio),
        }

        # Encrypt audio — only raw bytes are encrypted, metadata is plaintext
        packet = encrypt_audio_chunk(audio, self.aes_key, metadata)

        payload = json.dumps(packet)
        self.client.publish(self.topic, payload, qos=1)
        self.seq += 1
        print(f"[{self.node_id}] Published chunk #{self.seq} | scenario={scenario} | {len(audio)} samples")

    def run(self, interval: float = 2.0):
        """Connect and publish one chunk every `interval` seconds."""
        print(f"[{self.node_id}] Starting — publishing to {self.topic}")
        self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        self.client.loop_start()

        # Wait for connection
        time.sleep(1)

        try:
            while True:
                if self.client.is_connected():
                    try:
                        self._publish_chunk()
                    except Exception as e:
                        print(f"[{self.node_id}] Publish error: {e}")
                else:
                    print(f"[{self.node_id}] Not connected, waiting...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print(f"[{self.node_id}] Stopped.")
        finally:
            self.client.loop_stop()
            self.client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart assistant sensor node")
    parser.add_argument("--node", required=True, choices=["home", "car", "office"],
                        help="Which sensor node to run")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="Seconds between audio chunks (default 2.0)")
    args = parser.parse_args()

    # Create audio dir if missing
    audio_dir = os.path.join(AUDIO_DIR, args.node)
    os.makedirs(audio_dir, exist_ok=True)

    SensorNode(args.node).run(interval=args.interval)

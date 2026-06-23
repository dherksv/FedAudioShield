# cloud/fl_server.py — Central Flower FL aggregation server
import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import flwr as fl
import redis

from config import REDIS_URL, FL_MIN_CLIENTS, FL_NUM_ROUNDS

r = redis.from_url(REDIS_URL)

GRADIENT_NORM_THRESHOLD = 500.0   # reject updates with norm above this


class AudioFedAvgStrategy(fl.server.strategy.FedAvg):
    """
    FedAvg with gradient norm guard.
    Detects and rejects malicious model updates from compromised edge nodes.
    """

    def aggregate_fit(self, server_round, results, failures):
        valid, rejected = [], 0

        for proxy, fit_res in results:
            weights    = fl.common.parameters_to_ndarrays(fit_res.parameters)
            total_norm = sum(float(np.linalg.norm(w)) for w in weights)

            if total_norm > GRADIENT_NORM_THRESHOLD:
                rejected += 1
                print(f"[FL Server] Round {server_round} — "
                      f"REJECTED malicious update (norm={total_norm:.1f}) from {proxy.cid}")
                r.publish("audio:events", json.dumps({
                    "type":    "fl_alert",
                    "round":   server_round,
                    "message": f"Malicious FL update rejected — norm={total_norm:.0f}",
                    "cid":     str(proxy.cid),
                }))
            else:
                valid.append((proxy, fit_res))

        agg = super().aggregate_fit(server_round, valid, failures)

        r.publish("audio:events", json.dumps({
            "type":       "fl_update",
            "round":      server_round,
            "n_valid":    len(valid),
            "n_rejected": rejected,
        }))
        print(f"[FL Server] Round {server_round} — {len(valid)} valid, {rejected} rejected")
        return agg


def main():
    strategy = AudioFedAvgStrategy(
        min_fit_clients=FL_MIN_CLIENTS,
        min_evaluate_clients=FL_MIN_CLIENTS,
        min_available_clients=FL_MIN_CLIENTS,
        fraction_fit=1.0,
    )
    address = os.getenv("FL_SERVER_ADDRESS", "0.0.0.0:8080")
    print(f"[FL Server] Starting on {address}, waiting for {FL_MIN_CLIENTS} clients...")
    fl.server.start_server(
        server_address=address,
        config=fl.server.ServerConfig(num_rounds=FL_NUM_ROUNDS),
        strategy=strategy,
    )


if __name__ == "__main__":
    main()

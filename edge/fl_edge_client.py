# edge/fl_edge_client.py — Flower FL client for each edge node
import numpy as np
import torch
import torch.nn as nn
import threading
import flwr as fl
from models import KeywordSpotter, EmotionClassifier


class AudioFlowerClient(fl.client.NumPyClient):
    """
    Runs inside each edge node as a daemon thread.
    Trains locally on buffered MFCC data.
    Sends only model weight updates to FL server — raw audio NEVER leaves the edge.
    """

    def __init__(self, node_id: str,
                 keyword_model: KeywordSpotter,
                 emotion_model: EmotionClassifier,
                 mfcc_buffer: list,
                 buffer_lock: threading.Lock):
        self.node_id       = node_id
        self.kw_model      = keyword_model
        self.em_model      = emotion_model
        self.mfcc_buffer   = mfcc_buffer
        self.buffer_lock   = buffer_lock

    # ── FL protocol ───────────────────────────────────────────────────────────
    def get_parameters(self, config):
        """Return current keyword model weights to FL server."""
        return self.kw_model.get_weights()

    def fit(self, parameters, config):
        """
        1. Set global model weights received from server.
        2. Train locally on this edge node's buffered MFCC data.
        3. Return updated weights — only gradient updates, not raw data.
        """
        # Set global weights
        self.kw_model.set_weights(parameters)

        # Grab local training data snapshot
        with self.buffer_lock:
            buffer_snapshot = list(self.mfcc_buffer)

        if len(buffer_snapshot) < 10:
            print(f"[FL:{self.node_id}] Not enough local data yet ({len(buffer_snapshot)} samples)")
            return self.kw_model.get_weights(), 0, {}

        X, y = self._prepare_batch(buffer_snapshot)
        if X is None:
            return self.kw_model.get_weights(), 0, {}

        # Local training — 1 epoch
        loss = self._train_one_epoch(self.kw_model.model, X, y)
        n_samples = len(buffer_snapshot)

        print(f"[FL:{self.node_id}] Local training done — {n_samples} samples, loss={loss:.4f}")
        return self.kw_model.get_weights(), n_samples, {"loss": float(loss)}

    def evaluate(self, parameters, config):
        """Evaluate global model on local data."""
        self.kw_model.set_weights(parameters)
        with self.buffer_lock:
            buffer_snapshot = list(self.mfcc_buffer)
        if not buffer_snapshot:
            return 1.0, 0, {"accuracy": 0.0}
        X, y = self._prepare_batch(buffer_snapshot)
        if X is None:
            return 1.0, 0, {"accuracy": 0.0}
        acc = self._eval(self.kw_model.model, X, y)
        return float(1 - acc), len(buffer_snapshot), {"accuracy": float(acc)}

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _prepare_batch(self, buffer):
        """Convert MFCC buffer to tensors for CNN training."""
        from audio_utils import mfcc_to_fixed_vector
        from config import N_KEYWORDS
        import random

        Xs, ys = [], []
        for mfcc, label in buffer:
            mfcc_fixed = mfcc_to_fixed_vector(mfcc, n_frames=64)  # (40, 64)
            Xs.append(mfcc_fixed)
            ys.append(label % N_KEYWORDS)   # clamp to valid class range

        if not Xs:
            return None, None

        X = torch.FloatTensor(np.array(Xs)).unsqueeze(1)  # (N, 1, 40, 64)
        y = torch.LongTensor(ys)
        return X, y

    def _train_one_epoch(self, model, X, y, lr=0.001):
        model.train()
        opt  = torch.optim.Adam(model.parameters(), lr=lr)
        crit = nn.CrossEntropyLoss()
        opt.zero_grad()
        # Mini-batches of 32
        total_loss = 0
        n_batches  = max(1, len(X) // 32)
        idx = torch.randperm(len(X))
        for i in range(n_batches):
            batch_idx = idx[i*32:(i+1)*32]
            xb, yb = X[batch_idx], y[batch_idx]
            loss = crit(model(xb), yb)
            loss.backward()
            opt.step()
            opt.zero_grad()
            total_loss += loss.item()
        model.eval()
        return total_loss / n_batches

    def _eval(self, model, X, y):
        model.eval()
        with torch.no_grad():
            preds = model(X).argmax(dim=1)
        return (preds == y).float().mean().item()

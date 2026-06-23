# models.py — all AI models in one file
import numpy as np
import torch
import torch.nn as nn
import os, joblib
from sklearn.ensemble import IsolationForest
from config import N_MFCC, N_KEYWORDS, N_EMOTIONS, IF_ANOMALY_THRESHOLD


# ── CNN Keyword Spotter ────────────────────────────────────────────────────────
class KeywordCNN(nn.Module):
    """
    Lightweight 2D CNN on MFCC spectrogram.
    Input: (batch, 1, N_MFCC, 64) — 1-channel MFCC image
    Output: (batch, N_KEYWORDS) logits
    """
    def __init__(self, n_mfcc: int = N_MFCC, n_frames: int = 64,
                 n_classes: int = N_KEYWORDS):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=(3, 3), padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d((2, 2)),                          # → (16, 20, 32)

            nn.Conv2d(16, 32, kernel_size=(3, 3), padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d((2, 2)),                          # → (32, 10, 16)

            nn.Conv2d(32, 64, kernel_size=(3, 3), padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),                  # → (64, 4, 4)
        )
        self.fc = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(64 * 4 * 4, 128),
            nn.ReLU(),
            nn.Linear(128, n_classes),
        )

    def forward(self, x):
        # x: (B, 1, N_MFCC, T)
        x = self.conv(x)
        x = x.view(x.size(0), -1)
        return self.fc(x)


# ── Emotion LSTM ───────────────────────────────────────────────────────────────
class EmotionLSTM(nn.Module):
    """
    2-layer LSTM on MFCC sequence.
    Input: (batch, T, N_MFCC) — time-first
    Output: (batch, N_EMOTIONS) logits
    """
    def __init__(self, n_mfcc: int = N_MFCC, hidden: int = 64,
                 n_classes: int = N_EMOTIONS, n_layers: int = 2):
        super().__init__()
        self.lstm = nn.LSTM(n_mfcc, hidden, n_layers,
                            batch_first=True, dropout=0.2)
        self.fc   = nn.Linear(hidden, n_classes)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])   # last timestep


# ── Model wrappers ─────────────────────────────────────────────────────────────
class KeywordSpotter:
    MODEL_PATH = "models/keyword_cnn.pt"

    def __init__(self):
        self.model = KeywordCNN()
        self.device = torch.device("cpu")
        if os.path.exists(self.MODEL_PATH):
            self.model.load_state_dict(torch.load(self.MODEL_PATH, map_location="cpu"))
            print(f"[KeywordSpotter] Loaded from {self.MODEL_PATH}")
        else:
            print("[KeywordSpotter] No saved model — using random init (train first)")
        self.model.eval()

    def predict(self, mfcc: np.ndarray) -> tuple[str, float, bool]:
        """
        mfcc: (N_MFCC, T) array
        Returns: (keyword, confidence, is_threat)
        """
        from config import IDX_TO_KEYWORD, THREAT_KEYWORDS, N_KEYWORDS
        from audio_utils import mfcc_to_fixed_vector
        mfcc_fixed = mfcc_to_fixed_vector(mfcc, n_frames=64)
        tensor = torch.FloatTensor(mfcc_fixed).unsqueeze(0).unsqueeze(0)  # (1,1,40,64)
        with torch.no_grad():
            logits = self.model(tensor)
            probs  = torch.softmax(logits, dim=1)
            idx    = probs.argmax(dim=1).item()
            conf   = probs[0, idx].item()
        keyword   = IDX_TO_KEYWORD.get(idx, "unknown")
        is_threat = keyword in THREAT_KEYWORDS
        return keyword, round(conf, 4), is_threat

    def get_weights(self) -> list:
        return [p.data.numpy().copy() for p in self.model.parameters()]

    def set_weights(self, weights: list):
        for p, w in zip(self.model.parameters(), weights):
            p.data = torch.FloatTensor(w)


class EmotionClassifier:
    MODEL_PATH = "models/emotion_lstm.pt"

    def __init__(self):
        self.model = EmotionLSTM()
        if os.path.exists(self.MODEL_PATH):
            self.model.load_state_dict(torch.load(self.MODEL_PATH, map_location="cpu"))
            print(f"[EmotionClassifier] Loaded from {self.MODEL_PATH}")
        else:
            print("[EmotionClassifier] No saved model — using random init")
        self.model.eval()

    def predict(self, mfcc: np.ndarray) -> tuple[str, float]:
        """
        mfcc: (N_MFCC, T) array
        Returns: (emotion_label, confidence)
        """
        from config import EMOTIONS
        tensor = torch.FloatTensor(mfcc.T).unsqueeze(0)  # (1, T, N_MFCC)
        with torch.no_grad():
            logits = self.model(tensor)
            probs  = torch.softmax(logits, dim=1)
            idx    = probs.argmax(dim=1).item()
            conf   = probs[0, idx].item()
        return EMOTIONS[idx], round(conf, 4)

    def get_weights(self) -> list:
        return [p.data.numpy().copy() for p in self.model.parameters()]

    def set_weights(self, weights: list):
        for p, w in zip(self.model.parameters(), weights):
            p.data = torch.FloatTensor(w)


class AudioAnomalyDetector:
    MODEL_PATH = "models/audio_iforest.pkl"

    def __init__(self, contamination: float = 0.05):
        if os.path.exists(self.MODEL_PATH):
            self.model = joblib.load(self.MODEL_PATH)
            print(f"[AnomalyDetector] Loaded from {self.MODEL_PATH}")
        else:
            print("[AnomalyDetector] No saved model — bootstrapping with synthetic data")
            self.model = IsolationForest(
                contamination=contamination, n_estimators=100, random_state=42)
            self._bootstrap()

    def _bootstrap(self):
        """Train on synthetic normal MFCC statistics."""
        from audio_utils import generate_synthetic_audio, extract_mfcc
        samples = []
        for _ in range(300):
            audio = generate_synthetic_audio(scenario="normal")
            mfcc  = extract_mfcc(audio)
            # Use mean + std of each MFCC coefficient as feature vector
            feat = np.concatenate([mfcc.mean(axis=1), mfcc.std(axis=1)])
            samples.append(feat)
        X = np.array(samples)
        self.model.fit(X)
        os.makedirs("models", exist_ok=True)
        joblib.dump(self.model, self.MODEL_PATH)
        print("[AnomalyDetector] Bootstrap training done")

    def predict(self, mfcc: np.ndarray) -> tuple[float, bool]:
        """Returns (score 0-1, is_anomaly)."""
        feat  = np.concatenate([mfcc.mean(axis=1), mfcc.std(axis=1)]).reshape(1, -1)
        score = -self.model.score_samples(feat)[0]
        score = float(np.clip(score / 2.0, 0, 1))
        return round(score, 4), score > IF_ANOMALY_THRESHOLD

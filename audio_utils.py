# audio_utils.py — shared audio processing utilities
import numpy as np
import librosa
import hashlib
import base64
import json
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from config import SAMPLE_RATE, N_MFCC, HOP_LENGTH, N_FFT, CHUNK_SECONDS


# ── MFCC feature extraction ────────────────────────────────────────────────────
def extract_mfcc(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Extract MFCC features from audio chunk.
    Returns shape: (N_MFCC, time_frames) flattened to 1D vector.
    """
    mfcc = librosa.feature.mfcc(
        y=audio.astype(np.float32),
        sr=sr,
        n_mfcc=N_MFCC,
        hop_length=HOP_LENGTH,
        n_fft=N_FFT,
    )
    # Normalize per coefficient
    mfcc = (mfcc - mfcc.mean(axis=1, keepdims=True)) / (mfcc.std(axis=1, keepdims=True) + 1e-9)
    return mfcc  # shape (N_MFCC, T)


def mfcc_to_fixed_vector(mfcc: np.ndarray, n_frames: int = 64) -> np.ndarray:
    """Resize MFCC time axis to fixed length for CNN input."""
    from scipy.ndimage import zoom
    if mfcc.shape[1] == n_frames:
        return mfcc
    factor = n_frames / mfcc.shape[1]
    return zoom(mfcc, (1, factor))


def audio_fingerprint(mfcc: np.ndarray, node_id: str, timestamp: float) -> str:
    """
    SHA-256 hash of MFCC features + node_id + timestamp.
    Written to blockchain — proves WHAT was detected without storing raw audio.
    Privacy-preserving forensics.
    """
    data = f"{node_id}:{timestamp}:{mfcc.tobytes().hex()}"
    return hashlib.sha256(data.encode()).hexdigest()


# ── Synthetic audio generation ────────────────────────────────────────────────
def generate_synthetic_audio(duration: float = 2.0, sr: int = SAMPLE_RATE,
                               scenario: str = "normal") -> np.ndarray:
    """
    Generate realistic synthetic audio for simulation.
    Returns raw float32 audio array.
    """
    n_samples = int(duration * sr)
    t = np.linspace(0, duration, n_samples)

    if scenario == "normal":
        # Typical smart assistant command: voice-like harmonic + noise
        freq = np.random.choice([180, 200, 220, 240])   # fundamental freq
        audio = 0.3 * np.sin(2 * np.pi * freq * t)
        for harmonic in [2, 3, 4]:
            audio += (0.3 / harmonic) * np.sin(2 * np.pi * freq * harmonic * t)
        audio += 0.05 * np.random.randn(n_samples)      # background noise
        # Add voice envelope (attack + decay)
        envelope = np.ones(n_samples)
        attack  = int(0.05 * sr)
        release = int(0.1 * sr)
        envelope[:attack]  = np.linspace(0, 1, attack)
        envelope[-release:] = np.linspace(1, 0, release)
        audio *= envelope

    elif scenario == "threat":
        # Urgent/stressed voice: higher freq, more energy, sharper attack
        freq = np.random.choice([280, 300, 320])
        audio = 0.5 * np.sin(2 * np.pi * freq * t)
        for harmonic in [2, 3, 5]:
            audio += (0.4 / harmonic) * np.sin(2 * np.pi * freq * harmonic * t)
        audio += 0.08 * np.random.randn(n_samples)
        # Sharp attack, sustained energy
        attack = int(0.02 * sr)
        audio[:attack] *= np.linspace(0, 1, attack)

    elif scenario == "silence":
        # Background noise only — no command
        audio = 0.02 * np.random.randn(n_samples)

    elif scenario == "replay":
        # Replay: same signal repeated — lower variation
        base = generate_synthetic_audio(duration, sr, "normal")
        audio = base + 0.01 * np.random.randn(n_samples)  # tiny variation

    elif scenario == "spoofed":
        # Synthetic TTS-like: perfect sine waves, too clean
        freq = 200
        audio = 0.4 * np.sin(2 * np.pi * freq * t)
        audio += 0.2 * np.sin(2 * np.pi * freq * 2 * t)
        # Almost no noise = suspicious
        audio += 0.001 * np.random.randn(n_samples)

    else:
        audio = np.zeros(n_samples)

    # Normalize
    max_val = np.abs(audio).max()
    if max_val > 0:
        audio = audio / max_val * 0.9
    return audio.astype(np.float32)


def load_real_audio(filepath: str, duration: float = 2.0) -> np.ndarray:
    """Load a real .wav or .mp3 file, resample to SAMPLE_RATE, trim/pad to duration."""
    audio, sr = librosa.load(filepath, sr=SAMPLE_RATE, duration=duration, mono=True)
    target_len = int(duration * SAMPLE_RATE)
    if len(audio) < target_len:
        audio = np.pad(audio, (0, target_len - len(audio)))
    else:
        audio = audio[:target_len]
    return audio.astype(np.float32)


# ── AES-128 encryption ────────────────────────────────────────────────────────
def encrypt_audio_chunk(audio: np.ndarray, aes_key: bytes,
                         metadata: dict) -> dict:
    """
    Encrypt raw audio bytes + metadata dict using AES-128 CBC.
    Returns dict with cipher_b64, iv_b64, hmac, metadata_plain.
    Metadata (node_id, timestamp, scenario) is sent plaintext —
    only raw audio bytes are encrypted.
    """
    import hmac as hmac_lib, hashlib
    iv = np.random.bytes(16)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    audio_bytes = audio.tobytes()
    encrypted = cipher.encrypt(pad(audio_bytes, AES.block_size))
    cipher_b64 = base64.b64encode(encrypted).decode()
    iv_b64     = base64.b64encode(iv).decode()
    # HMAC over cipher + iv for integrity
    mac = hmac_lib.new(aes_key, (cipher_b64 + iv_b64).encode(), hashlib.sha256).hexdigest()
    return {
        "cipher":   cipher_b64,
        "iv":       iv_b64,
        "hmac":     mac,
        "metadata": metadata,   # plaintext: node_id, timestamp, scenario, n_samples
    }


def decrypt_audio_chunk(packet: dict, aes_key: bytes) -> tuple[np.ndarray, dict]:
    """Decrypt and verify audio packet. Returns (audio_array, metadata) or raises."""
    import hmac as hmac_lib, hashlib
    cipher_b64 = packet["cipher"]
    iv_b64     = packet["iv"]
    received   = packet["hmac"]
    # Verify HMAC
    expected = hmac_lib.new(aes_key, (cipher_b64 + iv_b64).encode(), hashlib.sha256).hexdigest()
    if not hmac_lib.compare_digest(expected, received):
        raise ValueError("HMAC verification failed — audio tampered")
    # Decrypt
    iv        = base64.b64decode(iv_b64)
    cipher    = AES.new(aes_key, AES.MODE_CBC, iv)
    raw_bytes = unpad(cipher.decrypt(base64.b64decode(cipher_b64)), AES.block_size)
    audio     = np.frombuffer(raw_bytes, dtype=np.float32).copy()
    return audio, packet["metadata"]

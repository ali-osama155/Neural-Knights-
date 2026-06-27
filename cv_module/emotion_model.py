"""
emotion_model.py
────────────────
Loads the trained MobileNetV2 emotion model and runs inference
on a single face crop.

Preprocessing replicates the training pipeline exactly:
  BGR crop → grayscale → 3-channel → resize 160×160 → preprocess_input [-1,1]
"""

import numpy as np
import cv2
import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

# ── Constants ──────────────────────────────────────────────────────────────────
EMOTION_NAMES = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
TARGET_SIZE   = (160, 160)


def _focal_loss(gamma: float = 2.0, alpha: float = 0.25):
    """Recreate the custom focal loss so the model loads without error."""
    def loss_fn(y_true, y_pred):
        y_pred = tf.clip_by_value(y_pred, 1e-7, 1.0)
        ce     = -y_true * tf.math.log(y_pred)
        weight = alpha * y_true * tf.pow(1.0 - y_pred, gamma)
        return tf.reduce_sum(weight * ce, axis=-1)
    return loss_fn


class EmotionModel:
    """
    Wraps the saved Keras model.

    Usage:
        em = EmotionModel('models/fer_raf_combined_final.keras')
        probs = em.predict(face_bgr_crop)   # → dict {emotion: probability}
    """

    def __init__(self, model_path: str):
        self.model = tf.keras.models.load_model(
            model_path,
            custom_objects={'loss_fn': _focal_loss(gamma=2.0, alpha=0.25)}
        )
        self.emotion_names = EMOTION_NAMES
        print(f'[EmotionModel] Loaded: {model_path}')

    def preprocess(self, face_bgr: np.ndarray) -> np.ndarray:
        """
        Converts a BGR face crop to the exact format the model expects.
        Returns array of shape (1, 160, 160, 3).
        """
        gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, TARGET_SIZE)
        rgb  = np.stack([gray, gray, gray], axis=-1).astype(np.float32)
        rgb  = preprocess_input(rgb)          # [0,255] → [-1, 1]
        return np.expand_dims(rgb, axis=0)    # (1, 160, 160, 3)

    def predict(self, face_bgr: np.ndarray) -> dict:
        """
        Run emotion prediction on a single face crop.

        Args:
            face_bgr: BGR image of a face (any size — will be resized internally)

        Returns:
            dict mapping emotion name → probability (floats sum to ~1.0)
            e.g. {'angry': 0.05, 'happy': 0.72, ...}
        """
        inp   = self.preprocess(face_bgr)
        probs = self.model.predict(inp, verbose=0)[0]   # shape (7,)
        return {name: float(p) for name, p in zip(EMOTION_NAMES, probs)}

    def predict_top(self, face_bgr: np.ndarray) -> tuple[str, float]:
        """
        Convenience method — returns just the top emotion and its probability.

        Returns:
            (emotion_name, probability)  e.g. ('happy', 0.72)
        """
        probs     = self.predict(face_bgr)
        top_name  = max(probs, key=probs.get)
        return top_name, probs[top_name]

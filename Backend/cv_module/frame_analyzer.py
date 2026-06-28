"""
frame_analyzer.py
─────────────────
Combines all three CV signals into a single FrameData object per frame.

Signals:
  1. Emotion probabilities    (EmotionModel)
  2. Gaze direction           (FaceMeshAnalyzer)
  3. Head pose angles         (FaceMeshAnalyzer)

Called every frame during the interview. Lightweight — no heavy logic here,
that happens in question_aggregator.py.
"""

import time
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict

from emotion_model   import EmotionModel,      EMOTION_NAMES
from face_mesh       import FaceMeshAnalyzer,  GazeResult, HeadPoseResult


# ── Per-frame data container ──────────────────────────────────────────────────
@dataclass
class FrameData:
    timestamp:      float                   # seconds since session start
    emotion_probs:  Dict[str, float]        # {'happy': 0.72, ...}
    top_emotion:    str                     # dominant emotion this frame
    top_prob:       float                   # probability of top emotion

    # Eye contact
    gaze_direction: str                     # 'camera'|'left'|'right'|'down'|'up'
    eye_contact:    bool                    # True when looking at camera

    # Head pose
    pitch:          float                   # degrees, + = nodding down
    yaw:            float                   # degrees, + = turning right
    roll:           float                   # degrees
    head_upright:   bool                    # True when facing camera

    # Face detected flags
    emotion_detected:  bool
    facemesh_detected: bool


# ── Frame Analyzer ────────────────────────────────────────────────────────────
class FrameAnalyzer:
    """
    Runs all CV analysis on every frame.

    Usage:
        fa = FrameAnalyzer(emotion_model, face_mesh_analyzer)
        data = fa.analyze(frame_bgr, face_crop_bgr, session_start_time)
    """

    def __init__(self,
                 emotion_model:    EmotionModel,
                 face_mesh:        Optional[FaceMeshAnalyzer] = None,
                 smoothing_window: int = 5):
        """
        Args:
            emotion_model:    loaded EmotionModel instance
            face_mesh:        FaceMeshAnalyzer instance (None = disabled)
            smoothing_window: number of frames to average emotion probs over
        """
        self.emotion_model = emotion_model
        self.face_mesh     = face_mesh

        # Rolling buffer for emotion smoothing
        self._smooth_buf: list = []
        self._smooth_n   = smoothing_window

    def analyze(self,
                full_frame:  np.ndarray,
                face_crop:   Optional[np.ndarray],
                session_t0:  float) -> FrameData:
        """
        Run full analysis on one frame.

        Args:
            full_frame:  complete BGR webcam frame (for face mesh)
            face_crop:   BGR crop of just the face (for emotion model)
                         Pass None if no face was detected this frame.
            session_t0:  time.time() value at session start

        Returns:
            FrameData object with all signals filled in.
        """
        timestamp = time.time() - session_t0

        # ── Emotion ───────────────────────────────────────────────────────────
        if face_crop is not None and face_crop.size > 0:
            raw_probs = self.emotion_model.predict(face_crop)

            # Smooth over last N frames
            self._smooth_buf.append(list(raw_probs.values()))
            if len(self._smooth_buf) > self._smooth_n:
                self._smooth_buf.pop(0)
            avg = np.mean(self._smooth_buf, axis=0)
            emotion_probs = {
                name: float(avg[i]) for i, name in enumerate(EMOTION_NAMES)
            }
            top_emotion = max(emotion_probs, key=emotion_probs.get)
            top_prob    = emotion_probs[top_emotion]
            emotion_ok  = True
        else:
            # No face detected — return neutral placeholder
            emotion_probs = {n: 1/7 for n in EMOTION_NAMES}
            top_emotion   = 'neutral'
            top_prob      = 1/7
            emotion_ok    = False
            self._smooth_buf.clear()

        # ── Gaze + Head pose ──────────────────────────────────────────────────
        if self.face_mesh is not None:
            mesh_result = self.face_mesh.process(full_frame)

            if mesh_result.landmarks_detected:
                gaze      = mesh_result.gaze
                head_pose = mesh_result.head_pose
                mesh_ok   = True
            else:
                gaze = head_pose = None
                mesh_ok = False
        else:
            gaze = head_pose = None
            mesh_ok = False

        # ── Pack result ───────────────────────────────────────────────────────
        return FrameData(
            timestamp         = round(timestamp, 3),
            emotion_probs     = emotion_probs,
            top_emotion       = top_emotion,
            top_prob          = top_prob,
            gaze_direction    = gaze.direction      if gaze      else 'unknown',
            eye_contact       = gaze.eye_contact    if gaze      else False,
            pitch             = head_pose.pitch     if head_pose else 0.0,
            yaw               = head_pose.yaw       if head_pose else 0.0,
            roll              = head_pose.roll      if head_pose else 0.0,
            head_upright      = head_pose.is_upright if head_pose else True,
            emotion_detected  = emotion_ok,
            facemesh_detected = mesh_ok,
        )

    def reset(self):
        """Clear smoothing buffer — call when starting a new question."""
        self._smooth_buf.clear()

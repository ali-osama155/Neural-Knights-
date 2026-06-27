"""
face_mesh.py
────────────
Uses MediaPipe Face Mesh to extract:
  1. Eye contact / gaze direction  (iris landmark positions)
  2. Head pose angles              (landmark-ratio method — no solvePnP)

Why landmark-ratio instead of solvePnP:
  solvePnP requires accurate camera calibration. Without it, pitch values
  can reach 100+ degrees (physically impossible). The landmark-ratio method
  derives yaw/pitch directly from facial geometry ratios — no calibration
  needed, stable results for webcam use.

Install:
    pip install mediapipe
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional

try:
    import mediapipe as mp
    _MP_AVAILABLE = True
except ImportError:
    _MP_AVAILABLE = False
    print('[face_mesh] mediapipe not installed — FaceMesh features disabled.')


# ── Landmark indices ───────────────────────────────────────────────────────────
LEFT_EYE_LEFT    = 33
LEFT_EYE_RIGHT   = 133
RIGHT_EYE_LEFT   = 362
RIGHT_EYE_RIGHT  = 263
LEFT_IRIS        = 468
RIGHT_IRIS       = 473
LEFT_EYE_TOP     = 159
LEFT_EYE_BOT     = 145
RIGHT_EYE_TOP    = 386
RIGHT_EYE_BOT    = 374
NOSE_TIP         = 4
LEFT_CHEEK       = 234
RIGHT_CHEEK      = 454
FOREHEAD         = 10
CHIN             = 152


# ── Data classes ───────────────────────────────────────────────────────────────
@dataclass
class GazeResult:
    direction:       str    # 'camera' | 'left' | 'right' | 'down' | 'up'
    eye_contact:     bool
    left_ratio:      float
    right_ratio:     float
    vertical_offset: float


@dataclass
class HeadPoseResult:
    pitch:      float   # + = nodding down
    yaw:        float   # + = turning right
    roll:       float   # + = tilting right
    is_upright: bool


@dataclass
class FaceMeshResult:
    gaze:               Optional[GazeResult]
    head_pose:          Optional[HeadPoseResult]
    landmarks_detected: bool


# ── Main class ────────────────────────────────────────────────────────────────
class FaceMeshAnalyzer:
    """
    Wraps MediaPipe Face Mesh for gaze and head pose extraction.

    Usage:
        fma = FaceMeshAnalyzer()
        result = fma.process(frame_bgr)
        print(result.gaze.direction)   # 'camera' | 'left' | 'right' | 'down'
        print(result.head_pose.yaw)    # degrees, e.g. -8.3
    """

    def __init__(self):
        if not _MP_AVAILABLE:
            raise RuntimeError('mediapipe not installed. Run: pip install mediapipe')

        mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        print('[FaceMeshAnalyzer] Ready.')

    def process(self, frame_bgr: np.ndarray) -> FaceMeshResult:
        h, w = frame_bgr.shape[:2]
        rgb  = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        res  = self.face_mesh.process(rgb)

        if not res.multi_face_landmarks:
            return FaceMeshResult(gaze=None, head_pose=None,
                                  landmarks_detected=False)

        lm = res.multi_face_landmarks[0].landmark

        def px(idx) -> np.ndarray:
            return np.array([lm[idx].x * w, lm[idx].y * h], dtype=np.float64)

        return FaceMeshResult(
            gaze               = self._compute_gaze(lm, px),
            head_pose          = self._compute_head_pose(lm, px),
            landmarks_detected = True,
        )

    # ── Gaze ──────────────────────────────────────────────────────────────────
    def _compute_gaze(self, lm, px) -> GazeResult:
        left_l  = px(LEFT_EYE_LEFT);   left_r  = px(LEFT_EYE_RIGHT)
        right_l = px(RIGHT_EYE_LEFT);  right_r = px(RIGHT_EYE_RIGHT)
        l_iris  = px(LEFT_IRIS);       r_iris  = px(RIGHT_IRIS)

        def horiz_ratio(iris, cl, cr) -> float:
            w = np.linalg.norm(cr - cl)
            return 0.5 if w < 1e-6 else float(np.linalg.norm(iris - cl) / w)

        left_ratio  = horiz_ratio(l_iris, left_l,  left_r)
        right_ratio = horiz_ratio(r_iris, right_l, right_r)
        avg_h       = (left_ratio + right_ratio) / 2.0

        # Vertical — normalised by eye height
        l_top = px(LEFT_EYE_TOP);  l_bot = px(LEFT_EYE_BOT)
        r_top = px(RIGHT_EYE_TOP); r_bot = px(RIGHT_EYE_BOT)
        l_cy  = (l_top[1] + l_bot[1]) / 2;  l_h = abs(l_bot[1]-l_top[1]) + 1e-6
        r_cy  = (r_top[1] + r_bot[1]) / 2;  r_h = abs(r_bot[1]-r_top[1]) + 1e-6
        vert  = float(((l_iris[1]-l_cy)/l_h + (r_iris[1]-r_cy)/r_h) / 2.0)

        # ── Head yaw for combined check ──────────────────────────────────
        # If head is turned > 12° the person isn't looking at camera
        # even if iris appears centred (common when looking at nearby screen)
        nose     = px(NOSE_TIP)
        l_cheek  = px(LEFT_CHEEK)
        r_cheek  = px(RIGHT_CHEEK)
        left_w   = max(nose[0] - l_cheek[0], 1e-6)
        right_w  = max(r_cheek[0] - nose[0], 1e-6)
        yaw_ratio= left_w / (left_w + right_w)
        head_yaw = float((yaw_ratio - 0.5) * 90.0)   # degrees, + = right

        # ── Classify ──────────────────────────────────────────────────────────
        if vert > 0.12:
            direction = 'down'
        elif vert < -0.12:
            direction = 'up'
        elif avg_h < 0.43:
            direction = 'left'
        elif avg_h > 0.57:
            direction = 'right'
        elif abs(head_yaw) > 12:
            # Head turned but iris appears centred — looking at nearby screen
            direction = 'left' if head_yaw < 0 else 'right'
        else:
            direction = 'camera'

        return GazeResult(
            direction       = direction,
            eye_contact     = (direction == 'camera'),
            left_ratio      = round(left_ratio,  3),
            right_ratio     = round(right_ratio, 3),
            vertical_offset = round(vert, 3),
        )

    # ── Head pose (landmark-ratio — no solvePnP, no calibration needed) ───────
    def _compute_head_pose(self, lm, px) -> HeadPoseResult:
        """
        Derives yaw/pitch/roll from facial geometry ratios.
        Values are clamped to [-45, +45] — physically impossible values
        like 112° cannot occur.

        Yaw:   nose splits face width asymmetrically when turned
        Pitch: nose splits face height asymmetrically when tilted
        Roll:  angle of the line between the two eye outer corners
        """
        nose     = px(NOSE_TIP)
        l_cheek  = px(LEFT_CHEEK);  r_cheek  = px(RIGHT_CHEEK)
        forehead = px(FOREHEAD);    chin     = px(CHIN)
        l_eye    = px(LEFT_EYE_LEFT); r_eye  = px(RIGHT_EYE_RIGHT)

        # Yaw: left_w / total_w — 0.5 means straight-on
        left_w  = max(nose[0] - l_cheek[0], 1e-6)
        right_w = max(r_cheek[0] - nose[0], 1e-6)
        yaw_ratio = left_w / (left_w + right_w)
        yaw = float(np.clip((yaw_ratio - 0.5) * 90.0, -45, 45))

        # Pitch: upper_h / total_h — > 0.5 means looking down
        upper_h = max(nose[1] - forehead[1], 1e-6)
        lower_h = max(chin[1] - nose[1],     1e-6)
        pitch_ratio = upper_h / (upper_h + lower_h)
        pitch = float(np.clip((pitch_ratio - 0.5) * 60.0, -30, 30))

        # Roll: angle of eye-to-eye line
        dx   = r_eye[0] - l_eye[0]
        dy   = r_eye[1] - l_eye[1]
        roll = float(np.clip(np.degrees(np.arctan2(dy, dx)), -30, 30))

        is_upright = (abs(yaw) < 20 and abs(pitch) < 15 and abs(roll) < 15)

        return HeadPoseResult(
            pitch      = round(pitch, 1),
            yaw        = round(yaw,   1),
            roll       = round(roll,  1),
            is_upright = is_upright,
        )

    def close(self):
        self.face_mesh.close()

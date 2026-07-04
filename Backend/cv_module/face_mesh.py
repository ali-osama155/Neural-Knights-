"""
face_mesh.py
────────────
Eye contact and head pose estimation using OpenCV only.
Replaces the mediapipe-based implementation to avoid protobuf conflicts.

Uses:
  - Haar cascade for face detection
  - Eye region geometry for gaze estimation
  - Face aspect ratio for head pose approximation
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional


# ── Data classes (same interface as before) ───────────────────────────────────
@dataclass
class GazeResult:
    direction:       str    # 'camera' | 'left' | 'right' | 'down' | 'up'
    eye_contact:     bool
    left_ratio:      float
    right_ratio:     float
    vertical_offset: float


@dataclass
class HeadPoseResult:
    pitch:      float
    yaw:        float
    roll:       float
    is_upright: bool


@dataclass
class FaceMeshResult:
    gaze:               Optional[GazeResult]
    head_pose:          Optional[HeadPoseResult]
    landmarks_detected: bool


# ── Main class ────────────────────────────────────────────────────────────────
class FaceMeshAnalyzer:
    """
    OpenCV-based gaze and head pose estimator.
    Same interface as the mediapipe version — drop-in replacement.
    """

    def __init__(self):
        import os
        _models_dir = os.path.join(os.path.dirname(__file__), 'models')
        # Face detector
        self.face_cascade = cv2.CascadeClassifier(
            os.path.join(_models_dir, 'haarcascade_frontalface_default.xml')
        )
        # Eye detectors
        self.eye_cascade = cv2.CascadeClassifier(
            os.path.join(_models_dir, 'haarcascade_eye.xml')
        )
        print('[FaceMeshAnalyzer] Ready (OpenCV mode).')

    def process(self, frame_bgr: np.ndarray) -> FaceMeshResult:
        h, w = frame_bgr.shape[:2]
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        # ── Detect face ───────────────────────────────────────────────────────
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )

        if len(faces) == 0:
            return FaceMeshResult(gaze=None, head_pose=None, landmarks_detected=False)

        # Use largest face
        fx, fy, fw, fh = max(faces, key=lambda r: r[2] * r[3])
        face_gray = gray[fy:fy+fh, fx:fx+fw]
        face_bgr  = frame_bgr[fy:fy+fh, fx:fx+fw]

        # ── Head pose from face aspect ratio ──────────────────────────────────
        head_pose = self._estimate_head_pose(fx, fy, fw, fh, w, h)

        # ── Detect eyes within face region ────────────────────────────────────
        eyes = self.eye_cascade.detectMultiScale(
            face_gray, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20)
        )

        if len(eyes) < 2:
            # Can't compute gaze without 2 eyes — use head pose only
            gaze = self._gaze_from_head_pose(head_pose)
            return FaceMeshResult(
                gaze=gaze,
                head_pose=head_pose,
                landmarks_detected=True,
            )

        # Sort eyes left to right
        eyes = sorted(eyes, key=lambda e: e[0])[:2]
        left_eye  = eyes[0]
        right_eye = eyes[1]

        gaze = self._compute_gaze(face_gray, left_eye, right_eye, fw, fh, head_pose)

        return FaceMeshResult(
            gaze=gaze,
            head_pose=head_pose,
            landmarks_detected=True,
        )

    # ── Gaze from pupil position ──────────────────────────────────────────────
    def _compute_gaze(self, face_gray, left_eye, right_eye, fw, fh, head_pose) -> GazeResult:
        def pupil_ratio(eye_region, ex, ew):
            """Returns horizontal pupil position ratio (0=left, 1=right)."""
            roi = face_gray[eye_region[1]:eye_region[1]+eye_region[3],
                            eye_region[0]:eye_region[0]+eye_region[2]]
            if roi.size == 0:
                return 0.5
            # Threshold to find dark pupil
            _, thresh = cv2.threshold(roi, 50, 255, cv2.THRESH_BINARY_INV)
            moments = cv2.moments(thresh)
            if moments['m00'] == 0:
                return 0.5
            cx = moments['m10'] / moments['m00']
            return float(cx / roi.shape[1])

        lx, ly, lw, lh = left_eye
        rx, ry, rw, rh = right_eye

        left_ratio  = pupil_ratio(left_eye,  lx, lw)
        right_ratio = pupil_ratio(right_eye, rx, rw)
        avg_h = (left_ratio + right_ratio) / 2.0

        # Vertical: eye center Y position relative to face height
        eye_center_y = ((ly + lh/2) + (ry + rh/2)) / 2.0
        vert = (eye_center_y / fh) - 0.35   # 0.35 is typical eye position

        # If head is significantly turned, override gaze
        if head_pose and abs(head_pose.yaw) > 15:
            direction = 'left' if head_pose.yaw < 0 else 'right'
        elif vert > 0.15:
            direction = 'down'
        elif vert < -0.15:
            direction = 'up'
        elif avg_h < 0.40:
            direction = 'left'
        elif avg_h > 0.60:
            direction = 'right'
        else:
            direction = 'camera'

        return GazeResult(
            direction       = direction,
            eye_contact     = (direction == 'camera'),
            left_ratio      = round(left_ratio,  3),
            right_ratio     = round(right_ratio, 3),
            vertical_offset = round(vert, 3),
        )

    def _gaze_from_head_pose(self, head_pose) -> GazeResult:
        """Fallback when only 1 eye detected — use head pose."""
        if head_pose is None:
            direction = 'unknown'
        elif abs(head_pose.yaw) > 15:
            direction = 'left' if head_pose.yaw < 0 else 'right'
        elif head_pose.pitch > 15:
            direction = 'down'
        elif head_pose.pitch < -15:
            direction = 'up'
        else:
            direction = 'camera'

        return GazeResult(
            direction       = direction,
            eye_contact     = (direction == 'camera'),
            left_ratio      = 0.5,
            right_ratio     = 0.5,
            vertical_offset = 0.0,
        )

    # ── Head pose from face bounding box geometry ─────────────────────────────
    def _estimate_head_pose(self, fx, fy, fw, fh, frame_w, frame_h) -> HeadPoseResult:
        """
        Approximate yaw/pitch/roll from face bounding box position.
        Not as accurate as landmark-based, but works without mediapipe.
        """
        face_cx = fx + fw / 2.0
        face_cy = fy + fh / 2.0

        # Yaw: how far face center is from frame center horizontally
        yaw = float(np.clip((face_cx / frame_w - 0.5) * 60.0, -45, 45))

        # Pitch: how far face is from vertical center
        pitch = float(np.clip((face_cy / frame_h - 0.4) * 60.0, -30, 30))

        # Roll: approximate from face aspect ratio (very rough)
        roll = 0.0

        is_upright = (abs(yaw) < 20 and abs(pitch) < 15)

        return HeadPoseResult(
            pitch      = round(pitch, 1),
            yaw        = round(yaw,   1),
            roll       = round(roll,  1),
            is_upright = is_upright,
        )

    def close(self):
        pass  # Nothing to close for OpenCV

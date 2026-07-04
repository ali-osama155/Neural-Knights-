"""
cv_pipeline.py
──────────────
Main entry point for the CV Module.
This is the ONLY file the Interview Controller needs to import.

Full pipeline per frame:
  Webcam → Face Detection → Emotion Model + Face Mesh → FrameData
  → SessionRecorder → QuestionReport JSON

Usage (Interview Controller side):
───────────────────────────────────
    from cv_module.cv_pipeline import CVPipeline

    cv = CVPipeline(model_path='cv_module/models/fer_raf_combined_final.keras')
    cv.start_session()

    for question in questions:
        cv.start_question(question.id, question.text)

        while candidate_is_answering:
            frame = get_webcam_frame()
            annotated_frame = cv.process_frame(frame)
            display(annotated_frame)

        report = cv.end_question()   # → dict (JSON-ready)
        send_to_feedback_module(report)

    summary = cv.end_session()       # → dict with all questions
    cv.release()
"""

import cv2
import numpy as np
import time
import os
import sys
from typing import Optional

# ── Make imports work regardless of where the script is run from ──────────────
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
if _MODULE_DIR not in sys.path:
    sys.path.insert(0, _MODULE_DIR)

from emotion_model    import EmotionModel,      EMOTION_NAMES
from face_mesh        import FaceMeshAnalyzer
from frame_analyzer   import FrameAnalyzer
from session_recorder import SessionRecorder

# ── Default model path — always relative to THIS file, not cwd ───────────────
_DEFAULT_MODEL = os.path.join(_MODULE_DIR, 'models', 'fer_raf_combined_final.keras')


# ── Emotion → display colour (BGR) ────────────────────────────────────────────
EMOTION_COLORS = {
    'angry'   : (0,   0,   220),
    'disgust' : (0,   140, 0  ),
    'fear'    : (130, 0,   130),
    'happy'   : (0,   210, 210),
    'neutral' : (180, 180, 180),
    'sad'     : (210, 100, 0  ),
    'surprise': (0,   165, 255),
}


class CVPipeline:
    """
    Orchestrates the full Computer Vision module for the interview system.

    Parameters
    ----------
    model_path : str
        Path to fer_raf_combined_final.keras
    enable_face_mesh : bool
        Set False to disable eye contact + head pose (faster, no mediapipe needed)
    camera_index : int
        Webcam index (0 = default)
    smoothing_window : int
        Number of frames to average emotion predictions over
    """

    def __init__(self,
                 model_path:        str  = None,
                 enable_face_mesh:  bool = True,
                 camera_index:      Optional[int] = 0,
                 smoothing_window:  int  = 5):
        """
        Parameters
        ----------
        camera_index : int or None
            Webcam index to open locally (0 = default). Pass None to skip
            opening a camera entirely — use this on a backend server where
            the browser owns the camera and frames arrive via
            analyze_frame() instead. read_frame()/process_frame() will not
            work when camera_index is None.
        """

        # Default model path resolves to cv_module/models/ regardless of cwd
        if model_path is None:
            model_path = _DEFAULT_MODEL

        # ── Emotion model ─────────────────────────────────────────────────────
        self.emotion_model = EmotionModel(model_path)

        # ── Face Mesh (optional) ──────────────────────────────────────────────
        self.face_mesh = None
        if enable_face_mesh:
            try:
                self.face_mesh = FaceMeshAnalyzer()
            except Exception as e:
                print(f'[CVPipeline] FaceMesh disabled: {e}')

        # ── Face detector (Haar Cascade — no extra install) ───────────────────
        import os
        _cascade_path = os.path.join(os.path.dirname(__file__), 'models', 'haarcascade_frontalface_default.xml')
        self.face_cascade = cv2.CascadeClassifier(_cascade_path)

        # ── Sub-components ────────────────────────────────────────────────────
        self.frame_analyzer   = FrameAnalyzer(
            self.emotion_model, self.face_mesh, smoothing_window
        )
        self.session_recorder = SessionRecorder(timeline_resolution_seconds=0.5)

        # ── Camera (optional — skip entirely for server-side / browser-camera use) ─
        self.cap          = None
        self._session_t0  = 0.0
        self._recording   = False

        if camera_index is not None:
            self.cap = cv2.VideoCapture(camera_index)
            if not self.cap.isOpened():
                raise RuntimeError(
                    f'Cannot open camera index {camera_index}. '
                    'Try a different index, or pass camera_index=None '
                    'if frames will arrive via analyze_frame() instead.'
                )
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            print('[CVPipeline] Ready (local camera open).')
        else:
            print('[CVPipeline] Ready (no local camera — use analyze_frame()).')

    # ── Session control ───────────────────────────────────────────────────────
    def start_session(self):
        """Call once at the beginning of the interview."""
        self._session_t0 = time.time()
        self.session_recorder.start_session()

    def start_question(self, question_id: int, question_text: str = ''):
        """Call when the candidate starts answering a question."""
        self.frame_analyzer.reset()
        self.session_recorder.start_question(question_id, question_text)
        self._recording = True

    def end_question(self) -> dict:
        """
        Call when the candidate finishes answering.
        Returns the QuestionReport as a dict.
        """
        self._recording = False
        return self.session_recorder.end_question()

    def end_session(self) -> dict:
        """
        Call at the end of the interview.
        Returns the full session summary dict.
        """
        return self.session_recorder.get_session_summary()

    # ── Per-frame processing ──────────────────────────────────────────────────
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Run full CV analysis on one frame.

        Args:
            frame: BGR frame from cv2.VideoCapture

        Returns:
            Annotated copy of the frame (bounding box + emotion label
            + prob bars + gaze indicator + head pose).
            Pass this to cv2.imshow() or your frontend.
        """
        display = frame.copy()
        h, w    = frame.shape[:2]

        # ── Detect faces ──────────────────────────────────────────────────────
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
        )

        face_crop = None
        box       = None

        if len(faces) > 0:
            # Use the largest detected face
            fx, fy, fw, fh = max(faces, key=lambda r: r[2] * r[3])
            pad  = int(min(fw, fh) * 0.08)
            x1   = max(0, fx - pad)
            y1   = max(0, fy - pad)
            x2   = min(w, fx + fw + pad)
            y2   = min(h, fy + fh + pad)
            face_crop = frame[y1:y2, x1:x2]
            box       = (x1, y1, x2, y2, fw)

        # ── Run all analyzers ─────────────────────────────────────────────────
        frame_data = self.frame_analyzer.analyze(
            full_frame  = frame,
            face_crop   = face_crop,
            session_t0  = self._session_t0,
        )

        # ── Record if active ──────────────────────────────────────────────────
        if self._recording:
            self.session_recorder.record_frame(frame_data)

        # ── Draw annotations ──────────────────────────────────────────────────
        if box is not None and face_crop is not None:
            x1, y1, x2, y2, fw = box
            color = EMOTION_COLORS.get(frame_data.top_emotion, (200, 200, 200))

            # Bounding box
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)

            # Emotion label
            label = (f'{frame_data.top_emotion.upper()}  '
                     f'{frame_data.top_prob*100:.0f}%')
            lbl_y = y1 - 10 if y1 > 30 else y2 + 22
            cv2.putText(display, label, (x1, lbl_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.72, color, 2, cv2.LINE_AA)

            # Probability bars
            self._draw_prob_bars(display, frame_data.emotion_probs, x1, y1, fw)

            # Gaze indicator
            if frame_data.facemesh_detected:
                gaze_col = (0, 220, 0) if frame_data.eye_contact else (0, 100, 220)
                gaze_lbl = f'Gaze: {frame_data.gaze_direction}'
                cv2.putText(display, gaze_lbl, (x1, y2 + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, gaze_col, 1, cv2.LINE_AA)

                # Head pose
                pose_lbl = (f'Y:{frame_data.yaw:+.0f}  '
                            f'P:{frame_data.pitch:+.0f}  '
                            f'R:{frame_data.roll:+.0f}')
                cv2.putText(display, pose_lbl, (x1, y2 + 36),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180),
                            1, cv2.LINE_AA)

        # ── Recording indicator ───────────────────────────────────────────────
        if self._recording:
            cv2.circle(display, (w - 20, 20), 8, (0, 0, 220), -1)
            cv2.putText(display, 'REC', (w - 50, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 220), 1)

        cv2.putText(display, 'Q = quit', (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1)

        return display

    # ── Browser-driven analysis (no cv2.VideoCapture involved) ─────────────────
    def analyze_frame(self, image_bytes: bytes) -> dict:
        """
        Analyzes ONE frame posted from a browser via getUserMedia + canvas
        capture. Use this instead of process_frame() when the frontend owns
        the camera and the backend never displays or streams video — only
        receives still frames for analysis.

        This is the recommended approach for a web-based interview UI:
        the browser shows the live camera natively (zero latency, full
        quality) while the backend silently analyzes a frame every
        ~300-500ms and returns lightweight JSON.

        Args:
            image_bytes: raw encoded image bytes (e.g. JPEG/PNG) — typically
                         the result of decoding a base64 data URL the
                         frontend posted from <canvas>.toDataURL().

        Returns:
            dict, JSON-serialisable:
                {
                  'face_detected'  : bool,
                  'top_emotion'    : str,
                  'top_confidence' : float,
                  'eye_contact'    : bool,
                  'gaze_direction' : str,
                }
            If recording is active (start_question() was called), this
            frame is also recorded into the current question's buffer —
            exactly like process_frame() does, just without drawing or
            requiring a live VideoCapture.
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return {'error': 'invalid image data'}

        h, w = frame.shape[:2]

        # ── Detect faces ──────────────────────────────────────────────────────
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
        )

        face_crop = None
        if len(faces) > 0:
            fx, fy, fw, fh = max(faces, key=lambda r: r[2] * r[3])
            pad = int(min(fw, fh) * 0.08)
            x1  = max(0, fx - pad)
            y1  = max(0, fy - pad)
            x2  = min(w, fx + fw + pad)
            y2  = min(h, fy + fh + pad)
            face_crop = frame[y1:y2, x1:x2]
            if face_crop.size == 0:
                face_crop = None

        # ── Run all analyzers (same as process_frame, no drawing) ──────────────
        frame_data = self.frame_analyzer.analyze(
            full_frame  = frame,
            face_crop   = face_crop,
            session_t0  = self._session_t0,
        )

        # ── Record if a question is actively being recorded ─────────────────────
        if self._recording:
            self.session_recorder.record_frame(frame_data)

        return {
            'face_detected'  : face_crop is not None,
            'top_emotion'    : frame_data.top_emotion,
            'top_confidence' : round(float(frame_data.top_prob), 3),
            'eye_contact'    : frame_data.eye_contact,
            'gaze_direction' : frame_data.gaze_direction,
        }

    def read_frame(self) -> Optional[np.ndarray]:
        """
        Read one raw frame from the local webcam.
        Returns None on failure, or if no local camera was opened
        (camera_index=None was passed to __init__).
        """
        if self.cap is None:
            return None
        ret, frame = self.cap.read()
        return frame if ret else None

    def release(self):
        """Release webcam (if any) and close Face Mesh."""
        if self.cap is not None:
            self.cap.release()
            cv2.destroyAllWindows()
        if self.face_mesh:
            self.face_mesh.close()
        print('[CVPipeline] Released.')

    # ── Drawing helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _draw_prob_bars(frame, probs: dict,
                        x, y, box_w,
                        bar_w=110, bar_h=9, gap=3):
        bx = x + box_w + 8
        if bx + bar_w + 70 > frame.shape[1]:
            bx = max(0, x - bar_w - 75)
        for i, emotion in enumerate(EMOTION_NAMES):
            prob = probs.get(emotion, 0.0)
            by   = y + i * (bar_h + gap)
            fill = int(prob * bar_w)
            col  = EMOTION_COLORS[emotion]
            cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), (50,50,50), -1)
            cv2.rectangle(frame, (bx, by), (bx + fill,  by + bar_h), col,        -1)
            cv2.putText(frame,
                        f'{emotion[:3]} {prob*100:4.1f}%',
                        (bx + bar_w + 4, by + bar_h - 1),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.30, (210,210,210), 1, cv2.LINE_AA)


# ── Standalone demo (run this file directly to test) ─────────────────────────
if __name__ == '__main__':
    import json
    import importlib.util
    import os as _os

    # Load feedback_generator relative to this file — works from any directory
    _fg_path = _os.path.join(_MODULE_DIR, 'feedback_generator.py')
    _spec    = importlib.util.spec_from_file_location('feedback_generator', _fg_path)
    _fg_mod  = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_fg_mod)
    generate_session_feedback = _fg_mod.generate_session_feedback

    cv = CVPipeline(enable_face_mesh=True)
    cv.start_session()
    cv.start_question(question_id=1, question_text='Tell me about yourself.')

    print('Camera running — press Q to end the demo question.')

    while True:
        frame = cv.read_frame()
        if frame is None:
            break
        annotated = cv.process_frame(frame)
        cv2.imshow('CV Module Demo', annotated)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    report   = cv.end_question()
    summary  = cv.end_session()
    feedback = generate_session_feedback(summary)

    print('\n── Question Report ──')
    print(json.dumps(report, indent=2))

    print('\n── Session Summary ──')
    print(json.dumps(
        {k: v for k, v in summary.items() if k != 'per_question_reports'},
        indent=2
    ))

    print('\n── CV Feedback ──')
    print('Overall Score  :', feedback['overall_cv_score'], '/ 100')
    print('Eye Contact    :', feedback['eye_contact_rating'])
    print('Composure      :', feedback['composure_rating'])
    print('Confidence     :', feedback['confidence_rating'])
    print('\nStrengths:')
    for s in feedback['strengths']:    print(' +', s)
    print('\nTo Improve:')
    for i in feedback['improvements']: print(' >', i)
    print('\n' + feedback['overall_summary'])

    cv.release()

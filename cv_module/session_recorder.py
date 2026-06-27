"""
session_recorder.py
───────────────────
Records FrameData objects during each interview question
and produces a structured QuestionReport when the answer ends.

The rest of the team (Interview Controller, Feedback Module)
only needs to call:

    recorder.start_question(question_id, question_text)
    # ... candidate answers ...
    report = recorder.end_question()    # → QuestionReport dict

No CV knowledge needed on their side.
"""

import time
import numpy as np
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from frame_analyzer import FrameData, EMOTION_NAMES


# ── Report structure ──────────────────────────────────────────────────────────
@dataclass
class QuestionReport:
    """
    Full behavioral analysis for one interview question.
    Serializable to dict/JSON for the Feedback Module.
    """
    question_id:      int
    question_text:    str
    duration_seconds: float
    frame_count:      int

    # Emotion
    dominant_emotion:    str
    emotion_breakdown:   List[dict]       # [{emotion, pct}, ...] top 3, ranked by avg strength
    emotion_timeline:    List[dict]     # [{second, emotion, confidence}, ...]
    emotion_switch_rate: float          # 0-1, higher = more unstable

    # Eye contact
    eye_contact_pct:  float             # 0-100
    gaze_breakdown:   Dict[str, float]  # {'camera': 74.0, 'down': 16.0, ...}

    # Head pose
    avg_yaw:          float
    avg_pitch:        float
    yaw_stability:    float             # 0-100, higher = steadier
    pitch_stability:  float

    # Peak stress moment
    peak_stress_second: float
    peak_stress_value:  float
    peak_stress_emotion: str

    # Auto-generated insight strings for Feedback Module
    behavioral_flags: List[str]

    def to_dict(self) -> dict:
        return {
            'question_id'        : self.question_id,
            'question_text'      : self.question_text,
            'duration_seconds'   : round(self.duration_seconds, 1),
            'frame_count'        : self.frame_count,
            'dominant_emotion'   : self.dominant_emotion,
            'emotion_breakdown'  : self.emotion_breakdown,
            'emotion_timeline'   : self.emotion_timeline,
            'emotion_switch_rate': round(self.emotion_switch_rate, 3),
            'eye_contact_pct'    : round(self.eye_contact_pct, 1),
            'gaze_breakdown'     : {k: round(v, 1) for k, v in self.gaze_breakdown.items()},
            'head_pose'          : {
                'avg_yaw'        : round(self.avg_yaw,        2),
                'avg_pitch'      : round(self.avg_pitch,      2),
                'yaw_stability'  : round(self.yaw_stability,  1),
                'pitch_stability': round(self.pitch_stability,1),
            },
            'peak_stress'        : {
                'timestamp_second': round(self.peak_stress_second, 1),
                'stress_value'    : round(self.peak_stress_value, 3),
                'emotion_at_peak' : self.peak_stress_emotion,
            },
            'behavioral_flags'   : self.behavioral_flags,
        }


# ── Session Recorder ──────────────────────────────────────────────────────────
class SessionRecorder:
    """
    Manages frame recording across all questions in an interview session.

    Typical integration with Interview Controller:

        recorder = SessionRecorder()
        recorder.start_session()

        for q in questions:
            display_question(q)
            recorder.start_question(q.id, q.text)
            wait_for_answer()
            report = recorder.end_question()
            send_to_feedback_module(report)

        all_reports = recorder.get_session_summary()
    """

    def __init__(self, timeline_resolution_seconds: float = 0.5):
        """
        Args:
            timeline_resolution_seconds: how often to sample for the
                                         emotion timeline (default every 0.5s)
        """
        self._frames:       List[FrameData] = []
        self._q_id:         int  = 0
        self._q_text:       str  = ''
        self._q_start:      float = 0.0
        self._recording:    bool  = False
        self._timeline_res: float = timeline_resolution_seconds
        self._all_reports:  List[dict] = []

    # ── Public API ────────────────────────────────────────────────────────────
    def start_session(self):
        """Call once at the start of the interview."""
        self._all_reports.clear()
        print('[SessionRecorder] Session started.')

    def start_question(self, question_id: int, question_text: str):
        """Call when the candidate begins answering a question."""
        self._frames    = []
        self._q_id      = question_id
        self._q_text    = question_text
        self._q_start   = time.time()
        self._recording = True
        print(f'[SessionRecorder] Recording Q{question_id}.')

    def record_frame(self, frame_data: FrameData):
        """
        Add one frame's data. Call this every frame while recording.
        Silently ignored if not currently recording.
        """
        if self._recording:
            self._frames.append(frame_data)

    def end_question(self) -> dict:
        """
        Stop recording and compute the QuestionReport.

        Returns:
            QuestionReport as a dict (JSON-serialisable).
        """
        self._recording = False
        duration = time.time() - self._q_start

        if not self._frames:
            print(f'[SessionRecorder] Warning: no frames for Q{self._q_id}.')
            report = self._empty_report(duration)
        else:
            report = self._aggregate(duration)

        report_dict = report.to_dict()
        self._all_reports.append(report_dict)
        print(f'[SessionRecorder] Q{self._q_id} done — '
              f'{len(self._frames)} frames, {duration:.1f}s.')
        return report_dict

    def get_session_summary(self) -> dict:
        """
        Returns aggregate stats across all questions in the session.
        Call at the end of the interview to hand off to Feedback Module.
        """
        if not self._all_reports:
            return {}

        avg_eye_contact = np.mean([r['eye_contact_pct']         for r in self._all_reports])
        avg_yaw_stab    = np.mean([r['head_pose']['yaw_stability'] for r in self._all_reports])
        all_emotions    = [r['dominant_emotion'] for r in self._all_reports]
        all_flags       = [f for r in self._all_reports for f in r['behavioral_flags']]

        return {
            'total_questions'      : len(self._all_reports),
            'avg_eye_contact_pct'  : round(float(avg_eye_contact), 1),
            'avg_head_stability'   : round(float(avg_yaw_stab), 1),
            'most_common_emotion'  : Counter(all_emotions).most_common(1)[0][0],
            'all_behavioral_flags' : list(set(all_flags)),
            'per_question_reports' : self._all_reports,
        }

    # ── Aggregation logic ─────────────────────────────────────────────────────
    def _aggregate(self, duration: float) -> QuestionReport:
        frames = self._frames

        # ── Dominant emotion + breakdown ────────────────────────────────────────
        # Averages actual probability strength across every frame, instead of
        # only counting which emotion "won" each frame. This means a genuine
        # smile during part of an otherwise neutral answer still shows up —
        # winner-take-all voting would wash it out completely if neutral was
        # the top pick on most frames.
        avg_all_probs = np.mean(
            [[f.emotion_probs[e] for e in EMOTION_NAMES] for f in frames],
            axis=0
        )
        ranked = sorted(
            zip(EMOTION_NAMES, avg_all_probs), key=lambda x: -x[1]
        )
        dominant = ranked[0][0]
        emotion_breakdown = [
            {'emotion': name, 'pct': round(float(pct) * 100, 1)}
            for name, pct in ranked[:3]
        ]

        # ── Emotion timeline (sampled at timeline_resolution_seconds) ─────────
        timeline = []
        t_cursor = 0.0
        while t_cursor <= duration:
            # Find frames closest to this timestamp
            window = [
                f for f in frames
                if abs(f.timestamp - t_cursor) <= self._timeline_res / 2
            ]
            if window:
                # Average probabilities in this window
                avg_p = np.mean(
                    [[f.emotion_probs[e] for e in EMOTION_NAMES] for f in window],
                    axis=0
                )
                top_i = int(np.argmax(avg_p))
                timeline.append({
                    'second'    : round(t_cursor, 1),
                    'emotion'   : EMOTION_NAMES[top_i],
                    'confidence': round(float(avg_p[top_i]), 3),
                })
            t_cursor += self._timeline_res

        # ── Emotion switch rate ───────────────────────────────────────────────
        emotions_seq   = [f.top_emotion for f in frames]
        switches       = sum(
            1 for i in range(1, len(emotions_seq))
            if emotions_seq[i] != emotions_seq[i - 1]
        )
        switch_rate = switches / max(len(emotions_seq) - 1, 1)

        # ── Eye contact ───────────────────────────────────────────────────────
        mesh_frames = [f for f in frames if f.facemesh_detected]
        if mesh_frames:
            gaze_counts = Counter(f.gaze_direction for f in mesh_frames)
            total_gaze  = len(mesh_frames)
            eye_contact_pct = (gaze_counts.get('camera', 0) / total_gaze) * 100
            gaze_breakdown  = {
                d: round((gaze_counts.get(d, 0) / total_gaze) * 100, 1)
                for d in ['camera', 'down', 'left', 'right', 'up']
            }
        else:
            eye_contact_pct = 0.0
            gaze_breakdown  = {d: 0.0 for d in ['camera','down','left','right','up']}

        # ── Head pose ─────────────────────────────────────────────────────────
        if mesh_frames:
            yaws   = [f.yaw   for f in mesh_frames]
            pitches= [f.pitch for f in mesh_frames]
            avg_yaw    = float(np.mean(yaws))
            avg_pitch  = float(np.mean(pitches))
            # Stability = 100 - normalised std (capped at 30 degrees = 0%)
            yaw_stab   = max(0.0, 100 - (float(np.std(yaws))   / 30) * 100)
            pitch_stab = max(0.0, 100 - (float(np.std(pitches)) / 30) * 100)
        else:
            avg_yaw = avg_pitch = 0.0
            yaw_stab = pitch_stab = 100.0

        # ── Peak stress moment ────────────────────────────────────────────────
        def stress_score(f: FrameData) -> float:
            p = f.emotion_probs
            return (p.get('fear', 0)    * 1.0 +
                    p.get('angry', 0)   * 0.8 +
                    p.get('disgust', 0) * 0.5 +
                    p.get('sad', 0)     * 0.3)

        peak_frame    = max(frames, key=stress_score)
        peak_stress_v = stress_score(peak_frame)
        peak_second   = peak_frame.timestamp
        peak_emotion  = peak_frame.top_emotion

        # ── Behavioral flags ──────────────────────────────────────────────────
        flags = self._generate_flags(
            eye_contact_pct, yaw_stab, switch_rate,
            peak_stress_v, dominant, duration
        )

        return QuestionReport(
            question_id         = self._q_id,
            question_text       = self._q_text,
            duration_seconds    = duration,
            frame_count         = len(frames),
            dominant_emotion    = dominant,
            emotion_breakdown   = emotion_breakdown,
            emotion_timeline    = timeline,
            emotion_switch_rate = switch_rate,
            eye_contact_pct     = eye_contact_pct,
            gaze_breakdown      = gaze_breakdown,
            avg_yaw             = avg_yaw,
            avg_pitch           = avg_pitch,
            yaw_stability       = yaw_stab,
            pitch_stability     = pitch_stab,
            peak_stress_second  = peak_second,
            peak_stress_value   = peak_stress_v,
            peak_stress_emotion = peak_emotion,
            behavioral_flags    = flags,
        )

    def _generate_flags(self, eye_contact_pct, yaw_stability,
                        switch_rate, peak_stress, dominant, duration) -> list:
        """
        Threshold-based insight strings.
        These are what the Feedback Module turns into natural language.
        """
        flags = []

        # Eye contact
        if eye_contact_pct >= 55:
            flags.append('Strong eye contact with camera lens maintained')
        elif eye_contact_pct >= 30:
            flags.append('Moderate eye contact — look at the lens more')
        else:
            flags.append('Limited eye contact — focus on the camera lens, not the screen')

        # Head pose stability
        if yaw_stability >= 80:
            flags.append('Stable head posture throughout')
        elif yaw_stability >= 55:
            flags.append('Some head movement detected')
        else:
            flags.append('Frequent head turning — possible distraction or nervousness')

        # Emotion stability
        if switch_rate <= 0.05:
            flags.append('Emotionally steady response')
        elif switch_rate <= 0.15:
            flags.append('Mild emotional variation during answer')
        else:
            flags.append('High emotional variability — possible nervousness or uncertainty')

        # Stress
        if peak_stress > 0.5:
            flags.append(f'Stress spike detected (peak at {peak_stress*100:.0f}%)')
        elif peak_stress > 0.25:
            flags.append('Mild stress detected during response')

        # Engagement
        if dominant == 'happy':
            flags.append('Positive engagement — candidate appeared enthusiastic')
        elif dominant == 'neutral':
            flags.append('Neutral composure maintained')
        elif dominant in ('fear', 'sad'):
            flags.append('Signs of low confidence or anxiety observed')

        return flags

    def _empty_report(self, duration: float) -> QuestionReport:
        return QuestionReport(
            question_id=self._q_id, question_text=self._q_text,
            duration_seconds=duration, frame_count=0,
            dominant_emotion='unknown', emotion_breakdown=[], emotion_timeline=[],
            emotion_switch_rate=0.0, eye_contact_pct=0.0,
            gaze_breakdown={}, avg_yaw=0.0, avg_pitch=0.0,
            yaw_stability=0.0, pitch_stability=0.0,
            peak_stress_second=0.0, peak_stress_value=0.0,
            peak_stress_emotion='unknown', behavioral_flags=['No data recorded'],
        )

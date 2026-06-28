"""
test_full_session.py
────────────────────
Simulates a complete 5-question interview using the CV module.
Run this to test everything end-to-end without needing the backend.

Controls:
    SPACE  — start answering the current question
    Q      — finish current answer and move to next question
    ESC    — quit at any time

Output:
    session_results.json   — full report saved to disk
    Console               — per-question reports + final summary
"""

import os
import sys
import json
import cv2
import numpy as np

# ── Allow running from any directory ──────────────────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from cv_pipeline        import CVPipeline
from feedback_generator import generate_session_feedback


# ── Interview questions ───────────────────────────────────────────────────────
QUESTIONS = [
    (1, "Tell me about yourself and your background."),
    (2, "What is your greatest professional strength?"),
    (3, "Describe a challenge you faced and how you overcame it."),
    (4, "Where do you see yourself in 5 years?"),
    (5, "Why should we hire you for this position?"),
]

WINDOW = 'AI Interview Simulator — CV Module Test'


# ── UI helpers ────────────────────────────────────────────────────────────────
def draw_overlay(frame, title_line1, title_line2, instruction,
                 recording=False, q_num=0, total_q=5):
    """Draw question text and instructions on the frame."""
    h, w = frame.shape[:2]
    overlay = frame.copy()

    # Top bar background
    cv2.rectangle(overlay, (0, 0), (w, 90), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # Question number badge
    badge_col = (0, 0, 200) if recording else (80, 80, 80)
    cv2.rectangle(frame, (10, 8), (90, 45), badge_col, -1)
    cv2.putText(frame, f'Q{q_num}/{total_q}', (15, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)

    # Question text (two lines if long)
    cv2.putText(frame, title_line1, (100, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    if title_line2:
        cv2.putText(frame, title_line2, (100, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

    # Instruction bar at bottom
    inst_col = (0, 180, 0) if not recording else (0, 0, 200)
    cv2.rectangle(frame, (0, h - 35), (w, h), (15, 15, 15), -1)
    cv2.putText(frame, instruction, (10, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, inst_col, 1, cv2.LINE_AA)

    # Recording dot
    if recording:
        cv2.circle(frame, (w - 20, 20), 8,  (0, 0, 220), -1)
        cv2.putText(frame, 'REC', (w - 50, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 220), 1)

    return frame


def wrap_question(text, max_chars=55):
    """Split long question into two display lines."""
    if len(text) <= max_chars:
        return text, ''
    split = text.rfind(' ', 0, max_chars)
    if split == -1:
        split = max_chars
    return text[:split], text[split:].strip()


def draw_question_summary(frame, report):
    """Show a brief summary card after each question ends."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (w//2 - 220, h//2 - 110),
                            (w//2 + 220, h//2 + 110), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

    cv2.putText(frame, f"Q{report['question_id']} Summary",
                (w//2 - 100, h//2 - 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

    lines = [
        f"Eye Contact : {report['eye_contact_pct']:.0f}%",
        f"Emotion     : {report['dominant_emotion'].capitalize()}",
        f"Stability   : {'High' if report['emotion_switch_rate'] < 0.08 else 'Moderate' if report['emotion_switch_rate'] < 0.15 else 'Low'}",
        f"Peak Stress : {report['peak_stress']['stress_value']*100:.0f}%",
    ]
    for i, line in enumerate(lines):
        cv2.putText(frame, line, (w//2 - 180, h//2 - 35 + i * 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (200, 220, 200), 1, cv2.LINE_AA)

    cv2.putText(frame, 'Press SPACE to continue to next question',
                (w//2 - 185, h//2 + 85),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 0), 1, cv2.LINE_AA)
    return frame


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  AI Interview Simulator — CV Module Test")
    print("  Controls: SPACE = start/continue  |  Q = end answer")
    print("=" * 60)

    cv_pipeline = CVPipeline(enable_face_mesh=True)
    cv_pipeline.start_session()

    all_reports = []

    for q_id, q_text in QUESTIONS:
        line1, line2 = wrap_question(q_text)

        # ── WAITING state: show question, wait for SPACE ──────────────────────
        print(f"\n{'─'*50}")
        print(f"Q{q_id}: {q_text}")
        print("Press SPACE to start answering...")

        while True:
            frame = cv_pipeline.read_frame()
            if frame is None:
                break
            display = draw_overlay(frame, line1, line2,
                                   'SPACE = start answering  |  ESC = quit',
                                   recording=False, q_num=q_id)
            cv2.imshow(WINDOW, display)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                break
            if key == 27:   # ESC
                cv_pipeline.release()
                return

        # ── RECORDING state: analyse frames, wait for Q ───────────────────────
        cv_pipeline.start_question(q_id, q_text)
        print("Recording... Press Q to finish your answer.")

        while True:
            frame = cv_pipeline.read_frame()
            if frame is None:
                break
            annotated = cv_pipeline.process_frame(frame)
            display   = draw_overlay(annotated, line1, line2,
                                     'Q = finish answer  |  ESC = quit',
                                     recording=True, q_num=q_id)
            cv2.imshow(WINDOW, display)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            if key == 27:
                cv_pipeline.release()
                return

        report = cv_pipeline.end_question()
        all_reports.append(report)

        # ── SUMMARY state: show quick stats, wait for SPACE ───────────────────
        print(f"\nQ{q_id} complete.")
        print(f"  Eye contact : {report['eye_contact_pct']:.0f}%")
        print(f"  Emotion     : {report['dominant_emotion']}")
        print(f"  Flags       : {report['behavioral_flags']}")

        while True:
            frame = cv_pipeline.read_frame()
            if frame is None:
                break
            display = draw_question_summary(frame.copy(), report)
            cv2.imshow(WINDOW, display)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' ') or key == 27:
                break

    # ── Session end ───────────────────────────────────────────────────────────
    summary  = cv_pipeline.end_session()
    feedback = generate_session_feedback(summary)
    cv_pipeline.release()

    # ── Print results ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  SESSION COMPLETE")
    print("=" * 60)
    print(f"\nOverall CV Score  : {feedback['overall_cv_score']}/100")
    print(f"Eye Contact       : {feedback['eye_contact_rating']}")
    print(f"Composure         : {feedback['composure_rating']}")
    print(f"Confidence Rating : {feedback['confidence_rating']}")
    print(f"\nStrengths:")
    for s in feedback['strengths']:
        print(f"  ✓ {s}")
    print(f"\nAreas to Improve:")
    for i in feedback['improvements']:
        print(f"  → {i}")
    print(f"\nSummary:\n  {feedback['overall_summary']}")

    print("\nPer-Question Feedback:")
    for q_fb in feedback['per_question_feedback']:
        print(f"\n  Q{q_fb['question_id']}: {q_fb['question_text']}")
        print(f"  {q_fb['full_paragraph']}")

    # ── Save to disk ──────────────────────────────────────────────────────────
    output = {
        'session_summary' : summary,
        'cv_feedback'     : feedback,
    }
    out_path = os.path.join(_DIR, 'session_results.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nFull results saved → {out_path}")


if __name__ == '__main__':
    main()

# CV Module — AI Smart Interview Simulator

Computer Vision module responsible for real-time behavioral analysis during interviews.

---

## What it does

Every webcam frame during a candidate's answer is analyzed for three signals:

| Signal | Source | Output |
|---|---|---|
| Facial Emotion | Your trained MobileNetV2 (.keras) | 7 emotion probabilities |
| Eye Contact / Gaze | MediaPipe Face Mesh (iris landmarks) | direction + eye contact % |
| Head Pose | MediaPipe Face Mesh (solvePnP) | pitch, yaw, roll angles |

These are aggregated per question into a structured JSON report.

---

## File Structure

```
cv_module/
├── __init__.py           # package entry — import CVPipeline from here
├── cv_pipeline.py        # main orchestrator — only file other modules need
├── emotion_model.py      # loads .keras model, runs prediction
├── face_mesh.py          # MediaPipe gaze + head pose
├── frame_analyzer.py     # combines all 3 signals per frame
├── session_recorder.py   # records frames, aggregates per question
└── models/
    └── fer_raf_combined_final.keras   ← place your model here
```

---

## Setup

```bash
pip install opencv-python tensorflow mediapipe numpy
```

Place your trained model at `cv_module/models/fer_raf_combined_final.keras`.

---

## Usage — Interview Controller Integration

```python
from cv_module import CVPipeline

# Initialize once
cv = CVPipeline(
    model_path       = 'cv_module/models/fer_raf_combined_final.keras',
    enable_face_mesh = True,   # set False if mediapipe causes issues
    camera_index     = 0,
)

cv.start_session()

for question in interview_questions:
    display_question_to_candidate(question)

    cv.start_question(question.id, question.text)

    while candidate_is_answering:
        frame = cv.read_frame()
        if frame is None:
            break
        annotated_frame = cv.process_frame(frame)
        show_to_interviewer(annotated_frame)   # or cv2.imshow(...)

    report = cv.end_question()
    # report is a dict — pass directly to Feedback Module
    feedback_module.receive_cv_report(report)

summary = cv.end_session()
cv.release()
```

---

## Output Format (per question)

```json
{
  "question_id": 2,
  "question_text": "Tell me about your greatest weakness.",
  "duration_seconds": 38.4,
  "frame_count": 1152,
  "dominant_emotion": "neutral",
  "emotion_timeline": [
    {"second": 0.0, "emotion": "neutral",  "confidence": 0.71},
    {"second": 0.5, "emotion": "neutral",  "confidence": 0.68},
    {"second": 5.0, "emotion": "fear",     "confidence": 0.52},
    {"second": 5.5, "emotion": "neutral",  "confidence": 0.61}
  ],
  "emotion_switch_rate": 0.08,
  "eye_contact_pct": 74.0,
  "gaze_breakdown": {
    "camera": 74.0,
    "down":   16.0,
    "left":    6.0,
    "right":   4.0,
    "up":      0.0
  },
  "head_pose": {
    "avg_yaw":         3.2,
    "avg_pitch":      -4.1,
    "yaw_stability":  91.0,
    "pitch_stability": 88.0
  },
  "peak_stress": {
    "timestamp_second": 5.0,
    "stress_value":     0.52,
    "emotion_at_peak":  "fear"
  },
  "behavioral_flags": [
    "Strong eye contact maintained",
    "Stable head posture throughout",
    "Mild stress detected during response"
  ]
}
```

---

## Run standalone demo

```bash
cd your_project_root
python cv_module/cv_pipeline.py
```

Press **Q** to end. Prints the full QuestionReport JSON to console.

---

## Disable MediaPipe (if version conflicts)

```python
cv = CVPipeline(
    model_path       = 'cv_module/models/fer_raf_combined_final.keras',
    enable_face_mesh = False,   # emotion only, no gaze/head pose
)
```

Eye contact and head pose fields will be 0 in the report.
Emotion detection works fully without MediaPipe.

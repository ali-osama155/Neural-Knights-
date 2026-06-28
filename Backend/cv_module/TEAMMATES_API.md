# CareerBoost Backend — Integration Guide
### What `cv_server.py` actually does, end to end

This replaces the old CV-module-only doc. `cv_server.py` is now the **single backend** for the whole site — auth, database, and the CV pipeline all live here. Read this instead of guessing from the code.

---

## Setup

```bash
pip install -r cv_module/requirements.txt flask
```

**Place the model file** (get it from the CV team's Drive link — too large for git):
```
cv_module/models/fer_raf_combined_final.keras
```

**Run the backend:**
```bash
python backend/cv_server.py
```
Starts on `http://localhost:5050`. Creates `backend/careerboost.db` automatically on first run, with the question bank pre-seeded.

**Run the frontend** (separate terminal — browsers block camera access on `file://`):
```bash
cd webdemo
python -m http.server 8080
```
Open `http://localhost:8080/login.html`.

---

## Auth — cookie-based, not tokens

The frontend and backend run on different ports (8080 / 5050), so this uses a **Flask signed session cookie**, not a bearer token. Every fetch call from the frontend must include `credentials: 'include'` or the cookie won't be sent/received.

```javascript
// Every request to the backend needs this
fetch('http://localhost:5050/cv/session/start', {
    method: 'POST',
    credentials: 'include',          // ← required, not optional
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_role: 'Software Engineer' }),
});
```

If you get unexplained 401s, check for `credentials: 'include'` first — it's the most common mistake.

### Auth endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/auth/register` | `{name, email, password}` | `{status, user: {id, email, name, created_at}}` |
| POST | `/auth/login` | `{email, password}` | same as above |
| GET | `/auth/me` | — | `{user: {...}}` or 401 |
| POST | `/auth/logout` | — | `{status: 'ok'}` |

Pages that require login redirect to `login.html` automatically — this is handled by `initAuthSession()` in `templatemo-glass-admin-script.js`, not something each page implements itself.

---

## How the camera pipeline actually works

**The browser owns the camera, not the backend.** This is the most important architectural fact — `cv_server.py` runs with `camera_index=None` and never touches `cv2.VideoCapture`. There is no MJPEG stream. The frontend calls `getUserMedia()` directly, shows the video natively, and posts individual still frames to the backend for analysis.

```
Browser: getUserMedia() → <video> element shows live feed (zero backend involvement)
Browser: every ~350ms, draws a frame to <canvas>, POSTs it as base64 JPEG
Backend: /cv/analyze-frame decodes it, runs face detection + emotion + gaze + head pose
Backend: returns a small JSON (face_detected, emotion, eye_contact) — NOT an image
Browser: uses that JSON only to toggle the green "face detected" ring — nothing else shown live
```

If you're building a new page that needs the camera, copy the pattern in `interview-session.js` — don't reach for `cv.process_frame()` or MJPEG streaming, that's not how this is wired anymore.

### Interview lifecycle endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/cv/session/start` | `{job_role}` | `{status, session_id}` |
| POST | `/cv/question/start` | `{question_id, question_text}` | `{status: 'recording'}` |
| POST | `/cv/analyze-frame` | `{frame: "data:image/jpeg;base64,..."}` | `{face_detected, top_emotion, top_confidence, eye_contact, gaze_direction}` |
| POST | `/cv/question/end` | — | full `QuestionReport` (see below) + `db_question_id` |
| POST | `/cv/session/end` | — | feedback object + `session_id` |

All five require login (401 if no valid session cookie).

---

## What `/cv/question/end` returns

```json
{
  "question_id": 2,
  "question_text": "What is your greatest strength?",
  "duration_seconds": 38.4,
  "frame_count": 1152,

  "dominant_emotion": "neutral",
  "emotion_breakdown": [
    {"emotion": "neutral", "pct": 73.4},
    {"emotion": "happy",   "pct": 16.3},
    {"emotion": "angry",   "pct": 2.1}
  ],
  "emotion_timeline": [
    {"second": 0.0, "emotion": "neutral", "confidence": 0.71}
  ],
  "emotion_switch_rate": 0.08,

  "eye_contact_pct": 74.0,
  "gaze_breakdown": {"camera": 74.0, "down": 16.0, "left": 6.0, "right": 4.0, "up": 0.0},

  "head_pose": {
    "avg_yaw": 3.2, "avg_pitch": -4.1,
    "yaw_stability": 91.0, "pitch_stability": 88.0
  },

  "peak_stress": {"timestamp_second": 5.0, "stress_value": 0.52, "emotion_at_peak": "fear"},

  "behavioral_flags": ["Strong eye contact maintained", "Mild stress detected during response"],

  "db_question_id": 17
}
```

`emotion_breakdown` is the top 3 emotions ranked by **average probability strength across every frame**, not just whichever emotion "won" the most frames. This matters — a brief smile during an otherwise neutral answer still shows up here even though `dominant_emotion` stays "neutral". Use `emotion_breakdown` for any UI that should reflect nuance, not just `dominant_emotion`.

`db_question_id` is what the audio/speech module uses to attach a transcript to this exact answer (see below).

---

## What `/cv/session/end` returns

```json
{
  "overall_cv_score": 74.2,
  "eye_contact_rating": "Strong",
  "composure_rating": "Stable",
  "confidence_rating": "Moderate",
  "dominant_emotion": "neutral",
  "strengths": ["Strong and consistent eye contact throughout the interview"],
  "improvements": ["Practice answers to high-stress questions to reduce anxiety"],
  "overall_summary": "Overall, you performed well across 3 interview questions...",
  "per_question_feedback": [ { "question_id": 1, "full_paragraph": "..." } ],
  "raw_scores": {"eye_contact": 92.0, "head_stability": 91.0, "emotion_stability": 96.0, "stress_management": 100.0},
  "session_id": 7
}
```

`session_id` is the real database row — `interview-session.js` redirects to `analytics.html?session=7` with it, and that page calls `GET /sessions/7` to render the actual per-question results.

---

## Database reads

| Method | Path | Auth | Returns |
|---|---|---|---|
| GET | `/sessions` | required | array of past sessions for the logged-in user, most recent first |
| GET | `/sessions/<id>` | required, must own it | session detail + all its questions (CV reports + transcripts) |
| GET | `/questions?role=...` | none | question bank for that role (falls back to "General") |
| GET | `/users/me/stats` | required | `{interviews_completed, avg_confidence_score}` — feeds the dashboard |

`GET /questions` is what replaced the old hardcoded array in `interview-session.js` — pass `?role=Software Engineer` etc. Falls back to General questions if the role isn't in the bank yet.

---

## Audio / Speech module integration point

Your module doesn't talk to the CV module's code at all — only to the same database row, via `db_question_id`.

```
POST /questions/<db_question_id>/transcript
Body: { "text": "...", any other fields you want }
→ { "status": "ok" }
```

Call this once your speech-to-text is done for a given answer. `cv_server.py` already created that question row when `/cv/question/end` fired — you're just filling in the `transcript` column on the same row. No timing coordination needed beyond knowing the id.

---

## Database schema

```
users           id, email, password_hash, name, created_at
sessions        id, user_id, job_role, started_at, ended_at, overall_score
questions       id, session_id, question_number, question_text,
                cv_report (json), transcript (json, nullable), duration_seconds
question_bank   id, job_role, text
```

`careerboost.db` is gitignored — every teammate gets their own fresh local file the first time they run `cv_server.py`.

---

## Frontend pages and what they expect

| Page | Needs |
|---|---|
| `login.html` / `register.html` | `templatemo-glass-admin-script.js`'s form handler — posts to `/auth/login` or `/auth/register` automatically via `data-auth-action` attribute on the `<form>` |
| `index.html` | `GET /users/me/stats` for the two real stat cards. Resume-dependent cards show `—` honestly until the Resume module exists |
| `users.html` | `GET /sessions` for the history table; role `<select>` feeds `interview-session.html?role=...` |
| `interview-session.html` + `.js` | The full camera flow described above |
| `analytics.html` | Only populates a results card if `?session=<id>` is in the URL — otherwise unchanged (resume-analysis content is a separate module's responsibility) |

---

## Disabling face mesh (if mediapipe version issues)

```python
cv = CVPipeline(enable_face_mesh=False)
```
Emotion detection still works fully. Eye contact and head pose fields will be 0/empty in the report. This has happened before from mediapipe version drift — pin your version if it breaks (`pip show mediapipe` to check what's working, then `pip install mediapipe==<that version>` for anyone hitting it).

---

## Files in this repo

| File | What it does |
|---|---|
| `backend/cv_server.py` | The entire backend — auth, database wiring, CV endpoints. Start here. |
| `backend/db.py` | SQLite schema + all read/write functions |
| `cv_module/cv_pipeline.py` | Orchestrates emotion model + face mesh + face detection per frame |
| `cv_module/emotion_model.py` | Loads and runs the trained `.keras` model |
| `cv_module/face_mesh.py` | Eye contact + head pose from MediaPipe landmarks |
| `cv_module/frame_analyzer.py` | Combines emotion + gaze + pose into one `FrameData` per frame |
| `cv_module/session_recorder.py` | Records frames per question, aggregates into the report shown above |
| `cv_module/feedback_generator.py` | Turns a report into the human-readable feedback object |
| `webdemo/interview-session.js` | The reference implementation for any camera-based page |
| `webdemo/templatemo-glass-admin-script.js` | Shared auth handling, theme, logout — used by every page |

# Neural Knights — AI Interview Platform

An AI-powered mock-interview platform: upload a CV, get role-tailored questions,
answer them on camera/mic, and receive automated scoring on both **what you said**
(BERT answer-quality model) and **how you said it** (real-time emotion / eye-contact
/ confidence analysis).

This package contains:

- **Frontend/** → `src/`, `public/`, `index.html`, `package.json` (React + Vite) — unchanged.
- **Backend/** → FastAPI backend, **updated** to include Sarah's fine-tuned BERT
  answer-evaluation model alongside all previously existing features.

---

## 1. Features preserved / included

| Feature                              | Status |
|---------------------------------------|--------|
| Authentication (register/login/JWT)   | ✅ working |
| CV upload & analysis                  | ✅ working |
| Question generation (role + skills)   | ✅ working |
| Text-to-speech / Speech-to-text       | ✅ working |
| Real-time emotion / confidence (CV)   | ✅ working |
| **Answer evaluation (BERT model)**    | ✅ **new** — `POST /api/v1/interviews/evaluate-answer` |
| **Session finalize / overall score**  | ✅ **new** — `POST /api/v1/interviews/sessions/{id}/finalize` |

All API route paths used by the frontend were cross-checked against the backend
router and match exactly (see section 5).

---

## 2. Running the Backend

```bash
cd Backend

# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# then edit .env and add your OPENAI_API_KEY / GEMINI_API_KEY, etc.

# 4. Place the trained answer-evaluation checkpoint (see section 3 below)

# 5. Start the server
uvicorn app.main:app --reload --port 8000
```

The API will be live at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

Database tables (SQLite, `recruitai.db`) are created automatically on first
startup — no manual migration step needed.

> **Note on the CV/emotion module:** `cv_module/models/` expects a Keras model
> file (e.g. `fer_raf_combined_final.keras`) for facial-emotion detection. Like
> `best_model.pt`, this file is not bundled (it's git-ignored due to size). If
> it's missing, the `/cv-start`, `/analyze-frame`, and `/cv-end` endpoints will
> return a 503 instead of crashing the server — every other feature still works.

---

## 3. Where to put `best_model.pt`

Sarah's fine-tuned BERT checkpoint is **not included** in this ZIP (it's a large
binary file). The model-loading code was left completely unchanged — just drop
the file in place:

```
Backend/app/ml/saved_model/best_model.pt
```

That's it — no code changes needed. On startup, `app/main.py`'s lifespan hook
calls `evaluation_service.preload()`, which loads the checkpoint into memory
(CPU or GPU, auto-detected) so the first real request isn't slow.

**If the checkpoint isn't there yet:** the server still starts normally. Only
`POST /api/v1/interviews/evaluate-answer` will respond with:
```json
{ "detail": "Evaluation model checkpoint not found at 'app/ml/saved_model/best_model.pt'. ..." }
```
(HTTP 503) until you add the file — every other endpoint is unaffected.

The first time the model loads, it will also download the `bert-base-uncased`
tokenizer/config from Hugging Face if it isn't already cached locally, so an
internet connection is needed on first run.

---

## 4. Running the Frontend

```bash
# from the project root (not Backend/)
npm install
npm run dev
```

This starts the Vite dev server, by default at `http://localhost:5173`
(the backend's CORS settings already allow this origin — see
`Backend/app/core/config.py`).

The frontend talks to the backend at `http://localhost:8000` by default. To
point it elsewhere, create a `.env` file in the project root:

```
VITE_API_URL=http://localhost:8000
```

**Run order:** start the Backend first (step 2 above), then the Frontend.

---

## 5. Verifying Frontend ↔ Backend route compatibility

Every API call made from `src/` was checked against the backend's router.
All paths match:

| Frontend call (src/)                                   | Backend route |
|----------------------------------------------------------|---------------|
| `POST /api/v1/auth/register`, `/login`                   | `auth.py` |
| `POST /api/v1/cv/upload`, `GET /cv/latest`                | `cv.py` |
| `POST /api/v1/interviews/generate-questions`              | `interviews.py` |
| `POST /api/v1/interviews/sessions`                        | `interviews.py` |
| `POST /api/v1/interviews/sessions/{id}/cv-start`          | `emotion.py` |
| `POST /api/v1/interviews/sessions/{id}/analyze-frame`     | `emotion.py` |
| `POST /api/v1/interviews/sessions/{id}/cv-end`            | `emotion.py` |
| `POST /api/v1/interviews/speech-to-text`                  | `interviews.py` |
| **`POST /api/v1/interviews/evaluate-answer`**              | `interviews.py` (new) |
| **`POST /api/v1/interviews/sessions/{id}/finalize`**       | `interviews.py` (new) |

The backend was also import-tested and boot-tested end-to-end (health check,
register, login, session create, evaluate-answer, finalize) to confirm it
starts cleanly and every route resolves correctly.

---

## 6. Testing the answer-evaluation feature

### Option A — via Swagger UI
1. Start the backend with `best_model.pt` in place.
2. Go to `http://localhost:8000/docs`.
3. Expand `POST /api/v1/interviews/evaluate-answer` → "Try it out".
4. Send:
   ```json
   {
     "question": "Tell me about a challenging project you worked on.",
     "answer": "I led a team migrating our monolith to microservices, which reduced deploy time by 60%."
   }
   ```
5. Expect a response like:
   ```json
   {
     "question": "Tell me about a challenging project you worked on.",
     "answer": "I led a team migrating our monolith to microservices, which reduced deploy time by 60%.",
     "score": 8.4,
     "feedback": "Strong answer"
   }
   ```

### Option B — via curl
```bash
curl -X POST http://localhost:8000/api/v1/interviews/evaluate-answer \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me about yourself.", "answer": "I am a backend engineer with 4 years of Python experience."}'
```

### Option C — full pipeline, through the frontend
1. Log in, upload a CV, and start an interview session.
2. Answer a question on camera — the frontend records your speech, sends it to
   `/speech-to-text`, then to `/evaluate-answer` with the `session_id` and
   `question_index` attached, so the score is saved onto that question.
3. Call `POST /interviews/sessions/{id}/finalize` (or finish the interview flow
   in the UI) to see the averaged `overall_score` across all answered questions.

### Testing without the checkpoint
If you don't have `best_model.pt` yet, `evaluate-answer` returns HTTP 503 with
a clear message rather than crashing — useful for confirming the rest of the
pipeline (question generation → TTS → STT) works before the model arrives.

---

## 7. What changed in this integration

- Replaced `Backend/` entirely with the updated FastAPI backend containing
  Sarah's BERT evaluation module (`app/ml/model.py`, `app/services/evaluation_service.py`)
  and the two new endpoints.
- Frontend (`src/`, `public/`, config files) is **untouched**.
- Fixed two pre-existing environment/dependency issues found while verifying
  the backend boots on a clean install:
  - Added `email-validator` to `requirements.txt` (required by Pydantic's
    `EmailStr`, used in auth/user schemas — was missing, would crash on import).
  - Pinned `bcrypt==4.0.1` in `requirements.txt` (newer `bcrypt` removed an
    attribute `passlib==1.7.4` depends on, which crashed password hashing on
    `/auth/register`).
- Added a `cv_report` column to the `InterviewSession` model (and to the
  automatic schema-sync step) so the CV/emotion report generated by
  `/sessions/{id}/cv-end` actually persists to the database instead of being
  silently dropped (it wasn't a mapped column before).
- Removed generated/environment junk (`__pycache__/`, the runtime SQLite DB,
  a leftover multi-megabyte debug dump, empty upload folders) so the ZIP only
  contains source.

Verification performed: every backend `.py` file was syntax-checked, the full
FastAPI app was import-tested with all 21 routes confirmed present, and a live
boot test exercised register → login → create session → evaluate-answer
(graceful 503 without the checkpoint) → finalize, end to end.

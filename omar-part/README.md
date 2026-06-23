# Neural-Knights-
# Neural-Knights — AI Smart Interview Simulator

AI-powered interview practice platform using computer vision, NLP, and speech analysis.

## Quick Start

### 1. Get the trained model
Download `fer_raf_combined_final.keras` from Google Drive:
https://drive.google.com/file/d/1FPzxR1xfZr4BfDKtlMJUDyoUsBiJg_T6/view?usp=drive_link

Place it at: `cv_module/models/fer_raf_combined_final.keras`

### 2. Install dependencies
pip install -r cv_module/requirements.txt flask werkzeug

### 3. Run the backend (Terminal 1)
python backend/cv_server.py

Creates `backend/careerboost.db` automatically on first run.

### 4. Run the frontend (Terminal 2)
cd webdemo
python -m http.server 8080

### 5. Open the browser
http://localhost:8080/login.html

---

## Project structure
backend/          Flask server — auth, database, CV endpoints
cv_module/        Computer vision module — emotion, gaze, head pose
webdemo/          Frontend HTML/CSS/JS

## CV Module API
See cv_module/TEAMMATES_API.md for full integration docs.

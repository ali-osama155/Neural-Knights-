# Neural Knights — FastAPI Backend

## Project Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── core/
│   │   ├── config.py            # Settings & env vars
│   │   ├── database.py          # SQLAlchemy async engine
│   │   └── security.py          # JWT auth helpers
│   ├── models/
│   │   └── models.py            # SQLAlchemy ORM models
│   ├── schemas/
│   │   └── schemas.py           # Pydantic request/response schemas
│   ├── api/
│   │   └── v1/
│   │       ├── router.py        # Aggregate all routers
│   │       └── endpoints/
│   │           ├── auth.py      # Login / register
│   │           ├── users.py     # Profile & user data
│   │           ├── cv.py        # CV upload & AI analysis
│   │           ├── interviews.py# Interview session management
│   │           └── chat.py      # AI chatbot
│   └── services/
│       ├── ai_service.py        # OpenAI / Claude integration
│       ├── cv_service.py        # CV parsing logic
│       └── storage_service.py   # File upload (local / S3)
├── tests/
│   └── test_endpoints.py
├── .env.example
├── requirements.txt
└── README.md
```

## Quick Start

```bash
# 1. Create virtual env
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and fill environment variables
cp .env.example .env

# 4. Run database migrations (auto-creates tables on startup)
# Tables are created automatically via SQLAlchemy on first run

# 5. Start the dev server
uvicorn app.main:app --reload --port 8000
```

## API Docs
- Swagger UI: http://localhost:8000/docs
- ReDoc:       http://localhost:8000/redoc

## Auth Flow
1. `POST /api/v1/auth/register` — create account
2. `POST /api/v1/auth/login`    — get JWT access token
3. Pass token as `Authorization: Bearer <token>` on all protected routes
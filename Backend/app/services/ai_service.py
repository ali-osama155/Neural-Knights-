"""
AI Service — Hybrid CV analysis: local lgbm model + OpenAI API fallback.
Also handles interview scoring and chat.
"""
import json
import logging
from app.core.config import get_settings
from app.services.cv_analyzer import analyze_cv_local

logger = logging.getLogger(__name__)
settings = get_settings()

# ── OpenAI client (may fail if no API key) ────────────────────────────────────
_client = None


def _get_openai_client():
    """Lazy-init OpenAI client. Returns None if unavailable."""
    global _client
    if _client is not None:
        return _client
    try:
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-xxx"):
            logger.warning("No valid OpenAI API key configured — using local model only")
            return None
        from openai import AsyncOpenAI
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return _client
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAI client: {e}")
        return None


# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_CV = """You are an expert HR recruiter and career coach.
Analyze the provided CV text and return a JSON object with these exact keys:
- score (float 0-100): Overall CV quality score
- skills (array of strings, max 12): Key technical/professional skills
- strengths (array of 3 short strings): Top 3 strengths shown in CV
- recommendations (array of 4 actionable strings): Improvement suggestions
- best_fit_role (string): Most suitable job role based on CV (e.g., "Senior Full-Stack Engineer")
Return ONLY valid JSON, no markdown."""

SYSTEM_INTERVIEW = """You are an expert interview coach.
Given a transcript of a job interview, evaluate the candidate and return JSON:
- overall_score (float 0-100)
- confidence_score (float 0-100)
- clarity_score (float 0-100)
- feedback (string, 2-3 sentences of overall feedback)
- question_scores (array of objects: {question_index, score, feedback})
Return ONLY valid JSON, no markdown."""

SYSTEM_CHAT = """You are a helpful AI recruitment assistant called RecruitAI.
You help candidates improve their CVs, prepare for interviews, and navigate job searches.
Be concise, encouraging, and specific. Use emojis sparingly."""


# ══════════════════════════════════════════════════════════════════════════════
# CV ANALYSIS — Hybrid: local model first, API enhancement
# ══════════════════════════════════════════════════════════════════════════════

async def analyze_cv(cv_text: str) -> dict:
    """
    Analyze a CV using hybrid pipeline:
    1. ALWAYS run local lgbm model (score, skills, strengths, recommendations, role)
    2. TRY OpenAI API to enhance recommendations and best_fit_role
    3. MERGE results — never fail even if API is down
    """
    # Step 1: Local model analysis (always runs, must not fail)
    logger.info("Running local lgbm model analysis...")
    local_result = analyze_cv_local(cv_text)
    logger.info(f"Local analysis: score={local_result['score']}, "
                f"skills={len(local_result['skills'])}, "
                f"role={local_result['best_fit_role']}")

    # Step 2: Try API enhancement
    client = _get_openai_client()
    if client:
        try:
            logger.info("Enhancing with OpenAI API...")
            api_result = await _call_openai_cv(client, cv_text)
            if api_result:
                # Merge: use local score + skills, API recommendations + role
                merged = {
                    'score': local_result['score'],  # Local model score
                    'skills': local_result['skills'] if local_result['skills'] else api_result.get('skills', []),
                    'strengths': api_result.get('strengths', local_result['strengths']),
                    'recommendations': api_result.get('recommendations', local_result['recommendations']),
                    'best_fit_role': api_result.get('best_fit_role', local_result['best_fit_role']),
                }
                logger.info("Merged local + API results successfully")
                return merged
        except Exception as e:
            logger.warning(f"OpenAI API enhancement failed (using local only): {e}")

    # Step 3: Return local-only results
    logger.info("Returning local-only analysis results")
    return local_result


async def _call_openai_cv(client, cv_text: str) -> dict | None:
    """Call OpenAI for CV analysis. Returns None on failure."""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_CV},
                {"role": "user", "content": f"CV TEXT:\n\n{cv_text[:8000]}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.warning(f"OpenAI CV call failed: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# INTERVIEW ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

async def analyze_interview(transcript: str, questions: list[str]) -> dict:
    """Score an interview transcript."""
    client = _get_openai_client()
    if not client:
        raise RuntimeError("OpenAI API key required for interview analysis")

    q_list = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    prompt = f"QUESTIONS:\n{q_list}\n\nTRANSCRIPT:\n{transcript[:10000]}"
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_INTERVIEW},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return json.loads(response.choices[0].message.content)


# ══════════════════════════════════════════════════════════════════════════════
# CHAT
# ══════════════════════════════════════════════════════════════════════════════

async def chat_with_ai(history: list[dict], user_message: str) -> str:
    """Multi-turn chat with conversation history."""
    client = _get_openai_client()
    if not client:
        return ("I'm currently running in offline mode without AI chat capability. "
                "Please configure your OpenAI API key to enable chat features.")

    messages = [{"role": "system", "content": SYSTEM_CHAT}]
    messages.extend(history[-20:])
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=600,
    )
    return response.choices[0].message.content
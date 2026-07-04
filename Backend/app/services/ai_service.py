"""
AI Service — Hybrid CV analysis: local lgbm model + OpenAI API fallback.
Also handles interview scoring and chat.
"""
import json
import logging
import google.generativeai as genai
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
# CHAT — powered by Gemini (OpenAI key is currently invalid/out of quota;
# Gemini is already used successfully for interview question generation)
# ══════════════════════════════════════════════════════════════════════════════

# NOTE: we no longer cache a single Gemini model instance globally. The system
# instruction now depends on the caller's CV/interview context, which differs
# per user/request, so a fixed cached model would leak stale or wrong context
# between users. Instead we cache the fact that `genai.configure(...)` has
# already run (cheap, global, context-independent) and build a lightweight
# `GenerativeModel` object per call with a dynamically-built system prompt.
# Creating a `GenerativeModel` does not make a network call, so this is cheap.
_gemini_configured = False


def _ensure_gemini_configured() -> bool:
    """Lazy-configure the Gemini SDK once. Returns True if usable."""
    global _gemini_configured
    if _gemini_configured:
        return True
    try:
        if not settings.GEMINI_API_KEY:
            logger.warning("No Gemini API key configured — chat unavailable")
            return False
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_configured = True
        return True
    except Exception as e:
        logger.warning(f"Failed to configure Gemini client: {e}")
        return False


def _build_chat_system_prompt(
    cv_analysis: dict | None = None,
    interview_results: dict | None = None,
) -> str:
    """
    Extend SYSTEM_CHAT with the candidate's actual CV analysis and interview
    results (when available) so responses are grounded in their real data
    instead of being generic.
    """
    context_sections = []

    if cv_analysis:
        skills = cv_analysis.get("skills") or []
        strengths = cv_analysis.get("strengths") or []
        recommendations = cv_analysis.get("recommendations") or []
        score = cv_analysis.get("score")
        best_fit_role = cv_analysis.get("best_fit_role")

        cv_lines = ["CANDIDATE'S CV ANALYSIS:"]
        if score is not None:
            cv_lines.append(f"- Overall CV score: {score}/100")
        if best_fit_role:
            cv_lines.append(f"- Best-fit role: {best_fit_role}")
        if skills:
            cv_lines.append(f"- Key skills: {', '.join(skills)}")
        if strengths:
            cv_lines.append(f"- Strengths: {', '.join(strengths)}")
        if recommendations:
            cv_lines.append(f"- Improvement recommendations: {', '.join(recommendations)}")

        if len(cv_lines) > 1:
            context_sections.append("\n".join(cv_lines))

    if interview_results:
        overall_score = interview_results.get("overall_score")
        confidence_score = interview_results.get("confidence_score")
        clarity_score = interview_results.get("clarity_score")
        feedback = interview_results.get("feedback")
        question_scores = interview_results.get("question_scores") or []

        interview_lines = ["CANDIDATE'S INTERVIEW RESULTS:"]
        if overall_score is not None:
            interview_lines.append(f"- Overall interview score: {overall_score}/100")
        if confidence_score is not None:
            interview_lines.append(f"- Confidence score: {confidence_score}/100")
        if clarity_score is not None:
            interview_lines.append(f"- Clarity score: {clarity_score}/100")
        if feedback:
            interview_lines.append(f"- Feedback: {feedback}")
        if question_scores:
            per_q = "; ".join(
                f"Q{q.get('question_index', i+1)}: {q.get('score')}/100"
                for i, q in enumerate(question_scores)
            )
            interview_lines.append(f"- Per-question scores: {per_q}")

        if len(interview_lines) > 1:
            context_sections.append("\n".join(interview_lines))

    if not context_sections:
        return SYSTEM_CHAT

    context_block = "\n\n".join(context_sections)
    return (
        f"{SYSTEM_CHAT}\n\n"
        "You have access to the following real data about the candidate you are "
        "currently talking to. Use it to personalize your answers — reference "
        "specific skills, scores, and recommendations where relevant instead of "
        "giving generic advice. Do not repeat this raw data verbatim; weave it "
        "naturally into your responses.\n\n"
        f"{context_block}"
    )


def _get_gemini_chat_model(system_instruction: str):
    """Build a Gemini model instance with the given system instruction.
    Returns None if Gemini is unavailable."""
    if not _ensure_gemini_configured():
        return None
    try:
        return genai.GenerativeModel(
            "models/gemini-2.5-flash",
            system_instruction=system_instruction,
        )
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini client: {e}")
        return None


async def chat_with_ai(
    history: list[dict],
    user_message: str,
    cv_analysis: dict | None = None,
    interview_results: dict | None = None,
) -> str:
    """
    Multi-turn chat with conversation history.

    cv_analysis: optional dict as returned by `analyze_cv()` (score, skills,
        strengths, recommendations, best_fit_role) for the current user.
    interview_results: optional dict as returned by `analyze_interview()`
        (overall_score, confidence_score, clarity_score, feedback,
        question_scores) for the current user, if an interview has been done.

    Both are optional so existing callers that don't pass them keep working
    exactly as before, just without personalization.
    """
    system_prompt = _build_chat_system_prompt(cv_analysis, interview_results)
    model = _get_gemini_chat_model(system_prompt)
    if not model:
        return ("I'm currently running in offline mode without AI chat capability. "
                "Please configure your Gemini API key to enable chat features.")

    # Gemini expects role "model" (not "assistant") and content under "parts"
    gemini_history = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [m["content"]]}
        for m in history[-20:]
    ]

    try:
        chat = model.start_chat(history=gemini_history)
        response = await chat.send_message_async(
            user_message,
            generation_config={"temperature": 0.7, "max_output_tokens": 600},
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini chat call failed: {e}")
        return "Sorry, I couldn't process that — please try again in a moment."
"""
AI Service — wraps OpenAI calls for CV analysis and interview scoring.
Swap the OpenAI client for the Anthropic SDK if preferred.
"""
import json
from openai import AsyncOpenAI
from app.core.config import get_settings

settings = get_settings()
_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_CV = """You are an expert HR recruiter and career coach.
Analyze the provided CV text and return a JSON object with these exact keys:
- score (float 0-100)
- skills (array of strings, max 12)
- strengths (array of 3 short strings)
- recommendations (array of 4 actionable strings)
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


async def analyze_cv(cv_text: str) -> dict:
    """Call OpenAI to score and analyze a CV."""
    response = await _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_CV},
            {"role": "user", "content": f"CV TEXT:\n\n{cv_text[:8000]}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return json.loads(response.choices[0].message.content)


async def analyze_interview(transcript: str, questions: list[str]) -> dict:
    """Score an interview transcript."""
    q_list = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    prompt = f"QUESTIONS:\n{q_list}\n\nTRANSCRIPT:\n{transcript[:10000]}"
    response = await _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_INTERVIEW},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return json.loads(response.choices[0].message.content)


async def chat_with_ai(history: list[dict], user_message: str) -> str:
    """Multi-turn chat with conversation history."""
    messages = [{"role": "system", "content": SYSTEM_CHAT}]
    messages.extend(history[-20:])  # keep last 20 turns for context
    messages.append({"role": "user", "content": user_message})

    response = await _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=600,
    )
    return response.choices[0].message.content
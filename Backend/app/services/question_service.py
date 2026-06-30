import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
print("GEMINI KEY LOADED:", settings.GEMINI_API_KEY[:8] if settings.GEMINI_API_KEY else "MISSING")

def generate_interview_questions(role: str, skills: list, num_questions: int = 10):
    """
    Takes role and skills from Ali's CV analysis
    Returns list of 10 interview questions (easy → intermediate → hard)
    """
    skills_str = ", ".join(skills) if isinstance(skills, list) else skills

    prompt = f"""You are an expert technical interviewer conducting a job interview.

The candidate is applying for the role of: {role}
Their skills include: {skills_str}

Generate exactly {num_questions} technical interview questions for this candidate.

Follow these rules strictly:
- Each question must be maximum 17 words long
- Start with easy questions (questions 1-3)
- Then intermediate questions (questions 4-7)
- Then hard questions (questions 8-10)
- Be specific to their role and skills
- Return ONLY the questions, numbered 1 to {num_questions}
- No explanations, no answers, no difficulty labels"""

    model = genai.GenerativeModel("models/gemini-2.5-flash")
    response = model.generate_content(prompt)

    raw_text = response.text.strip()
    lines = raw_text.split('\n')

    questions = []
    for line in lines:
        line = line.strip()
        if line and line[0].isdigit():
            question = line.split('.', 1)[-1].strip()
            question = question.split(')', 1)[-1].strip()
            if question:
                questions.append(question)

    return questions
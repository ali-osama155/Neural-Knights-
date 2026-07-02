# -*- coding: utf-8 -*-
"""
Adapter: takes the AI Interviewer module's transcript output format and
scores each candidate answer using the trained model.

Expected input format (a list of dicts), matching your interviewer module:
[
    {
        "question": "...",
        "status": "answered",          # or "skipped", etc.
        "transcript": [
            {"role": "interviewer", "text": "..."},
            {"role": "candidate", "text": "..."},
            ...
        ]
    },
    ...
]
"""

from inference import score_answer


def _extract_candidate_text(transcript):
    """Concatenates all candidate turns in a transcript into one answer string."""
    parts = [turn["text"] for turn in transcript if turn.get("role") == "candidate"]
    return " ".join(parts).strip()


def score_interview(interview_items):
    """
    interview_items: list of {question, status, transcript}
    Returns: list of {question, status, candidate_answer, score}
    """
    results = []
    for item in interview_items:
        question = item.get("question", "")
        status = item.get("status", "unknown")
        transcript = item.get("transcript", [])

        if status != "answered" or not transcript:
            results.append({
                "question": question,
                "status": status,
                "candidate_answer": "",
                "score": None,
            })
            continue

        candidate_answer = _extract_candidate_text(transcript)
        if not candidate_answer:
            results.append({
                "question": question,
                "status": status,
                "candidate_answer": "",
                "score": None,
            })
            continue

        score = score_answer(question, candidate_answer)
        results.append({
            "question": question,
            "status": status,
            "candidate_answer": candidate_answer,
            "score": round(score, 2),
        })

    return results


if __name__ == "__main__":
    example = [
        {
            "question": "What is overfitting and how can you prevent it?",
            "status": "answered",
            "transcript": [
                {"role": "interviewer", "text": "What is overfitting and how can you prevent it?"},
                {"role": "candidate", "text": "Overfitting happens when a model learns the training data too closely, including noise, and performs worse on new data. You can prevent it with regularization, cross-validation, or more training data."},
            ],
        }
    ]
    print(score_interview(example))

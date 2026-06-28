"""
feedback_generator.py
─────────────────────
Converts raw CV module JSON output into human-readable feedback text.

This is called by the Feedback Module — teammates don't need to know
anything about computer vision to use it.

Usage:
    from cv_module.feedback_generator import generate_session_feedback

    summary  = cv.end_session()          # from CVPipeline
    feedback = generate_session_feedback(summary)

    print(feedback['overall_cv_score'])           # e.g. 74.2
    print(feedback['per_question_feedback'][0])   # paragraph for Q1
"""

from typing import List


# ── Per-question feedback ─────────────────────────────────────────────────────
def generate_question_feedback(report: dict) -> dict:
    """
    Generates readable feedback for one interview question.

    Args:
        report: QuestionReport dict from cv.end_question()

    Returns:
        dict with keys:
            question_id, question_text,
            eye_contact_comment, emotion_comment,
            stress_comment, posture_comment,
            full_paragraph  (all comments joined into one text block)
    """
    lines = []

    # ── Eye contact ───────────────────────────────────────────────────────────
    ec = report.get('eye_contact_pct', 0)
    if ec >= 55:
        ec_comment = (f"You maintained strong eye contact with the camera lens ({ec:.0f}% of the time). "
                       "This projects confidence and direct engagement to the interviewer.")
    elif ec >= 30:
        ec_comment = (f"Your eye contact was moderate ({ec:.0f}%). "
                       "Try to look at the camera lens more often when speaking — "
                       "not the screen. The lens is what creates direct eye contact in video interviews.")
    else:
        ec_comment = (f"Limited camera eye contact was detected ({ec:.0f}%). "
                       "In video interviews, you must look at the camera LENS, not your screen. "
                       "Place a small sticker next to your lens as a reminder, "
                       "and practice keeping focus there while speaking.")
    lines.append(ec_comment)

    # ── Emotion and stability ─────────────────────────────────────────────────
    dom    = report.get('dominant_emotion', 'neutral')
    switch = report.get('emotion_switch_rate', 0)

    if dom == 'happy' and switch < 0.1:
        em_comment = ("You appeared enthusiastic and engaged — "
                      "a positive sign that you're interested in the role.")
    elif dom == 'happy' and switch >= 0.1:
        em_comment = ("You showed enthusiasm, though your expressions varied "
                      "quite a bit. Consistent positivity is more reassuring "
                      "for interviewers.")
    elif dom == 'neutral' and switch < 0.08:
        em_comment = ("You maintained calm, composed body language — "
                      "professional and appropriate for a formal interview setting.")
    elif dom == 'neutral' and switch >= 0.08:
        em_comment = ("Your composure was generally neutral, but expressions "
                      "fluctuated at times. Try to stay steady and focused "
                      "throughout your answer.")
    elif dom in ('fear', 'sad'):
        em_comment = ("Signs of anxiety or low confidence were detected. "
                      "This is normal — practice answering this question aloud "
                      "several times to build familiarity and reduce nerves.")
    elif dom == 'angry':
        em_comment = ("Your expression appeared tense during this answer. "
                      "Try to relax your facial muscles and approach the question "
                      "with calm confidence.")
    else:
        em_comment = ("Your emotional expression was varied during this answer. "
                      "Aim for steady, calm confidence throughout.")
    lines.append(em_comment)

    # ── Stress spike ──────────────────────────────────────────────────────────
    peak       = report.get('peak_stress', {})
    peak_val   = peak.get('stress_value', 0)
    peak_t     = peak.get('timestamp_second', 0)
    peak_emot  = peak.get('emotion_at_peak', '')

    if peak_val > 0.5:
        st_comment = (f"A noticeable stress spike was detected at {peak_t:.0f} seconds "
                      f"into your answer (emotion: {peak_emot}). "
                       "This may indicate hesitation on this topic. "
                       "Prepare a structured response and practice it until it feels natural.")
    elif peak_val > 0.25:
        st_comment = ("Mild stress was detected but well managed overall. "
                      "A small amount of nerves is completely normal in interviews.")
    else:
        st_comment = ("No significant stress was detected — well done.")
    lines.append(st_comment)

    # ── Head pose ─────────────────────────────────────────────────────────────
    head    = report.get('head_pose', {})
    yaw_stab = head.get('yaw_stability', 100)
    avg_yaw  = abs(head.get('avg_yaw', 0))

    if yaw_stab < 50:
        pos_comment = ("Frequent head movement was detected throughout your answer. "
                       "Keeping your head steady and your gaze forward "
                       "signals attentiveness and confidence.")
    elif avg_yaw > 15:
        pos_comment = ("Your head was turned slightly to one side during this answer. "
                       "Try to face the camera directly when speaking.")
    else:
        pos_comment = ("Your head posture was stable and forward-facing — good.")
    lines.append(pos_comment)

    full_paragraph = " ".join(lines)

    return {
        'question_id'       : report.get('question_id'),
        'question_text'     : report.get('question_text', ''),
        'eye_contact_comment': ec_comment,
        'emotion_comment'   : em_comment,
        'stress_comment'    : st_comment,
        'posture_comment'   : pos_comment,
        'full_paragraph'    : full_paragraph,
    }


# ── Full session feedback ─────────────────────────────────────────────────────
def generate_session_feedback(summary: dict) -> dict:
    """
    Generates the complete interview performance report from the session summary.

    Args:
        summary: dict from cv.end_session()

    Returns:
        dict with:
            overall_cv_score        float 0-100
            eye_contact_rating      'Strong' | 'Moderate' | 'Needs work'
            composure_rating        'Stable' | 'Moderate' | 'Unstable'
            confidence_rating       'High' | 'Moderate' | 'Low'
            dominant_emotion        str
            strengths               list of str
            improvements            list of str
            overall_summary         str (paragraph)
            per_question_feedback   list of dicts (one per question)
    """
    reports = summary.get('per_question_reports', [])

    # ── Aggregate across all questions ────────────────────────────────────────
    ec_avg   = summary.get('avg_eye_contact_pct', 0)
    stab_avg = summary.get('avg_head_stability',  0)
    dom_emot = summary.get('most_common_emotion', 'neutral')
    flags    = summary.get('all_behavioral_flags', [])

    avg_switch  = _safe_mean([r.get('emotion_switch_rate', 0) for r in reports])
    avg_stress  = _safe_mean([r.get('peak_stress', {}).get('stress_value', 0)
                              for r in reports])

    # ── Compute overall CV score (0-100) ──────────────────────────────────────
    # Weighted: eye contact 35%, head stability 25%, emotion stability 25%, stress 15%
    ec_score    = ec_avg                                    # already 0-100
    stab_score  = stab_avg                                  # already 0-100
    emot_score  = max(0, (1 - avg_switch * 5) * 100)        # switch rate → 0-100
    stress_score= max(0, (1 - avg_stress)  * 100)           # stress val → 0-100

    overall = round(
        ec_score    * 0.35 +
        stab_score  * 0.25 +
        emot_score  * 0.25 +
        stress_score* 0.15,
        1
    )

    # ── Ratings ───────────────────────────────────────────────────────────────
    ec_rating   = ('Strong'     if ec_avg   >= 55
                   else 'Moderate' if ec_avg   >= 30 else 'Needs work')
    comp_rating = ('Stable'     if stab_avg >= 70
                   else 'Moderate' if stab_avg >= 45 else 'Unstable')
    conf_rating = ('High'       if overall  >= 70
                   else 'Moderate' if overall  >= 50 else 'Low')

    # ── Strengths ─────────────────────────────────────────────────────────────
    strengths = []
    if ec_avg >= 55:
        strengths.append('Strong and consistent eye contact with the camera lens throughout the interview')
    if stab_avg >= 70:
        strengths.append('Stable head posture showing attentiveness')
    if avg_switch < 0.08:
        strengths.append('Emotionally steady and composed responses')
    if avg_stress < 0.25:
        strengths.append('Remained calm — no significant stress spikes detected')
    if dom_emot == 'happy':
        strengths.append('Positive and enthusiastic facial expressions')
    if not strengths:
        strengths.append('Completed all questions under interview conditions')

    # ── Areas for improvement ─────────────────────────────────────────────────
    improvements = []
    if ec_avg < 55:
        improvements.append('Increase eye contact by looking directly at the camera lens')
    if stab_avg < 45:
        improvements.append('Reduce head movement — keep gaze steady and forward')
    if avg_switch > 0.15:
        improvements.append('Work on emotional consistency — try to stay calm and neutral')
    if avg_stress > 0.35:
        improvements.append('Practice answers to high-stress questions to reduce anxiety')
    if dom_emot in ('fear', 'sad', 'angry'):
        improvements.append('Build confidence through mock interviews and answer preparation')
    if not improvements:
        improvements.append('Continue practising to maintain this level of performance')

    # ── Overall summary paragraph ─────────────────────────────────────────────
    summary_text = _build_summary_paragraph(
        overall, ec_avg, ec_rating, comp_rating, conf_rating,
        dom_emot, avg_stress, len(reports)
    )

    # ── Per-question feedback ─────────────────────────────────────────────────
    per_q = [generate_question_feedback(r) for r in reports]

    return {
        'overall_cv_score'     : min(overall, 100),
        'eye_contact_rating'   : ec_rating,
        'composure_rating'     : comp_rating,
        'confidence_rating'    : conf_rating,
        'dominant_emotion'     : dom_emot,
        'strengths'            : strengths,
        'improvements'         : improvements,
        'overall_summary'      : summary_text,
        'per_question_feedback': per_q,
        'raw_scores'           : {
            'eye_contact'       : round(ec_score,    1),
            'head_stability'    : round(stab_score,  1),
            'emotion_stability' : round(emot_score,  1),
            'stress_management' : round(stress_score,1),
        }
    }


# ── Helpers ───────────────────────────────────────────────────────────────────
def _safe_mean(values: list) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def _build_summary_paragraph(overall, ec_avg, ec_rating, comp_rating,
                              conf_rating, dom_emot, avg_stress, n_q) -> str:
    parts = []

    if overall >= 75:
        parts.append(
            f"Overall, you performed well across {n_q} interview questions, "
            f"achieving a behavioral score of {overall:.0f}/100."
        )
    elif overall >= 55:
        parts.append(
            f"You showed a solid foundation across {n_q} questions "
            f"with a behavioral score of {overall:.0f}/100, "
            "with clear areas to develop further."
        )
    else:
        parts.append(
            f"Your behavioral score was {overall:.0f}/100 across {n_q} questions. "
            "With focused practice, there is significant room for improvement."
        )

    parts.append(
        f"Eye contact was rated {ec_rating.lower()} ({ec_avg:.0f}% camera focus), "
        f"and your overall composure was {comp_rating.lower()}."
    )

    if dom_emot == 'happy':
        parts.append("You came across as enthusiastic and genuinely engaged.")
    elif dom_emot == 'neutral':
        parts.append("You maintained professional composure throughout.")
    elif dom_emot in ('fear', 'sad'):
        parts.append(
            "Some anxiety was visible — this is very common and improves "
            "significantly with practice."
        )

    if avg_stress < 0.25:
        parts.append("Stress levels were low, which is excellent.")
    elif avg_stress > 0.45:
        parts.append(
            "Notable stress was detected at points — focus on preparation "
            "for the questions that triggered the most anxiety."
        )

    return " ".join(parts)

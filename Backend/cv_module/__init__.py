"""
cv_module
─────────
Computer Vision module for the AI Smart Interview Simulator.

Quick start:
    from cv_module import CVPipeline
    from cv_module.feedback_generator import generate_session_feedback

    cv = CVPipeline()
    cv.start_session()
    cv.start_question(1, 'Tell me about yourself.')
    # ... process frames ...
    report   = cv.end_question()
    summary  = cv.end_session()
    feedback = generate_session_feedback(summary)
    cv.release()
"""

import os, sys
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from cv_module.cv_pipeline        import CVPipeline
from cv_module.feedback_generator import (generate_session_feedback,
                                          generate_question_feedback)

__all__    = ['CVPipeline', 'generate_session_feedback', 'generate_question_feedback']
__version__ = '2.0.0'

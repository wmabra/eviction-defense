"""
Official court form filler — fills eviction answer forms for any state.
Handles both fillable PDFs and scanned PDFs via coordinate overlay.
"""

import os
import logging
from app.services.pdf_overlay import fill_answer_form  # noqa: F401

logger = logging.getLogger(__name__)

# Keep backward-compatible references
FORMS_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "counties")

def get_supported_states() -> list:
    """Return list of state codes we have forms for."""
    from app.services.state_configs import STATE_CONFIGS
    return sorted(STATE_CONFIGS.keys())

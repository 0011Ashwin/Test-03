import os
import sys
import google.auth

# Ensure the agent directory is in the path
sys.path.insert(0, os.path.dirname(__file__))

# --- Configuration ---
os.environ["ADK_SUPPRESS_EXPERIMENTAL_FEATURE_WARNINGS"] = "True"

try:
    _, project_id = google.auth.default()
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id) # type: ignore
except Exception:
    pass

if "GEMINI_API_KEY" in os.environ and "GOOGLE_API_KEY" not in os.environ:
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

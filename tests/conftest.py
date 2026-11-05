import os

# Tests must be deterministic and offline: no Claude calls, no log files.
os.environ["TUNEJUDGE_USE_LLM"] = "0"
os.environ["TUNEJUDGE_LOG_FILE"] = "0"

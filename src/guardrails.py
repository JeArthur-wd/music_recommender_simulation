"""
Guardrails for the recommender: checks that run before and after the model.

1. check_request()           - free-text input: empty, too long, control chars,
                               prompt-injection attempts, unsafe requests.
2. sanitize_profile()        - a preference dict (from a person, the rule planner
                               or the LLM): normalize strings, clamp numbers,
                               drop unknown keys, warn about values the catalog lacks.
3. validate_recommendations() - the output: songs exist in the catalog, no
                               duplicates, finite and descending scores, every
                               pick has an explanation.

Each check returns its findings instead of raising, so callers decide whether
a problem blocks the run (errors) or is just surfaced to the user (warnings).
"""

import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

try:
    from .logging_config import get_logger
except ImportError:
    from logging_config import get_logger

logger = get_logger("guardrails")

MAX_REQUEST_CHARS = 500
MAX_MOOD_TAGS = 5
MIN_DECADE, MAX_DECADE = 1900, 2030

# Profile keys score_song understands, with the type each must have
ALLOWED_KEYS = {
    "favorite_genre": str,
    "favorite_mood": str,
    "target_energy": float,
    "likes_acoustic": bool,
    "preferred_decade": int,
    "mood_tags": list,
    "prefers_popular": bool,
    "wants_instrumental": bool,
    "likes_rap": bool,
}
REQUIRED_KEYS = ("favorite_genre", "favorite_mood", "target_energy")

INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above) (instructions|prompts?|rules)",
    r"disregard (the |your )?(instructions|rules|system prompt)",
    r"(reveal|print|show|repeat) (your|the) (system )?(prompt|instructions)",
    r"you are now\b",
    r"\bact as (a|an) (?!dj\b)",
    r"\bjailbreak\b",
    r"</?(system|assistant|instructions?)>",
]
# Requests that have nothing to do with music and that we refuse outright
BLOCKED_PATTERNS = [
    r"\b(credit card|password|social security|ssn)\b",
    r"\b(make|build) (a )?(bomb|weapon|explosive)\b",
]


@dataclass
class GuardrailResult:
    """Outcome of a guardrail check."""
    ok: bool
    text: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def check_request(text) -> GuardrailResult:
    """Validate and clean a free-text request before it reaches retrieval or the LLM."""
    if not isinstance(text, str):
        return GuardrailResult(False, errors=["Request must be text."])

    # Normalize unicode look-alikes, drop control characters, collapse whitespace
    cleaned = unicodedata.normalize("NFKC", text)
    cleaned = re.sub(r"\s", " ", cleaned)  # tabs/newlines become spaces before control chars are dropped
    cleaned = "".join(ch for ch in cleaned if ch.isprintable())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    result = GuardrailResult(True, cleaned)
    if not cleaned:
        result.ok = False
        result.errors.append("Request is empty. Describe what you want to listen to.")
    elif len(cleaned) > MAX_REQUEST_CHARS:
        result.ok = False
        result.errors.append(
            f"Request is {len(cleaned)} characters; the limit is {MAX_REQUEST_CHARS}."
        )

    lowered = cleaned.lower()
    if any(re.search(p, lowered) for p in INJECTION_PATTERNS):
        result.ok = False
        result.errors.append(
            "Request looks like an attempt to override the assistant's instructions."
        )
    if any(re.search(p, lowered) for p in BLOCKED_PATTERNS):
        result.ok = False
        result.errors.append("Request is outside what a music recommender can help with.")

    if not result.ok:
        logger.warning("Request blocked: %s", "; ".join(result.errors))
    return result


def _to_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "y"}
    return bool(value)


def sanitize_profile(prefs: Dict, songs: List[Dict]) -> Tuple[Dict, List[str]]:
    """
    Return (clean_prefs, warnings). Never raises on bad values: it repairs what
    it can and reports what it changed, so the recommender only sees valid input.
    """
    warnings = []
    genres = {song["genre"].lower() for song in songs}
    moods = {song["mood"].lower() for song in songs}
    tags = {tag for song in songs for tag in song.get("mood_tags", [])}
    clean = {}

    for key, value in (prefs or {}).items():
        if key not in ALLOWED_KEYS:
            warnings.append(f"Ignored unknown preference '{key}'.")
            continue
        if value is None:
            continue
        kind = ALLOWED_KEYS[key]
        try:
            if kind is not list and isinstance(value, (list, tuple, set, dict)):
                raise TypeError
            if kind is str:
                clean[key] = " ".join(str(value).split()).lower()
            elif kind is float:
                number = float(value)
                if math.isnan(number) or math.isinf(number):
                    raise ValueError
                clean[key] = number
            elif kind is int:
                clean[key] = int(value)
            elif kind is bool:
                clean[key] = _to_bool(value)
            elif kind is list:
                if isinstance(value, dict) or not isinstance(value, (str, list, tuple, set)):
                    raise TypeError
                items = [value] if isinstance(value, str) else list(value)
                clean[key] = [" ".join(str(v).split()).lower() for v in items if str(v).strip()]
        except (TypeError, ValueError, OverflowError):
            warnings.append(f"Dropped '{key}': {value!r} is not a valid {kind.__name__}.")

    for key in ("favorite_genre", "favorite_mood"):
        if not clean.get(key):
            clean[key] = ""
            warnings.append(f"No {key.split('_')[1]} given; that preference will not score.")

    if "target_energy" not in clean:
        clean["target_energy"] = 0.5
        warnings.append("No target energy given; using 0.5 (medium).")
    elif not 0.0 <= clean["target_energy"] <= 1.0:
        original = clean["target_energy"]
        clean["target_energy"] = min(max(original, 0.0), 1.0)
        warnings.append(f"Target energy {original} is outside 0-1; clamped to {clean['target_energy']}.")

    clean.setdefault("likes_acoustic", False)

    if clean["favorite_genre"] and clean["favorite_genre"] not in genres:
        warnings.append(f"Genre '{clean['favorite_genre']}' is not in the catalog, so no song can match it.")
    if clean["favorite_mood"] and clean["favorite_mood"] not in moods:
        warnings.append(f"Mood '{clean['favorite_mood']}' is not in the catalog, so no song can match it.")

    decade = clean.get("preferred_decade")
    if decade is not None:
        if not MIN_DECADE <= decade <= MAX_DECADE:
            warnings.append(f"Decade {decade} is out of range; ignored.")
            del clean["preferred_decade"]
        elif decade % 10:
            clean["preferred_decade"] = decade - decade % 10
            warnings.append(f"Decade {decade} rounded down to {clean['preferred_decade']}.")

    if "mood_tags" in clean:
        known = [t for t in dict.fromkeys(clean["mood_tags"]) if t in tags]
        unknown = [t for t in clean["mood_tags"] if t not in tags]
        if unknown:
            warnings.append(f"Unknown mood tags ignored: {', '.join(unknown)}.")
        if len(known) > MAX_MOOD_TAGS:
            warnings.append(f"Kept the first {MAX_MOOD_TAGS} mood tags.")
        clean["mood_tags"] = known[:MAX_MOOD_TAGS]
        if not clean["mood_tags"]:
            del clean["mood_tags"]

    for warning in warnings:
        logger.info("Profile guardrail: %s", warning)
    return clean, warnings


def validate_recommendations(results: List[Tuple], songs: List[Dict], k: int) -> List[str]:
    """Return a list of problems with a ranked result list (empty means it passed)."""
    problems = []
    catalog = {song["id"]: song for song in songs}
    if len(results) > k:
        problems.append(f"Returned {len(results)} songs but k={k}.")
    if songs and k > 0 and not results:
        problems.append("Returned no songs from a non-empty catalog.")

    seen = set()
    previous = math.inf
    for rank, (song, score, explanation) in enumerate(results, start=1):
        if song.get("id") not in catalog or catalog[song["id"]]["title"] != song.get("title"):
            problems.append(f"#{rank} '{song.get('title')}' is not in the catalog.")
        if song.get("id") in seen:
            problems.append(f"#{rank} '{song.get('title')}' is a duplicate.")
        seen.add(song.get("id"))
        if not isinstance(score, (int, float)) or not math.isfinite(score):
            problems.append(f"#{rank} has a non-numeric score {score!r}.")
        elif score > previous + 1e-9:
            problems.append(f"#{rank} scores higher than #{rank - 1}; ranking is out of order.")
        else:
            previous = score
        if not str(explanation).strip():
            problems.append(f"#{rank} '{song.get('title')}' has no explanation.")

    for problem in problems:
        logger.error("Output guardrail: %s", problem)
    return problems

"""
Agentic recommendation workflow.

The agent turns a free-text request ("something calm for studying on a rainy
day") into ranked, explained recommendations through observable steps:

    1. guard_input   - guardrails.check_request() blocks empty, oversized,
                       injection-style or off-limits requests
    2. retrieve      - RAG: BM25 over data/knowledge_base.json
    3. plan          - build a listener profile, grounded in the retrieved docs
                       (Claude if available, otherwise the rule-based planner)
    4. validate      - guardrails.sanitize_profile() repairs/flags the profile
    5. recommend     - the existing scoring + ranking engine
    6. self_check    - critique the result; if a fixable problem is found,
                       revise the plan and go back to step 5 (bounded loop)
    7. guard_output  - guardrails.validate_recommendations()

Every step is appended to a trace (shown with `--trace` and in the web UI) and
logged, so a run can be audited after the fact.
"""

import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    from .guardrails import check_request, sanitize_profile, validate_recommendations
    from .llm import llm_available, llm_plan_profile
    from .logging_config import get_logger, log_event
    from .rag import KnowledgeBase, Retrieved
    from .recommender import GENRE_FIRST, ScoringMode, max_possible_score, recommend_songs
except ImportError:
    from guardrails import check_request, sanitize_profile, validate_recommendations
    from llm import llm_available, llm_plan_profile
    from logging_config import get_logger, log_event
    from rag import KnowledgeBase, Retrieved
    from recommender import GENRE_FIRST, ScoringMode, max_possible_score, recommend_songs

logger = get_logger("agent")

MAX_REVISIONS = 2
LOW_CONFIDENCE = 0.5
ENERGY_CONFLICT_GAP = 0.4

GENRE_ALIASES = {
    "hip hop": "hip-hop", "rap": "hip-hop", "rnb": "r&b", "r and b": "r&b",
    "kpop": "k-pop", "k pop": "k-pop", "lo fi": "lofi", "lo-fi": "lofi",
    "electronic": "edm", "classical music": "classical",
}
NEGATORS = {"no", "not", "without", "never", "hate", "except", "avoid", "isn't", "nothing"}
LOW_ENERGY_WORDS = {"sleepy", "quiet", "soft", "gentle", "slow", "calm", "peaceful", "mellow",
                    "low energy", "low-energy", "relaxing", "soothing"}
HIGH_ENERGY_WORDS = {"energetic", "high energy", "high-energy", "hype", "pumped", "intense",
                     "loud", "fast", "banger", "bangers", "upbeat", "heavy"}
POPULAR_WORDS = {"popular", "mainstream", "hits", "hit songs", "well known", "top songs"}
UNDERGROUND_WORDS = {"underground", "obscure", "hidden gem", "hidden gems", "deep cut",
                     "deep cuts", "unknown", "lesser known", "niche"}
INSTRUMENTAL_PHRASES = {"instrumental", "no vocals", "no lyrics", "without lyrics", "without vocals"}
RAP_WORDS = {"rap", "rapping", "bars", "rapper", "spoken word"}


@dataclass
class TraceStep:
    """One observable step of an agent run."""
    step: str
    detail: str


@dataclass
class AgentResult:
    """Everything an agent run produced, including how it got there."""
    run_id: str
    request: str
    status: str                       # ok | blocked | needs_clarification | error
    message: str = ""
    profile: Dict = field(default_factory=dict)
    recommendations: List[Tuple] = field(default_factory=list)
    confidence: float = 0.0
    planner: str = ""
    sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    trace: List[TraceStep] = field(default_factory=list)
    diversity: bool = False
    excluded_genres: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Rule-based planner (offline, deterministic)
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    text = re.sub(r"[^a-z0-9&'%.\- ]", " ", text.lower())
    text = re.sub(r"(?<![0-9])\.|\.(?![0-9])", " ", text)  # keep '.' only inside numbers
    return " " + re.sub(r"\s+", " ", text).strip() + " "


NEGATION_SPAN = re.compile(
    r"\b(?:no|not|without|never|hate|avoid|except|nothing)\s+(?:too\s+|so\s+|very\s+|any\s+)?[a-z0-9&-]+",
    re.IGNORECASE,
)


def strip_negations(text: str) -> str:
    """Remove negated phrases ('not too loud', 'no country') so retrieval ignores them."""
    return re.sub(r"\s+", " ", NEGATION_SPAN.sub(" ", text)).strip()


def _find(phrase: str, text: str) -> List[int]:
    """Start offsets of a whole-word phrase in normalized text (hyphen and space are equivalent)."""
    pattern = r"(?<![a-z0-9&])" + re.escape(phrase).replace(r"\-", "[- ]").replace(r"\ ", "[- ]") + r"(?![a-z0-9&])"
    return [m.start() for m in re.finditer(pattern, text)]


def _negated(text: str, start: int) -> bool:
    """True if one of the two words before position `start` is a negator ('no country')."""
    before = text[:start].split()[-2:]
    return any(word in NEGATORS for word in before)


def _mentions(phrases, text: str) -> Tuple[bool, bool]:
    """(mentioned positively, mentioned negatively) for any phrase in the set."""
    positive = negative = False
    for phrase in phrases:
        for start in _find(phrase, text):
            if _negated(text, start):
                negative = True
            else:
                positive = True
    return positive, negative


def _match_terms(text: str, vocabulary: List[str], aliases: Dict[str, str] = None) -> Tuple[List[str], set]:
    """Catalog terms mentioned in text, longest first, plus the set of negated ones."""
    candidates = {term: term for term in vocabulary}
    candidates.update(aliases or {})
    first_seen, negated, taken = {}, set(), []
    for phrase in sorted(candidates, key=len, reverse=True):
        for start in _find(phrase, text):
            if any(s <= start < e for s, e in taken):  # 'pop' inside 'indie pop'
                continue
            taken.append((start, start + len(phrase)))
            term = candidates[phrase]
            if _negated(text, start):
                negated.add(term)
            else:
                first_seen[term] = min(start, first_seen.get(term, start))
    # Earliest mention first: "jazz or blues" prefers jazz
    return sorted(first_seen, key=first_seen.get), negated


def _decade(text: str) -> Optional[int]:
    match = re.search(r"(?<![0-9])(19|20)?([0-9])0'?s(?![a-z])", text)
    if not match:
        return None
    century, digit = match.group(1), int(match.group(2))
    if century:
        return int(century) * 100 + digit * 10
    return 2000 + digit * 10 if digit <= 2 else 1900 + digit * 10


def rule_based_plan(request: str, retrieved: List[Retrieved], songs: List[Dict]) -> Tuple[Dict, List[str]]:
    """
    Build a profile from explicit mentions in the request, filled in by retrieved
    hints. Returns (prefs, excluded_genres), where excluded genres were negated
    in the request ("no country").
    """
    text = _normalize(request)
    genres = sorted({s["genre"] for s in songs})
    moods = sorted({s["mood"] for s in songs})
    tags = sorted({t for s in songs for t in s.get("mood_tags", [])})

    named_genres, banned_genres = _match_terms(text, genres, GENRE_ALIASES)
    named_moods, banned_moods = _match_terms(text, moods)
    named_tags, banned_tags = _match_terms(text, tags)

    def voted_hint(key, allowed, banned):
        """Score-weighted vote across retrieved docs, so one strong but off-target
        match ("slow mornings" for "morning run") can't outvote several agreeing ones."""
        votes: Dict[str, float] = {}
        for r in retrieved:
            value = r.doc.hints.get(key)
            if not (value in allowed and value not in banned) and key == "genre":
                # A doc for a genre the catalog lacks (or the user ruled out) points at related genres
                value = next((g for g in r.doc.hints.get("related_genres", [])
                              if g in allowed and g not in banned), None)
            if value in allowed and value not in banned:
                votes[value] = votes.get(value, 0.0) + r.score
        # max() keeps the first-seen value on ties, i.e. the higher-ranked doc
        return max(votes, key=votes.get) if votes else None

    genre = named_genres[0] if named_genres else voted_hint("genre", genres, banned_genres)
    mood = named_moods[0] if named_moods else voted_hint("mood", moods, banned_moods)
    # Docs that agree with the chosen genre or mood lead the remaining hints
    agreeing = [r for r in retrieved
                if r.doc.hints.get("genre") == genre or r.doc.hints.get("mood") == mood]
    lead = agreeing or retrieved
    prefs = {"favorite_genre": genre or "", "favorite_mood": mood or ""}

    # Energy: explicit number > energy words > retrieved hints > the genre's catalog average
    explicit = re.search(r"energy\D{0,10}(\d+(?:\.\d+)?)\s*(%)?", text) or \
        re.search(r"(\d+(?:\.\d+)?)\s*(%)\s*energy", text)
    low_pos, low_neg = _mentions(LOW_ENERGY_WORDS, text)
    high_pos, high_neg = _mentions(HIGH_ENERGY_WORDS, text)
    if explicit:
        value = float(explicit.group(1))
        prefs["target_energy"] = value / 100 if explicit.group(2) or value > 1 else value
    elif high_pos and not low_pos:
        prefs["target_energy"] = 0.85 if not high_neg else 0.6
    elif low_pos and not high_pos:
        prefs["target_energy"] = 0.25
    elif high_neg:            # "nothing too loud"
        prefs["target_energy"] = 0.4
    elif low_neg:             # "not too slow"
        prefs["target_energy"] = 0.7
    else:
        weighted = [(r.doc.hints["energy"], r.score) for r in lead[:2] if "energy" in r.doc.hints]
        genre_energy = [s["energy"] for s in songs if s["genre"] == genre]
        if genre in named_genres and genre_energy:
            prefs["target_energy"] = round(sum(genre_energy) / len(genre_energy), 2)
        elif weighted:
            prefs["target_energy"] = round(sum(e * w for e, w in weighted) / sum(w for _, w in weighted), 2)
        else:
            prefs["target_energy"] = 0.5

    acoustic_pos, acoustic_neg = _mentions({"acoustic", "unplugged"}, text)
    if acoustic_pos or acoustic_neg:
        prefs["likes_acoustic"] = acoustic_pos and not acoustic_neg
    else:
        prefs["likes_acoustic"] = bool(lead and lead[0].doc.hints.get("likes_acoustic"))

    wanted_tags = [t for t in named_tags if t not in banned_tags]
    for r in lead[:2]:
        wanted_tags += [t for t in r.doc.hints.get("mood_tags", []) if t in tags and t not in banned_tags]
    wanted_tags = list(dict.fromkeys(wanted_tags))[:3]
    if wanted_tags:
        prefs["mood_tags"] = wanted_tags

    decade = _decade(text)
    if decade:
        prefs["preferred_decade"] = decade

    popular, _ = _mentions(POPULAR_WORDS, text)
    underground, _ = _mentions(UNDERGROUND_WORDS, text)
    if popular != underground:
        prefs["prefers_popular"] = popular
    elif lead and "prefers_popular" in lead[0].doc.hints:
        prefs["prefers_popular"] = lead[0].doc.hints["prefers_popular"]

    if any(_find(p, text) for p in INSTRUMENTAL_PHRASES) or (lead and lead[0].doc.hints.get("wants_instrumental")):
        prefs["wants_instrumental"] = True
    rap, _ = _mentions(RAP_WORDS, text)
    if rap:
        prefs["likes_rap"] = True
    return prefs, sorted(banned_genres)


def mentions_catalog_term(request: str, songs: List[Dict]) -> bool:
    """True if the request names any catalog genre, mood or tag directly."""
    text = _normalize(request)
    vocab = {s["genre"] for s in songs} | {s["mood"] for s in songs} | set(GENRE_ALIASES)
    vocab |= {t for s in songs for t in s.get("mood_tags", [])}
    return any(_find(term, text) for term in vocab)


# ---------------------------------------------------------------------------
# The agent
# ---------------------------------------------------------------------------

class RecommenderAgent:
    """Plans, acts, checks its own work, and revises: see the module docstring."""

    def __init__(self, songs: List[Dict], kb: KnowledgeBase = None,
                 use_llm: Optional[bool] = None, max_revisions: int = MAX_REVISIONS):
        self.songs = songs
        self.kb = kb or KnowledgeBase.load()
        self.use_llm = llm_available() if use_llm is None else (use_llm and llm_available())
        self.max_revisions = max_revisions
        self.genres = {s["genre"] for s in songs}

    def run(self, request: str, k: int = 5, mode: ScoringMode = GENRE_FIRST,
            diversity: bool = False) -> AgentResult:
        result = AgentResult(run_id=uuid.uuid4().hex[:8], request=str(request), status="ok",
                             diversity=diversity)
        log = lambda step, detail: self._trace(result, step, detail)  # noqa: E731
        k = max(1, min(int(k), len(self.songs)))

        # 1. Input guardrail
        guard = check_request(request)
        if not guard.ok:
            result.status = "blocked"
            result.message = " ".join(guard.errors)
            log("guard_input", f"blocked: {result.message}")
            return self._finish(result)
        request = result.request = guard.text
        log("guard_input", "passed")

        # 2. Retrieve
        retrieved = self.kb.retrieve(strip_negations(request), k=4)
        result.sources = [r.doc.title for r in retrieved]
        log("retrieve", ", ".join(f"{r.doc.title} ({r.score:.2f})" for r in retrieved) or "no documents matched")
        if not retrieved and not mentions_catalog_term(request, self.songs):
            result.status = "needs_clarification"
            result.message = ("I couldn't connect that request to any genre, mood or activity I know. "
                              "Try naming a genre (e.g. jazz), a mood (e.g. happy) or an activity "
                              "(e.g. studying, workout).")
            log("retrieve", "nothing relevant: asking for clarification")
            return self._finish(result)

        # 3. Plan
        prefs, excluded = None, []
        if self.use_llm:
            planned = llm_plan_profile(request, retrieved, self.songs)
            if planned:
                prefs, excluded, result.planner = planned["prefs"], planned["excluded_genres"], "claude"
                log("plan", f"Claude planner: {planned['rationale']}")
        if prefs is None:
            prefs, excluded = rule_based_plan(request, retrieved, self.songs)
            result.planner = "rules"
            log("plan", f"rule-based planner from {len(retrieved)} retrieved docs")
        result.excluded_genres = excluded
        candidates = [s for s in self.songs if s["genre"] not in excluded]
        if excluded:
            log("plan", f"excluding genres the request ruled out: {', '.join(excluded)}")

        # 4. Validate the profile
        prefs, warnings = sanitize_profile(prefs, self.songs)
        if prefs["favorite_genre"] in excluded:
            warnings.append(f"Planner picked excluded genre '{prefs['favorite_genre']}'; cleared it.")
            prefs["favorite_genre"] = ""
        result.warnings += warnings
        log("validate", "; ".join(warnings) or "profile is valid")
        if not (prefs["favorite_genre"] or prefs["favorite_mood"] or prefs.get("mood_tags")):
            # e.g. "not happy music": only negations, so ranking would just be by energy noise
            result.status = "needs_clarification"
            result.message = ("I can tell what you don't want, but not what you do. Name a genre "
                              "(e.g. jazz), a mood (e.g. relaxed) or an activity (e.g. studying).")
            log("validate", "profile has no genre, mood or tags: asking for clarification")
            return self._finish(result)

        # 5-6. Recommend, critique, revise (bounded)
        for attempt in range(self.max_revisions + 1):
            recs = recommend_songs(prefs, candidates, min(k, len(candidates)), mode, diversity)
            confidence = self._confidence(prefs, recs, mode)
            log("recommend", f"attempt {attempt + 1}: top = "
                + ", ".join(f"{s['title']} ({sc:.2f})" for s, sc, _ in recs[:3])
                + f"; confidence {confidence:.2f}")
            revision = self._critique(prefs, recs, retrieved, diversity) if attempt < self.max_revisions else None
            if not revision:
                log("self_check", "no fixable issues found")
                break
            reason, prefs, diversity = revision
            log("self_check", f"revising: {reason}")
            result.warnings.append(f"Agent revision: {reason}")

        result.profile, result.recommendations, result.confidence = prefs, recs, confidence
        result.diversity = diversity
        result.warnings += self._advisories(prefs, confidence)

        # 7. Output guardrail
        problems = validate_recommendations(recs, self.songs, k)
        problems += [f"'{s['title']}' is {s['genre']}, which the request excluded"
                     for s, _, _ in recs if s["genre"] in excluded]
        if problems:
            result.status = "error"
            result.message = "Output failed validation: " + "; ".join(problems)
            log("guard_output", result.message)
        else:
            log("guard_output", "passed")
            result.message = self._summary(prefs, result.sources)
        return self._finish(result)

    # -- helpers -------------------------------------------------------------

    def _confidence(self, prefs: Dict, recs: List[Tuple], mode: ScoringMode) -> float:
        """Top score as a fraction of the best score possible for this profile (0-1)."""
        if not recs:
            return 0.0
        best = max_possible_score(prefs, mode)
        return round(min(recs[0][1] / best, 1.0), 3) if best > 0 else 0.0

    def _critique(self, prefs, recs, retrieved, diversity):
        """Return (reason, new_prefs, new_diversity) for a fixable problem, else None."""
        genre = prefs.get("favorite_genre")
        if genre and genre not in self.genres:
            for r in retrieved:
                for related in r.doc.hints.get("related_genres", []):
                    if related in self.genres:
                        return (f"genre '{genre}' is not in the catalog; using related genre "
                                f"'{related}' from '{r.doc.title}'", dict(prefs, favorite_genre=related), diversity)
            return (f"genre '{genre}' is not in the catalog and has no known substitute; "
                    "dropping it", dict(prefs, favorite_genre=""), diversity)

        artists = Counter(song["artist"] for song, _, _ in recs)
        repeated = [a for a, n in artists.items() if n > 1]
        if repeated and not diversity:
            return (f"artist {', '.join(repeated)} appears more than once; "
                    "turning on the diversity penalty", prefs, True)
        return None

    def _advisories(self, prefs: Dict, confidence: float) -> List[str]:
        """Non-fixable caveats the user should know about."""
        notes = []
        if confidence < LOW_CONFIDENCE:
            notes.append(f"Low confidence ({confidence:.0%}): the catalog has no close match "
                         "for every part of this request.")
        genre_energy = [s["energy"] for s in self.songs if s["genre"] == prefs.get("favorite_genre")]
        if genre_energy:
            typical = sum(genre_energy) / len(genre_energy)
            if abs(typical - prefs["target_energy"]) > ENERGY_CONFLICT_GAP:
                notes.append(f"Energy {prefs['target_energy']:.2f} conflicts with {prefs['favorite_genre']} "
                             f"songs (typically {typical:.2f}); results trade off one against the other.")
        return notes

    @staticmethod
    def _summary(prefs: Dict, sources: List[str]) -> str:
        parts = [f"genre {prefs['favorite_genre'] or 'any'}", f"mood {prefs['favorite_mood'] or 'any'}",
                 f"energy {prefs['target_energy']:.2f}"]
        if prefs.get("likes_acoustic"):
            parts.append("acoustic")
        if prefs.get("mood_tags"):
            parts.append("tags " + "/".join(prefs["mood_tags"]))
        if prefs.get("wants_instrumental"):
            parts.append("instrumental")
        text = "I read this as: " + ", ".join(parts) + "."
        if sources:
            text += " Grounded in: " + "; ".join(sources) + "."
        return text

    @staticmethod
    def _trace(result: AgentResult, step: str, detail: str) -> None:
        result.trace.append(TraceStep(step, detail))
        logger.debug("[%s] %s: %s", result.run_id, step, detail)

    @staticmethod
    def _finish(result: AgentResult) -> AgentResult:
        log_event(logger, "agent_run", run_id=result.run_id, request=result.request,
                  status=result.status, planner=result.planner, profile=result.profile,
                  confidence=result.confidence, diversity=result.diversity,
                  excluded_genres=result.excluded_genres,
                  top=[s["title"] for s, _, _ in result.recommendations],
                  warnings=result.warnings, sources=result.sources)
        return result

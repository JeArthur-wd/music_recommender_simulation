import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict, field

# Algorithm Recipe weights (see README "How The System Works")
GENRE_WEIGHT = 2.0
MOOD_WEIGHT = 1.0
ENERGY_WEIGHT = 1.5
ACOUSTIC_BONUS = 0.5
ACOUSTIC_THRESHOLD = 0.6

# Advanced features: only scored when the user profile asks for them
DECADE_BONUS = 1.0          # exact decade match
NEAR_DECADE_BONUS = 0.5     # one decade away
MOOD_TAG_BONUS = 0.5        # per matching tag
MAX_MOOD_TAGS = 2           # cap so tags can't outweigh genre
POPULARITY_WEIGHT = 0.5
INSTRUMENTAL_BONUS = 0.5
INSTRUMENTAL_THRESHOLD = 0.7
SPEECH_BONUS = 0.5
SPEECH_THRESHOLD = 0.33     # rap / spoken word

# Diversity penalties: applied per song of the same artist/genre already picked
ARTIST_PENALTY = 1.5
GENRE_PENALTY = 0.5

INT_FIELDS = {"id", "popularity", "release_decade"}
FLOAT_FIELDS = {
    "energy", "tempo_bpm", "valence", "danceability", "acousticness",
    "instrumentalness", "speechiness",
}
LIST_FIELDS = {"mood_tags"}

@dataclass(frozen=True)
class ScoringMode:
    """A ranking strategy: the weights score_song uses for the core features."""
    name: str
    genre_weight: float
    mood_weight: float
    energy_weight: float
    acoustic_bonus: float = ACOUSTIC_BONUS

GENRE_FIRST = ScoringMode("Genre-First", GENRE_WEIGHT, MOOD_WEIGHT, ENERGY_WEIGHT)
MOOD_FIRST = ScoringMode("Mood-First", 1.0, 2.0, ENERGY_WEIGHT)
ENERGY_FOCUSED = ScoringMode("Energy-Focused", 1.0, 0.5, 3.0)

MODES = {
    "genre-first": GENRE_FIRST,
    "mood-first": MOOD_FIRST,
    "energy-focused": ENERGY_FOCUSED,
}

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    popularity: int = 50
    release_decade: int = 0
    mood_tags: List[str] = field(default_factory=list)
    instrumentalness: float = 0.0
    speechiness: float = 0.0

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(
        self, user: UserProfile, k: int = 5,
        mode: ScoringMode = GENRE_FIRST, diversity: bool = False,
    ) -> List[Song]:
        """Return the top k songs for the user, highest score first."""
        # UserProfile/Song field names match the dict keys score_song expects
        by_id = {song.id: song for song in self.songs}
        ranked = recommend_songs(
            asdict(user), [asdict(song) for song in self.songs], k, mode, diversity
        )
        return [by_id[song["id"]] for song, _, _ in ranked]

    def explain_recommendation(
        self, user: UserProfile, song: Song, mode: ScoringMode = GENRE_FIRST
    ) -> str:
        """Return a readable summary of the song's score and the reasons behind it."""
        score, reasons = score_song(asdict(user), asdict(song), mode)
        if not reasons:
            return f"Score {score:.2f}: no preferences matched"
        return f"Score {score:.2f}: " + "; ".join(reasons)

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file into dicts, converting numeric columns to int/float.
    Required by src/main.py
    """
    print(f"Loading songs from {csv_path}...")
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Convert numeric columns so they can be used in math later
            for name in INT_FIELDS & row.keys():
                row[name] = int(row[name])
            for name in FLOAT_FIELDS & row.keys():
                row[name] = float(row[name])
            # Multi-value columns are stored as "tag1;tag2;tag3"
            for name in LIST_FIELDS & row.keys():
                row[name] = [tag.strip().lower() for tag in row[name].split(";") if tag.strip()]
            songs.append(row)
    return songs

def score_song(
    user_prefs: Dict, song: Dict, mode: ScoringMode = GENRE_FIRST
) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py

    Returns (score, reasons), where reasons lists each rule that awarded points.
    """
    score = 0.0
    reasons = []

    if song["genre"].lower() == user_prefs.get("favorite_genre", "").lower():
        score += mode.genre_weight
        reasons.append(f"genre match: {song['genre']} (+{mode.genre_weight:.1f})")

    if song["mood"].lower() == user_prefs.get("favorite_mood", "").lower():
        score += mode.mood_weight
        reasons.append(f"mood match: {song['mood']} (+{mode.mood_weight:.1f})")

    # Reward closeness to the target energy, not just higher or lower energy
    if "target_energy" in user_prefs:
        target = user_prefs["target_energy"]
        energy_points = mode.energy_weight * (1 - abs(target - song["energy"]))
        score += energy_points
        reasons.append(
            f"energy {song['energy']:.2f} vs target {target:.2f} (+{energy_points:.2f})"
        )

    if user_prefs.get("likes_acoustic") and song["acousticness"] > ACOUSTIC_THRESHOLD:
        score += mode.acoustic_bonus
        reasons.append(f"acoustic sound: {song['acousticness']:.2f} (+{mode.acoustic_bonus:.1f})")

    advanced_points, advanced_reasons = score_advanced_features(user_prefs, song)
    return score + advanced_points, reasons + advanced_reasons

def score_advanced_features(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score the optional features (decade, mood tags, popularity, instrumental, speech)."""
    score = 0.0
    reasons = []

    decade = user_prefs.get("preferred_decade")
    if decade and song.get("release_decade"):
        gap = abs(decade - song["release_decade"])
        if gap == 0:
            score += DECADE_BONUS
            reasons.append(f"from the {decade}s (+{DECADE_BONUS:.1f})")
        elif gap == 10:
            score += NEAR_DECADE_BONUS
            reasons.append(f"close decade: {song['release_decade']}s (+{NEAR_DECADE_BONUS:.1f})")

    wanted_tags = {tag.lower() for tag in user_prefs.get("mood_tags", [])}
    matched = sorted(wanted_tags & set(song.get("mood_tags", [])))[:MAX_MOOD_TAGS]
    if matched:
        tag_points = MOOD_TAG_BONUS * len(matched)
        score += tag_points
        reasons.append(f"mood tags: {', '.join(matched)} (+{tag_points:.1f})")

    # True = mainstream fan, False = underground fan, missing = don't care
    prefers_popular = user_prefs.get("prefers_popular")
    if prefers_popular is not None and "popularity" in song:
        share = song["popularity"] / 100
        if not prefers_popular:
            share = 1 - share
        pop_points = POPULARITY_WEIGHT * share
        score += pop_points
        label = "popular" if prefers_popular else "underground"
        reasons.append(f"{label} pick: popularity {song['popularity']} (+{pop_points:.2f})")

    if user_prefs.get("wants_instrumental") and song.get("instrumentalness", 0) >= INSTRUMENTAL_THRESHOLD:
        score += INSTRUMENTAL_BONUS
        reasons.append(f"instrumental: {song['instrumentalness']:.2f} (+{INSTRUMENTAL_BONUS:.1f})")

    if user_prefs.get("likes_rap") and song.get("speechiness", 0) >= SPEECH_THRESHOLD:
        score += SPEECH_BONUS
        reasons.append(f"rap/spoken vocals: {song['speechiness']:.2f} (+{SPEECH_BONUS:.1f})")

    return score, reasons

def recommend_songs(
    user_prefs: Dict, songs: List[Dict], k: int = 5,
    mode: ScoringMode = GENRE_FIRST, diversity: bool = False,
) -> List[Tuple[Dict, float, str]]:
    """
    Scores every song and returns the top k as (song, score, explanation), highest first.
    Required by src/main.py
    """
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, mode)
        scored.append((song, score, reasons))

    if diversity:
        ranked = rerank_with_diversity(scored, k)
    else:
        # sorted() returns a new list and leaves the caller's songs untouched.
        # Highest score first; ties broken by id so the order is stable.
        ranked = sorted(scored, key=lambda item: (-item[1], item[0]["id"]))[:k]
    return [(song, score, "; ".join(reasons)) for song, score, reasons in ranked]

def rerank_with_diversity(
    scored: List[Tuple[Dict, float, List[str]]], k: int
) -> List[Tuple[Dict, float, List[str]]]:
    """Greedily pick k songs, penalizing artists and genres already in the picks."""
    remaining = list(scored)
    picks = []
    while remaining and len(picks) < k:
        best = None
        for song, score, reasons in remaining:
            same_artist = sum(p["artist"] == song["artist"] for p, _, _ in picks)
            same_genre = sum(p["genre"] == song["genre"] for p, _, _ in picks)
            penalty = ARTIST_PENALTY * same_artist + GENRE_PENALTY * same_genre
            candidate = (song, score - penalty, reasons, same_artist, same_genre, penalty)
            if best is None or (candidate[1], -song["id"]) > (best[1], -best[0]["id"]):
                best = candidate
        song, adjusted, reasons, same_artist, same_genre, penalty = best
        remaining = [item for item in remaining if item[0] is not song]
        if penalty:
            repeats = []
            if same_artist:
                repeats.append(f"artist {song['artist']} x{same_artist}")
            if same_genre:
                repeats.append(f"genre {song['genre']} x{same_genre}")
            reasons = reasons + [f"diversity penalty: {', '.join(repeats)} already listed (-{penalty:.1f})"]
        picks.append((song, adjusted, reasons))
    return picks

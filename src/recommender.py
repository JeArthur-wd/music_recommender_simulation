import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

# Algorithm Recipe weights (see README "How The System Works")
GENRE_WEIGHT = 2.0
MOOD_WEIGHT = 1.0
ENERGY_WEIGHT = 1.5
ACOUSTIC_BONUS = 0.5
ACOUSTIC_THRESHOLD = 0.6

INT_FIELDS = {"id"}
FLOAT_FIELDS = {"energy", "tempo_bpm", "valence", "danceability", "acousticness"}

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

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k songs for the user, highest score first."""
        # UserProfile/Song field names match the dict keys score_song expects
        prefs = asdict(user)
        return sorted(
            self.songs,
            key=lambda song: (-score_song(prefs, asdict(song))[0], song.id),
        )[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a readable summary of the song's score and the reasons behind it."""
        score, reasons = score_song(asdict(user), asdict(song))
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
            for field in INT_FIELDS:
                row[field] = int(row[field])
            for field in FLOAT_FIELDS:
                row[field] = float(row[field])
            songs.append(row)
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py

    Returns (score, reasons), where reasons lists each rule that awarded points.
    """
    score = 0.0
    reasons = []

    if song["genre"].lower() == user_prefs.get("favorite_genre", "").lower():
        score += GENRE_WEIGHT
        reasons.append(f"genre match: {song['genre']} (+{GENRE_WEIGHT:.1f})")

    if song["mood"].lower() == user_prefs.get("favorite_mood", "").lower():
        score += MOOD_WEIGHT
        reasons.append(f"mood match: {song['mood']} (+{MOOD_WEIGHT:.1f})")

    # Reward closeness to the target energy, not just higher or lower energy
    if "target_energy" in user_prefs:
        target = user_prefs["target_energy"]
        energy_points = ENERGY_WEIGHT * (1 - abs(target - song["energy"]))
        score += energy_points
        reasons.append(
            f"energy {song['energy']:.2f} vs target {target:.2f} (+{energy_points:.2f})"
        )

    if user_prefs.get("likes_acoustic") and song["acousticness"] > ACOUSTIC_THRESHOLD:
        score += ACOUSTIC_BONUS
        reasons.append(f"acoustic sound: {song['acousticness']:.2f} (+{ACOUSTIC_BONUS:.1f})")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Scores every song and returns the top k as (song, score, explanation), highest first.
    Required by src/main.py
    """
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        scored.append((song, score, "; ".join(reasons)))

    # sorted() returns a new list and leaves the caller's songs untouched.
    # Highest score first; ties broken by id so the order is stable.
    ranked = sorted(scored, key=lambda item: (-item[1], item[0]["id"]))
    return ranked[:k]

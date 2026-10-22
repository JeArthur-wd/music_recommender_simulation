"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

try:
    from .recommender import load_songs, recommend_songs  # python -m src.main
except ImportError:
    from recommender import load_songs, recommend_songs  # python src/main.py


PROFILES = {
    # Default profile: an upbeat pop listener
    "High-Energy Pop": {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.8,
        "likes_acoustic": False,
    },
    # A lofi listener who wants calm, acoustic study music
    "Chill Lofi": {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.4,
        "likes_acoustic": True,
    },
    "Deep Intense Rock": {
        "favorite_genre": "rock",
        "favorite_mood": "intense",
        "target_energy": 0.9,
        "likes_acoustic": False,
    },
    # --- Adversarial / edge-case profiles ---
    # Conflicting preferences: sad songs in this catalog are all low energy
    "Sad but Hyped": {
        "favorite_genre": "blues",
        "favorite_mood": "sad",
        "target_energy": 0.9,
        "likes_acoustic": False,
    },
    # Genre and mood that don't exist in the catalog
    "Ghost Genre": {
        "favorite_genre": "indie",
        "favorite_mood": "dreamy",
        "target_energy": 0.5,
        "likes_acoustic": False,
    },
    # Wants acoustic sound from the least acoustic genre
    "Acoustic Headbanger": {
        "favorite_genre": "metal",
        "favorite_mood": "angry",
        "target_energy": 0.95,
        "likes_acoustic": True,
    },
    # Messy input: capitalization and stray spaces
    "Messy Input": {
        "favorite_genre": " Pop ",
        "favorite_mood": "HAPPY",
        "target_energy": 0.8,
        "likes_acoustic": False,
    },
    # Out-of-range energy target (scale is 0.0-1.0)
    "Energy Overload": {
        "favorite_genre": "edm",
        "favorite_mood": "energetic",
        "target_energy": 1.8,
        "likes_acoustic": False,
    },
}


def print_recommendations(name: str, user_prefs: dict, recommendations: list) -> None:
    """Print a profile header followed by each ranked song, its score, and its reasons."""
    prefs = ", ".join(f"{key}={value}" for key, value in user_prefs.items())
    print("=" * 60)
    print(f"Profile: {name}")
    print(f"  {prefs}")
    print("=" * 60)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"{rank}. {song['title']} by {song['artist']}")
        print(f"   Score: {score:.2f}  ({song['genre']} / {song['mood']})")
        for reason in explanation.split("; "):
            print(f"     - {reason}")
        print()


def main() -> None:
    """Load the catalog and print the top 5 recommendations for each profile."""
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}\n")

    for name, user_prefs in PROFILES.items():
        recommendations = recommend_songs(user_prefs, songs, k=5)
        print_recommendations(name, user_prefs, recommendations)


if __name__ == "__main__":
    main()

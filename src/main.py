"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import argparse
import textwrap

try:
    from .recommender import MODES, load_songs, recommend_songs  # python -m src.main
except ImportError:
    from recommender import MODES, load_songs, recommend_songs  # python src/main.py

REASON_WIDTH = 52


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
    # --- Profiles using the advanced features ---
    "Nostalgic Night Owl": {
        "favorite_genre": "synthwave",
        "favorite_mood": "moody",
        "target_energy": 0.6,
        "likes_acoustic": False,
        "preferred_decade": 2010,
        "mood_tags": ["nostalgic", "nocturnal"],
        "prefers_popular": False,
        "wants_instrumental": True,
    },
    "Hip-Hop Head": {
        "favorite_genre": "hip-hop",
        "favorite_mood": "confident",
        "target_energy": 0.8,
        "likes_acoustic": False,
        "preferred_decade": 2020,
        "mood_tags": ["swagger", "aggressive"],
        "prefers_popular": True,
        "likes_rap": True,
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


def format_table(headers: list, rows: list) -> str:
    """Render rows as an ASCII table; a cell may be a list of lines."""
    rows = [[cell if isinstance(cell, list) else [str(cell)] for cell in row] for row in rows]
    widths = [
        max([len(header)] + [len(line) for row in rows for line in row[i]])
        for i, header in enumerate(headers)
    ]
    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def render(cells: list) -> list:
        height = max(len(cell) for cell in cells)
        return [
            "| " + " | ".join(
                (cell[i] if i < len(cell) else "").ljust(w) for cell, w in zip(cells, widths)
            ) + " |"
            for i in range(height)
        ]

    lines = [border, *render([[h] for h in headers]), border]
    for row in rows:
        lines += render(row) + [border]
    return "\n".join(lines)


def print_table(name: str, user_prefs: dict, recommendations: list) -> None:
    """Print one profile's recommendations as a table with a reasons column."""
    prefs = ", ".join(f"{key}={value}" for key, value in user_prefs.items())
    print(f"Profile: {name}")
    print(textwrap.fill(prefs, width=100, initial_indent="  ", subsequent_indent="  "))
    rows = []
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        reasons = []
        for reason in explanation.split("; "):
            reasons += textwrap.wrap(reason, REASON_WIDTH, initial_indent="- ", subsequent_indent="  ")
        rows.append([rank, song["title"], f"{song['genre']} / {song['mood']}", f"{score:.2f}", reasons])
    print(format_table(["#", "Title", "Genre / Mood", "Score", "Reasons"], rows))
    print()


def parse_args() -> argparse.Namespace:
    """Read the scoring mode, diversity flag, profile filter, and output format."""
    parser = argparse.ArgumentParser(description="Music Recommender Simulation")
    parser.add_argument("--mode", choices=MODES, default="genre-first",
                        help="ranking strategy (default: genre-first)")
    parser.add_argument("--diverse", action="store_true",
                        help="penalize repeated artists and genres in the top results")
    parser.add_argument("--profile", choices=PROFILES, metavar="NAME",
                        help="run a single profile (default: all)")
    parser.add_argument("--format", choices=["table", "detailed"], default="table",
                        help="output layout (default: table)")
    parser.add_argument("-k", type=int, default=5, help="number of recommendations")
    return parser.parse_args()


def main() -> None:
    """Load the catalog and print the top k recommendations for each profile."""
    args = parse_args()
    mode = MODES[args.mode]
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")
    print(f"Mode: {mode.name}  |  Diversity: {'on' if args.diverse else 'off'}\n")

    show = print_table if args.format == "table" else print_recommendations
    profiles = {args.profile: PROFILES[args.profile]} if args.profile else PROFILES
    for name, user_prefs in profiles.items():
        recommendations = recommend_songs(user_prefs, songs, args.k, mode, args.diverse)
        show(name, user_prefs, recommendations)


if __name__ == "__main__":
    main()

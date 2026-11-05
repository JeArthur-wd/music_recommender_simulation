"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import argparse
import sys
import textwrap

try:
    from .guardrails import sanitize_profile  # python -m src.main
    from .logging_config import get_logger
    from .recommender import MODES, load_songs, recommend_songs
except ImportError:
    from guardrails import sanitize_profile  # python src/main.py
    from logging_config import get_logger
    from recommender import MODES, load_songs, recommend_songs

logger = get_logger("cli")

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
    parser.add_argument("--ask", metavar="TEXT",
                        help='agent mode: describe what you want, e.g. --ask "calm music for studying"')
    parser.add_argument("--trace", action="store_true",
                        help="with --ask, print each step the agent took")
    parser.add_argument("--no-llm", action="store_true",
                        help="with --ask, use the offline rule-based planner even if Claude is available")
    parser.add_argument("--no-guardrails", action="store_true",
                        help="score preset profiles exactly as written (reproduces the original bugs)")
    args = parser.parse_args()
    if args.k < 1:
        parser.error("-k must be at least 1")
    return args


def run_agent(args: argparse.Namespace, songs: list, mode) -> None:
    """Agent mode: free-text request -> RAG + planning + self-check -> recommendations."""
    try:
        from .agent import RecommenderAgent
    except ImportError:
        from agent import RecommenderAgent

    agent = RecommenderAgent(songs, use_llm=False if args.no_llm else None)
    result = agent.run(args.ask, k=args.k, mode=mode, diversity=args.diverse)
    print(f'Request: "{result.request}"')
    print(f"Status: {result.status}  |  Planner: {result.planner or '-'}  |  "
          f"Confidence: {result.confidence:.0%}  |  Run id: {result.run_id}")
    print()

    if args.trace:
        print("Agent trace:")
        for i, step in enumerate(result.trace, start=1):
            print(textwrap.fill(f"{i}. [{step.step}] {step.detail}", width=100, subsequent_indent="     "))
        print()

    if result.status != "ok":
        print(result.message)
        return
    print(textwrap.fill(result.message, width=100))
    for warning in result.warnings:
        print(textwrap.fill(f"! {warning}", width=100, subsequent_indent="  "))
    print()
    show = print_table if args.format == "table" else print_recommendations
    show("Agent", result.profile, result.recommendations)


def main() -> None:
    """Load the catalog and print the top k recommendations for each profile."""
    # Windows consoles (cp1252) can't print emoji echoed back from a request; replace, don't crash
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = parse_args()
    mode = MODES[args.mode]
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")
    print(f"Mode: {mode.name}  |  Diversity: {'on' if args.diverse else 'off'}\n")

    if args.ask is not None:
        run_agent(args, songs, mode)
        return

    show = print_table if args.format == "table" else print_recommendations
    profiles = {args.profile: PROFILES[args.profile]} if args.profile else PROFILES
    for name, user_prefs in profiles.items():
        if not args.no_guardrails:
            user_prefs, warnings = sanitize_profile(user_prefs, songs)
            for warning in warnings:
                print(f"! guardrail ({name}): {warning}")
        recommendations = recommend_songs(user_prefs, songs, args.k, mode, args.diverse)
        logger.info("profile=%s mode=%s top=%s", name, mode.name,
                    [song["title"] for song, _, _ in recommendations])
        show(name, user_prefs, recommendations)


if __name__ == "__main__":
    main()

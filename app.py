"""
Streamlit web UI for the Music Recommender Simulation.

Run with:  streamlit run app.py
"""

import pandas as pd
import streamlit as st

from src.main import PROFILES
from src.recommender import MODES, load_songs, recommend_songs

CUSTOM = "Custom"
POPULARITY_CHOICES = {"Don't care": None, "Mainstream": True, "Underground": False}

st.set_page_config(page_title="TuneJudge", page_icon="🎧", layout="wide")


@st.cache_data
def get_songs() -> list:
    """Load the catalog once and reuse it across reruns."""
    return load_songs("data/songs.csv")


def with_option(options: list, value: str) -> list:
    """Make sure a preset's value appears in a dropdown, even if the catalog lacks it."""
    return options if value in options else options + [value]


def sidebar_profile(songs: list) -> dict:
    """Build the user's preference dict from the sidebar widgets."""
    st.sidebar.header("Listener profile")
    preset_name = st.sidebar.selectbox("Start from a preset", [CUSTOM, *PROFILES])
    preset = PROFILES.get(preset_name, {})
    key = preset_name  # widget keys per preset, so switching presets resets the widgets

    genres = sorted({song["genre"] for song in songs})
    moods = sorted({song["mood"] for song in songs})
    genre = preset.get("favorite_genre", genres[0])
    mood = preset.get("favorite_mood", moods[0])
    energy = preset.get("target_energy", 0.5)

    prefs = {
        "favorite_genre": st.sidebar.selectbox(
            "Favorite genre", with_option(genres, genre),
            index=with_option(genres, genre).index(genre), key=f"genre_{key}"),
        "favorite_mood": st.sidebar.selectbox(
            "Favorite mood", with_option(moods, mood),
            index=with_option(moods, mood).index(mood), key=f"mood_{key}"),
        "target_energy": st.sidebar.slider(
            "Target energy (0 = calm, 1 = intense)", 0.0, 1.0,
            min(max(energy, 0.0), 1.0), 0.01, key=f"energy_{key}"),
        "likes_acoustic": st.sidebar.checkbox(
            "Likes acoustic music", preset.get("likes_acoustic", False), key=f"acoustic_{key}"),
    }
    if not 0.0 <= energy <= 1.0:
        st.sidebar.caption(f"Preset energy {energy} is outside 0–1, so the slider clamps it.")

    with st.sidebar.expander("Advanced preferences", expanded=bool(set(preset) - set(prefs))):
        decades = sorted({song["release_decade"] for song in songs})
        decade_labels = ["Any"] + [f"{d}s" for d in decades]
        preset_decade = preset.get("preferred_decade")
        decade = st.selectbox(
            "Preferred decade", decade_labels,
            index=decade_labels.index(f"{preset_decade}s") if preset_decade in decades else 0,
            key=f"decade_{key}")
        if decade != "Any":
            prefs["preferred_decade"] = int(decade[:-1])

        all_tags = sorted({tag for song in songs for tag in song["mood_tags"]})
        tags = st.multiselect(
            "Mood tags", all_tags,
            [t for t in preset.get("mood_tags", []) if t in all_tags], key=f"tags_{key}")
        if tags:
            prefs["mood_tags"] = tags

        popularity_labels = list(POPULARITY_CHOICES)
        preset_popular = preset.get("prefers_popular")
        popularity = st.radio(
            "Popularity", popularity_labels,
            index=list(POPULARITY_CHOICES.values()).index(preset_popular),
            horizontal=True, key=f"popular_{key}")
        if POPULARITY_CHOICES[popularity] is not None:
            prefs["prefers_popular"] = POPULARITY_CHOICES[popularity]

        if st.checkbox("Wants instrumental", preset.get("wants_instrumental", False),
                       key=f"instrumental_{key}"):
            prefs["wants_instrumental"] = True
        if st.checkbox("Likes rap / spoken vocals", preset.get("likes_rap", False),
                       key=f"rap_{key}"):
            prefs["likes_rap"] = True

    return prefs


def sidebar_ranking() -> tuple:
    """Read the scoring mode, diversity toggle, and number of results."""
    st.sidebar.header("Ranking")
    mode_key = st.sidebar.radio(
        "Scoring mode", list(MODES), format_func=lambda m: MODES[m].name, key="mode")
    mode = MODES[mode_key]
    st.sidebar.caption(
        f"Genre +{mode.genre_weight:g} · Mood +{mode.mood_weight:g} · "
        f"Energy up to +{mode.energy_weight:g} · Acoustic +{mode.acoustic_bonus:g}")
    diversity = st.sidebar.toggle(
        "Diversity penalty", key="diversity", help="−1.5 per repeated artist, −0.5 per repeated genre")
    k = st.sidebar.slider("Number of recommendations", 1, 10, 5)
    return mode, diversity, k


def main() -> None:
    """Render the recommender page."""
    songs = get_songs()
    prefs = sidebar_profile(songs)
    mode, diversity, k = sidebar_ranking()

    st.title("🎧 TuneJudge")
    st.write(
        "A content-based recommender that scores every song against your taste, "
        "ranks them, and shows exactly where each point came from."
    )

    results = recommend_songs(prefs, songs, k, mode, diversity)
    tab_results, tab_catalog = st.tabs(["Recommendations", f"Catalog ({len(songs)} songs)"])

    with tab_results:
        st.caption(
            f"Mode: **{mode.name}** · Diversity: **{'on' if diversity else 'off'}** · "
            f"Genre **{prefs['favorite_genre']}**, mood **{prefs['favorite_mood']}**, "
            f"energy **{prefs['target_energy']:.2f}**"
        )
        table = pd.DataFrame([
            {
                "#": rank,
                "Title": song["title"],
                "Artist": song["artist"],
                "Genre": song["genre"],
                "Mood": song["mood"],
                "Score": round(score, 2),
                "Reasons": explanation,
            }
            for rank, (song, score, explanation) in enumerate(results, start=1)
        ])
        st.dataframe(table, hide_index=True, width="stretch")

        st.subheader("Why these songs?")
        for rank, (song, score, explanation) in enumerate(results, start=1):
            with st.expander(f"{rank}. {song['title']} — {song['artist']}  ·  {score:.2f} pts",
                             expanded=rank == 1):
                for reason in explanation.split("; "):
                    st.markdown(f"- {reason}")

    with tab_catalog:
        catalog = pd.DataFrame(songs)
        catalog["mood_tags"] = catalog["mood_tags"].apply(", ".join)
        st.dataframe(catalog, hide_index=True, width="stretch")


main()

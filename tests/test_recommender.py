from src.recommender import Song, UserProfile, Recommender

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


from src.recommender import (
    GENRE_FIRST, MOOD_FIRST, load_songs, recommend_songs, score_song,
)


def make_song(id, artist, genre, mood, energy, **extra):
    song = {
        "id": id, "title": f"Song {id}", "artist": artist, "genre": genre, "mood": mood,
        "energy": energy, "tempo_bpm": 100, "valence": 0.5, "danceability": 0.5,
        "acousticness": 0.2,
    }
    song.update(extra)
    return song


def test_load_songs_parses_advanced_columns():
    songs = load_songs("data/songs.csv")
    first = songs[0]
    assert isinstance(first["popularity"], int)
    assert isinstance(first["release_decade"], int)
    assert isinstance(first["instrumentalness"], float)
    assert isinstance(first["speechiness"], float)
    assert first["mood_tags"] == ["happy", "sunny", "uplifting"]


def test_scoring_modes_change_genre_vs_mood_priority():
    prefs = {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.8}
    songs = [
        make_song(1, "A", "pop", "intense", 0.8),   # genre match only
        make_song(2, "B", "indie", "happy", 0.8),   # mood match only
    ]
    assert recommend_songs(prefs, songs, 2, GENRE_FIRST)[0][0]["id"] == 1
    assert recommend_songs(prefs, songs, 2, MOOD_FIRST)[0][0]["id"] == 2


def test_diversity_penalty_breaks_up_repeated_artist():
    prefs = {"favorite_genre": "lofi", "favorite_mood": "chill", "target_energy": 0.4}
    songs = [
        make_song(1, "LoRoom", "lofi", "chill", 0.4),
        make_song(2, "LoRoom", "lofi", "chill", 0.4),
        make_song(3, "Other", "lofi", "chill", 0.39),  # slightly worse, new artist
    ]
    plain = [song["id"] for song, _, _ in recommend_songs(prefs, songs, 2)]
    diverse = recommend_songs(prefs, songs, 2, diversity=True)
    assert plain == [1, 2]
    assert [song["id"] for song, _, _ in diverse] == [1, 3]


def test_advanced_features_only_scored_when_requested():
    song = make_song(1, "A", "pop", "happy", 0.8, popularity=80, release_decade=2010,
                     mood_tags=["nostalgic"], instrumentalness=0.9, speechiness=0.4)
    base_prefs = {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.8}
    base_score, _ = score_song(base_prefs, song)

    rich_prefs = dict(base_prefs, preferred_decade=2010, mood_tags=["nostalgic"],
                      prefers_popular=True, wants_instrumental=True, likes_rap=True)
    rich_score, reasons = score_song(rich_prefs, song)

    # decade 1.0 + tag 0.5 + popularity 0.5 * 0.8 + instrumental 0.5 + rap 0.5
    assert abs(rich_score - base_score - 2.9) < 1e-9
    assert len(reasons) == 8

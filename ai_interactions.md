# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agentic Workflow (SF8)

**What task did you give the agent?**

I asked Claude Code (in agent mode) to complete all four optional challenges in one multi-step run, on a separate branch (`experiment/advanced-scoring`) so the working version on `main` stayed safe:

1. Add 5+ advanced song attributes to `data/songs.csv` and score them.
2. Add switchable scoring modes using a modular design pattern.
3. Add a diversity penalty for repeated artists and genres.
4. Show the results as a readable terminal table that includes the reasons.

**Prompts used:**

- *Challenge 1:* "Add five new attributes to `data/songs.csv` that aren't in the baseline data: popularity (0–100), release decade, detailed mood tags (e.g. nostalgic, aggressive, euphoric), instrumentalness and speechiness. Update `load_songs` to parse them (ints, floats, and a list for the tags), and update the scoring in `src/recommender.py` so each one can earn points. Existing profiles that don't ask for the new features must get exactly the same results as before."
- *Challenge 2:* "Brainstorm a design pattern, like a simple Strategy pattern, that lets me switch between Genre-First, Mood-First and Energy-Focused ranking modes from `main.py` without duplicating the scoring code."
- *Challenge 3:* "Add a diversity rule to the ranking: if a song's artist is already in the top recommendations list, subtract a penalty from its score before choosing the next song. Do the same, more gently, for a repeated genre. Show the penalty in the song's reasons so the user can see why it moved."
- *Challenge 4:* "Suggest a way to show the top recommendations as a table in the terminal, using a library like `tabulate` or plain ASCII formatting. The table must include the reasons for each score, not just the title and number."

**What did the agent generate or change?**

| File | Change |
|---|---|
| `data/songs.csv` | 5 new columns for all 20 songs: `popularity`, `release_decade`, `mood_tags` (stored as `tag1;tag2;tag3`), `instrumentalness`, `speechiness`. |
| `src/recommender.py` | `ScoringMode` strategy objects and a `MODES` registry; new optional `Song` fields with defaults; `load_songs` parses the new columns; new `score_advanced_features()`; new `rerank_with_diversity()`; `recommend_songs` and `Recommender` accept `mode` and `diversity`. |
| `src/main.py` | Command-line options `--mode`, `--diverse`, `--profile`, `--format`, `-k`; an ASCII `format_table()` with a wrapped reasons column; two profiles that use the new features (Nostalgic Night Owl, Hip-Hop Head). |
| `tests/test_recommender.py` | 4 new tests: parsing the new columns, modes swapping the genre/mood priority, the diversity penalty, and new features only counting when requested. |

The agent chose plain ASCII over `tabulate` so the project doesn't need a new dependency.

**What did you verify or fix manually?**

These checks were run during the agent session. I reviewed the results.

- **No regressions:** I saved the top 5 for all 8 original profiles before the change and compared them after. They were identical in Genre-First mode with diversity off, so the README sample output and the model card evaluation are still accurate.
- **A test that was wrong, not the code:** the first diversity test failed. The penalized LoRoom song (4.5 − 1.5 − 0.5 = 2.5) tied exactly with the jazz test song (2.5), and ties go to the lower id. I changed the test to a different artist in the same genre so the expected order isn't decided by a tie.
- **Math check for the new features:** a test confirms the new features add exactly 1.0 (decade) + 0.5 (tag) + 0.4 (popularity 80 × 0.5) + 0.5 (instrumental) + 0.5 (rap) = 2.9 points, and add nothing when the profile doesn't ask for them.
- **Behavior I'd question:** for *Hip-Hop Head*, #2 and #3 are k-pop and pop songs. They rank there mainly because they're from the 2020s (+1.0) and popular, not because they sound like hip-hop. The decade bonus is as large as a mood match, which may be too strong.
- **CLI:** checked `--help`, that an invalid `--mode` gives a clear error, and that both `python -m src.main` and `python src/main.py` still work. All 6 tests pass.

---

## Design Pattern (SF10)

**Which design pattern did you use?**

A lightweight, data-driven **Strategy** pattern. Each ranking mode is a `ScoringMode` object, and `score_song` takes whichever mode it's given.

**How did AI help you brainstorm or implement it?**

The AI suggested two versions of Strategy:

1. **One class per mode** (`GenreFirstScorer`, `MoodFirstScorer`, …), each with its own `score()` method. This is the textbook version, but each class would repeat almost the same scoring code.
2. **One shared scoring function plus a small frozen dataclass of weights per mode.** The modes differ only in how much each rule is worth, not in which rules exist, so only the weights need to change.

I chose option 2. It keeps all the scoring rules in one place, a new mode is a one-line addition to `MODES`, and the existing tests and functions keep working because the default mode is the original Genre-First weights. If a future mode needed genuinely different logic (for example, collaborative filtering), I could switch to option 1 for that mode.

**How does the pattern appear in your final code?**

- `ScoringMode` dataclass and the `GENRE_FIRST`, `MOOD_FIRST`, `ENERGY_FOCUSED` instances in `src/recommender.py`, registered in the `MODES` dict.
- `score_song(user_prefs, song, mode=GENRE_FIRST)` reads its weights from `mode`.
- `recommend_songs(..., mode, diversity)` and `Recommender.recommend(..., mode, diversity)` pass the strategy through.
- `src/main.py` picks the strategy at runtime: `python -m src.main --mode mood-first`.

| Mode | Genre | Mood | Energy (max) | What it's for |
|---|---|---|---|---|
| Genre-First (default) | 2.0 | 1.0 | 1.5 | The original recipe |
| Mood-First | 1.0 | 2.0 | 1.5 | Listeners who care about feeling over style |
| Energy-Focused | 1.0 | 0.5 | 3.0 | Workout or study sessions where intensity matters most |

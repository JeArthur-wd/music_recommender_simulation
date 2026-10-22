# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

Real-world platforms like Spotify and YouTube combine two main approaches. **Collaborative filtering** learns from millions of users' behavior (likes, skips, replays, playlist adds, watch time) and recommends what similar listeners enjoyed, even when the songs sound nothing alike. **Content-based filtering** compares the attributes of the songs themselves (genre, mood, tempo, energy, audio features) to what a user already likes, which lets brand-new songs be recommended before anyone has played them. At scale, these systems run in stages: they generate a few hundred candidates from huge catalogs, rank them with machine-learning models that predict engagement, then re-rank for diversity and freshness. My version is a small **content-based** recommender. It has no other users' data, so it scores each song by how well its attributes match a single user's stated taste. It gives genre the most weight, then **closeness** to the user's target energy (not just "higher is better"), then mood. Every recommendation comes with a plain-language reason.

### Features used

**`Song`** (from `data/songs.csv`):
- `genre`: categorical, matched exactly against the user's favorite genre
- `mood`: categorical, matched exactly against the user's favorite mood
- `energy`: 0–1, scored by closeness to the user's target energy
- `acousticness`: 0–1, a small bonus for users who like acoustic music
- Advanced features (stretch), scored only when the profile asks: `popularity`, `release_decade`, `mood_tags`, `instrumentalness`, `speechiness` (see Stretch Features).
- Also stored but not scored: `id`, `title`, `artist`, `tempo_bpm`, `valence`, `danceability`. In this dataset tempo, danceability and acousticness are highly correlated with energy (|r| ≈ 0.75–0.97), so scoring them all would count the same "intensity" signal several times. Valence is the best candidate for a later experiment.

**`UserProfile`** (`src/main.py` runs a default pop/happy profile plus this lofi study listener):
- `favorite_genre`: `"lofi"`
- `favorite_mood`: `"chill"`
- `target_energy`: `0.4`
- `likes_acoustic`: `True`

**Catalog:** `data/songs.csv` has 20 songs across 17 genres and 16 moods. I expanded it from the original 10 so it also covers sad/quiet songs (folk, blues, classical) and loud/dark songs (metal).

### Data Flow

```
 INPUT                      PROCESS (the loop)                          OUTPUT (the ranking)
 ─────                      ──────────────────                          ────────────────────
 user_prefs                 for each song in songs.csv:                 sort all (song, score, reasons)
  genre  = lofi               genre match?   +2.0                         by score, high → low
  mood   = chill              mood match?    +1.0                       break ties by id
  energy = 0.4                energy close?  +1.5 × (1 − |Δ|)           keep top k
  acoustic = True             acoustic fan?  +0.5                       print title, score, "because…"
        │                     → (song, score, reasons)
        └──────────────────►  (20 songs → 20 scores)  ──────────────►   Top k recommendations
```

**One song through the pipeline:** *Library Rain* (lofi, chill, energy 0.35, acousticness 0.86)
→ genre match +2.0 → mood match +1.0 → energy |0.4 − 0.35| = 0.05, so 1.5 × 0.95 = +1.425 → acoustic +0.5
→ **score 4.925** → ranks #2 behind *Midnight Coding* (4.97), because its energy is 0.02 from the target instead of 0.05.

### Algorithm Recipe

**Scoring Rule** (one song):

```
score = 2.0  if genre matches favorite_genre
      + 1.0  if mood matches favorite_mood
      + 1.5 × (1 − |target_energy − song.energy|)
      + 0.5  if likes_acoustic and song.acousticness > 0.6
```

The energy term rewards songs *near* the target. A song exactly at the target earns the full 1.5 points, and the score drops as the song gets farther away in either direction.

**Why these weights:**
- **Genre (2.0) beats mood (1.0).** Genre is the most stable preference, and a wrong genre feels like the system ignored the user. A wrong mood just feels slightly off.
- **Mood is still worth a full point.** That is enough to lift a same-mood song from another genre (Rooftop Lights, indie pop/happy) above songs that only match on energy.
- **Energy (up to 1.5) mostly sorts songs within a group.** Songs that share a genre or mood usually have similar energy, so this term decides the order inside each group. It can also overturn a match: a mood-only song beats a genre-only song when it is at least 0.67 closer in energy (the 1.0-point genre/mood gap divided by 1.5).
- **Acoustic (0.5) is a tiebreaker.** Acousticness tracks energy almost exactly (r ≈ −0.97), so a larger weight would count the same signal twice.

**Known trade-off:** with genre weighted above mood, a "country / sad" listener gets *Dirt Road Summer* (country but nostalgic and upbeat) ahead of *Empty Platform* (blues / sad). Raising mood to 1.5 reverses that. I'll test this in Experiments.

**Ranking Rule** (whole catalog): score every song, sort from highest to lowest score (ties broken by `id`), and return the top `k` with their explanations. A single score on its own doesn't say whether a song is a *good* pick; ranking compares it against the rest of the catalog to decide what to show.

### Expected Biases

- **Genre over-prioritization.** A genre match (2.0) is worth twice a mood match (1.0), so a song in the right genre but the wrong mood can outrank a great song in a neighboring genre that fits the user's mood. Example: a sad country listener gets upbeat country before sad blues.
- **Exact string matching.** `"pop"` ≠ `"indie pop"` and `"chill"` ≠ `"relaxed"`, so close matches get zero credit. Songs with labels that are similar but not identical lose out.
- **Thin catalog for most genres.** 15 of the 17 genres have only one song. A metal or blues fan gets one strong match, and every result after that is ranked on energy alone.
- **Over-represented styles.** Lofi has 3 songs and pop has 2 (plus indie pop), so those listeners get fuller, more accurate lists than fans of single-song genres.
- **"More of the same."** There's no diversity rule, so a lofi listener's top 3 are near-identical lofi tracks, and two of them are by the same artist (LoRoom).
- **Missing dimensions.** Valence, lyrics, vocals and texture aren't scored, so a calm but *sad* song can rank highly for a user who wants calm *and* content.
- **Hand-picked numbers.** The weights and every song's feature values were chosen by me or generated by AI rather than measured. They reflect my assumptions about what a "vibe" is.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main                                   # all profiles, Genre-First, table view
python -m src.main --mode mood-first                 # switch ranking strategy
python -m src.main --profile "Chill Lofi" --diverse  # one profile, with diversity penalty
python -m src.main --format detailed -k 3            # list layout, top 3
```

Modes: `genre-first` (default), `mood-first`, `energy-focused`. Run `python -m src.main --help` for all options.

4. Or run the web UI (Streamlit), which opens at http://localhost:8501:

```bash
streamlit run app.py
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Output of `python -m src.main` (default: Genre-First mode, table view) for the two main profiles. Run `python -m src.main --profile "High-Energy Pop"` to see a single profile, or add `--format detailed` for the list layout.

```
Profile: High-Energy Pop
  favorite_genre=pop, favorite_mood=happy, target_energy=0.8, likes_acoustic=False
+---+-----------------+---------------------+-------+--------------------------------------+
| # | Title           | Genre / Mood        | Score | Reasons                              |
+---+-----------------+---------------------+-------+--------------------------------------+
| 1 | Sunrise City    | pop / happy         | 4.47  | - genre match: pop (+2.0)            |
|   |                 |                     |       | - mood match: happy (+1.0)           |
|   |                 |                     |       | - energy 0.82 vs target 0.80 (+1.47) |
+---+-----------------+---------------------+-------+--------------------------------------+
| 2 | Gym Hero        | pop / intense       | 3.30  | - genre match: pop (+2.0)            |
|   |                 |                     |       | - energy 0.93 vs target 0.80 (+1.30) |
+---+-----------------+---------------------+-------+--------------------------------------+
| 3 | Rooftop Lights  | indie pop / happy   | 2.44  | - mood match: happy (+1.0)           |
|   |                 |                     |       | - energy 0.76 vs target 0.80 (+1.44) |
+---+-----------------+---------------------+-------+--------------------------------------+
| 4 | Concrete Crown  | hip-hop / confident | 1.47  | - energy 0.78 vs target 0.80 (+1.47) |
+---+-----------------+---------------------+-------+--------------------------------------+
| 5 | Glass Heartbeat | k-pop / euphoric    | 1.43  | - energy 0.85 vs target 0.80 (+1.43) |
+---+-----------------+---------------------+-------+--------------------------------------+

Profile: Chill Lofi
  favorite_genre=lofi, favorite_mood=chill, target_energy=0.4, likes_acoustic=True
+---+---------------------+-----------------+-------+--------------------------------------+
| # | Title               | Genre / Mood    | Score | Reasons                              |
+---+---------------------+-----------------+-------+--------------------------------------+
| 1 | Midnight Coding     | lofi / chill    | 4.97  | - genre match: lofi (+2.0)           |
|   |                     |                 |       | - mood match: chill (+1.0)           |
|   |                     |                 |       | - energy 0.42 vs target 0.40 (+1.47) |
|   |                     |                 |       | - acoustic sound: 0.71 (+0.5)        |
+---+---------------------+-----------------+-------+--------------------------------------+
| 2 | Library Rain        | lofi / chill    | 4.92  | - genre match: lofi (+2.0)           |
|   |                     |                 |       | - mood match: chill (+1.0)           |
|   |                     |                 |       | - energy 0.35 vs target 0.40 (+1.42) |
|   |                     |                 |       | - acoustic sound: 0.86 (+0.5)        |
+---+---------------------+-----------------+-------+--------------------------------------+
| 3 | Focus Flow          | lofi / focused  | 4.00  | - genre match: lofi (+2.0)           |
|   |                     |                 |       | - energy 0.40 vs target 0.40 (+1.50) |
|   |                     |                 |       | - acoustic sound: 0.78 (+0.5)        |
+---+---------------------+-----------------+-------+--------------------------------------+
| 4 | Spacewalk Thoughts  | ambient / chill | 2.82  | - mood match: chill (+1.0)           |
|   |                     |                 |       | - energy 0.28 vs target 0.40 (+1.32) |
|   |                     |                 |       | - acoustic sound: 0.92 (+0.5)        |
+---+---------------------+-----------------+-------+--------------------------------------+
| 5 | Coffee Shop Stories | jazz / relaxed  | 1.96  | - energy 0.37 vs target 0.40 (+1.46) |
|   |                     |                 |       | - acoustic sound: 0.89 (+0.5)        |
+---+---------------------+-----------------+-------+--------------------------------------+
```

These match my expectations for the pop/happy profile. *Sunrise City* is the only song that matches genre, mood and energy, so it wins clearly. *Gym Hero* (pop but intense) ranks above *Rooftop Lights* (indie pop but happy) because a genre match is worth more than a mood match. That's the genre bias I expected. After the top 3, only energy separates the songs, so places 4–5 go to hip-hop and k-pop tracks with energy near 0.8.

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Stretch Features

All four optional challenges are implemented. `ai_interactions.md` documents the prompts, the design pattern and the verification.

### 1. Advanced song features

Five new columns in `data/songs.csv`. Each one is scored only if the user profile asks for it, so the original profiles give exactly the same results as before:

| Column | Type | Profile key | Points |
|---|---|---|---|
| `popularity` | 0–100 | `prefers_popular`: True (mainstream) / False (underground) | up to +0.5, scaled by popularity (or by 100 − popularity) |
| `release_decade` | e.g. 2010 | `preferred_decade` | +1.0 exact decade, +0.5 one decade away |
| `mood_tags` | e.g. `nostalgic;nocturnal` | `mood_tags`: list of wanted tags | +0.5 per matching tag (max 2) |
| `instrumentalness` | 0–1 | `wants_instrumental` | +0.5 if ≥ 0.7 |
| `speechiness` | 0–1 | `likes_rap` | +0.5 if ≥ 0.33 |

```
Profile: Nostalgic Night Owl
  favorite_genre=synthwave, favorite_mood=moody, target_energy=0.6, likes_acoustic=False,
  preferred_decade=2010, mood_tags=['nostalgic', 'nocturnal'], prefers_popular=False,
  wants_instrumental=True
+---+--------------------+-------------------+-------+-------------------------------------------+
| # | Title              | Genre / Mood      | Score | Reasons                                   |
+---+--------------------+-------------------+-------+-------------------------------------------+
| 1 | Night Drive Loop   | synthwave / moody | 7.00  | - genre match: synthwave (+2.0)           |
|   |                    |                   |       | - mood match: moody (+1.0)                |
|   |                    |                   |       | - energy 0.75 vs target 0.60 (+1.27)      |
|   |                    |                   |       | - from the 2010s (+1.0)                   |
|   |                    |                   |       | - mood tags: nocturnal, nostalgic (+1.0)  |
|   |                    |                   |       | - underground pick: popularity 55 (+0.22) |
|   |                    |                   |       | - instrumental: 0.70 (+0.5)               |
+---+--------------------+-------------------+-------+-------------------------------------------+
| 2 | Midnight Coding    | lofi / chill      | 3.00  | - energy 0.42 vs target 0.60 (+1.23)      |
|   |                    |                   |       | - close decade: 2020s (+0.5)              |
|   |                    |                   |       | - mood tags: nocturnal (+0.5)             |
|   |                    |                   |       | - underground pick: popularity 45 (+0.28) |
|   |                    |                   |       | - instrumental: 0.85 (+0.5)               |
+---+--------------------+-------------------+-------+-------------------------------------------+
| 3 | Spacewalk Thoughts | ambient / chill   | 2.91  | - energy 0.28 vs target 0.60 (+1.02)      |
|   |                    |                   |       | - from the 2010s (+1.0)                   |
|   |                    |                   |       | - underground pick: popularity 22 (+0.39) |
|   |                    |                   |       | - instrumental: 0.95 (+0.5)               |
+---+--------------------+-------------------+-------+-------------------------------------------+
```

Mood tags give partial credit that the single `mood` label couldn't. *Midnight Coding* (lofi / chill) earns +0.5 for its "nocturnal" tag, and *Broken Compass* (folk), which no other profile ever got, ranks #4 thanks to its "nostalgic" tag and its decade.

### 2. Scoring modes (Strategy pattern)

Each mode is a `ScoringMode` object holding its weights. `score_song` uses whichever mode it's given.

| Mode | Genre | Mood | Energy (max) |
|---|---|---|---|
| `genre-first` (default) | 2.0 | 1.0 | 1.5 |
| `mood-first` | 1.0 | 2.0 | 1.5 |
| `energy-focused` | 1.0 | 0.5 | 3.0 |

Mood-First fixes the ranking I disagreed with in Genre-First: the happy indie-pop song now beats the intense workout song for a happy pop fan.

```
Profile: High-Energy Pop
  favorite_genre=pop, favorite_mood=happy, target_energy=0.8, likes_acoustic=False
+---+----------------+-------------------+-------+--------------------------------------+
| # | Title          | Genre / Mood      | Score | Reasons                              |
+---+----------------+-------------------+-------+--------------------------------------+
| 1 | Sunrise City   | pop / happy       | 4.47  | - genre match: pop (+1.0)            |
|   |                |                   |       | - mood match: happy (+2.0)           |
|   |                |                   |       | - energy 0.82 vs target 0.80 (+1.47) |
+---+----------------+-------------------+-------+--------------------------------------+
| 2 | Rooftop Lights | indie pop / happy | 3.44  | - mood match: happy (+2.0)           |
|   |                |                   |       | - energy 0.76 vs target 0.80 (+1.44) |
+---+----------------+-------------------+-------+--------------------------------------+
| 3 | Gym Hero       | pop / intense     | 2.30  | - genre match: pop (+1.0)            |
|   |                |                   |       | - energy 0.93 vs target 0.80 (+1.30) |
+---+----------------+-------------------+-------+--------------------------------------+
```

Energy-Focused shows the opposite risk. For *Sad but Hyped*, the only blues/sad song drops out of the top 4 entirely, and the list becomes four loud songs.

### 3. Diversity penalty (`--diverse`)

The ranking picks songs one at a time. Before each pick, a candidate loses **1.5 points for each song by the same artist** and **0.5 points for each song in the same genre** already in the list. The penalty is shown in the reasons.

```
Profile: Chill Lofi
  favorite_genre=lofi, favorite_mood=chill, target_energy=0.4, likes_acoustic=True
+---+---------------------+-----------------+-------+---------------------------------------------------+
| # | Title               | Genre / Mood    | Score | Reasons                                           |
+---+---------------------+-----------------+-------+---------------------------------------------------+
| 1 | Midnight Coding     | lofi / chill    | 4.97  | - genre match: lofi (+2.0)                        |
|   |                     |                 |       | - mood match: chill (+1.0)                        |
|   |                     |                 |       | - energy 0.42 vs target 0.40 (+1.47)              |
|   |                     |                 |       | - acoustic sound: 0.71 (+0.5)                     |
+---+---------------------+-----------------+-------+---------------------------------------------------+
| 2 | Library Rain        | lofi / chill    | 4.42  | - genre match: lofi (+2.0)                        |
|   |                     |                 |       | - mood match: chill (+1.0)                        |
|   |                     |                 |       | - energy 0.35 vs target 0.40 (+1.42)              |
|   |                     |                 |       | - acoustic sound: 0.86 (+0.5)                     |
|   |                     |                 |       | - diversity penalty: genre lofi x1 already listed |
|   |                     |                 |       |   (-0.5)                                          |
+---+---------------------+-----------------+-------+---------------------------------------------------+
| 3 | Spacewalk Thoughts  | ambient / chill | 2.82  | - mood match: chill (+1.0)                        |
|   |                     |                 |       | - energy 0.28 vs target 0.40 (+1.32)              |
|   |                     |                 |       | - acoustic sound: 0.92 (+0.5)                     |
+---+---------------------+-----------------+-------+---------------------------------------------------+
| 4 | Coffee Shop Stories | jazz / relaxed  | 1.96  | - energy 0.37 vs target 0.40 (+1.46)              |
|   |                     |                 |       | - acoustic sound: 0.89 (+0.5)                     |
+---+---------------------+-----------------+-------+---------------------------------------------------+
| 5 | Empty Platform      | blues / sad     | 1.85  | - energy 0.30 vs target 0.40 (+1.35)              |
|   |                     |                 |       | - acoustic sound: 0.75 (+0.5)                     |
+---+---------------------+-----------------+-------+---------------------------------------------------+
```

Compare this with the Chill Lofi table above. *Focus Flow* (a second LoRoom track and a third lofi song) drops out: 4.00 − 1.5 − 1.0 = 1.50. *Empty Platform* (blues) takes the last slot. The list is more varied, but one of the new songs is a sad blues track, which shows that diversity can cost some accuracy.

### 4. Summary table

The default output is an ASCII table with a wrapped **Reasons** column, so every score shows how it was calculated. I used plain ASCII instead of `tabulate`, so no new dependency is needed.

---

## Experiments You Tried

### Experiment 1: Weight Shift (energy ×2, genre ×½)

**Change:** `GENRE_WEIGHT` 2.0 → 1.0 and `ENERGY_WEIGHT` 1.5 → 3.0 in `src/recommender.py`; mood (1.0) and acoustic (0.5) unchanged.

**Math check:** the score is still a sum of non-negative parts. For a valid energy target (0–1), the energy term stays between 0 and 3.0, so scores range from 0 to 5.5 (1.0 + 1.0 + 3.0 + 0.5). Across all 8 profiles, actual scores ranged from 0.75 to 5.44. The one exception is the out-of-range *Energy Overload* profile (target 1.8): its lowest score fell from about −0.97 to −1.95, because doubling the weight also doubled the existing bug.

**What changed in the top 5:** only 2 of 8 profiles changed order. The other 6 kept exactly the same ranking, with every score roughly 1.5 points higher.

| Profile | Baseline | Experiment |
|---|---|---|
| High-Energy Pop | #2 Gym Hero (pop/intense) 3.30, #3 Rooftop Lights (indie pop/happy) 2.44 | **#2 Rooftop Lights 3.88**, #3 Gym Hero 3.61 |
| Acoustic Headbanger | #4 Dirt Road Summer (country, acoustic bonus) 1.45 | Dirt Road Summer drops out; **Storm Runner (rock) #4**, Glass Heartbeat #5 |
| Sad but Hyped | Empty Platform #1 with a 2.12-point lead | Still #1, but the lead shrinks to **0.23** |

**More accurate, or just different?** A little more accurate, in a narrow way:
- **Better:** the happy indie-pop song now beats the intense workout song for a happy pop listener, which matches my intuition. The metal fan no longer gets a country song just for the acoustic bonus.
- **Mostly no change:** the songs matching both genre and mood still win, and the energy-only filler songs (Gym Hero, Glass Heartbeat…) appear just as often. The ranking is not very sensitive to these weights, because within each group the songs already have similar energy.
- **New risk:** genre is now worth only a third of energy. A song from any genre with perfect energy (3.0) beats a genre match (1.0) whose energy is 0.67 or more away. In *Sad but Hyped*, the only blues/sad song now wins by just 0.23, so a slightly higher energy target would push genre and mood out completely.

**Decision:** I reverted to the baseline weights (2.0 / 1.0 / 1.5). The experiment fixed one ranking I disagreed with, but it made genre almost irrelevant. A gentler change, such as raising mood to 1.5, may fix the pop ranking without that side effect.

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this




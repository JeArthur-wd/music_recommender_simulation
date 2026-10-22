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
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Output of `python -m src.main` (top 5 songs for each of the two profiles):

```
Loading songs from data/songs.csv...
Loaded songs: 20

============================================================
Profile: Pop / Happy
  favorite_genre=pop, favorite_mood=happy, target_energy=0.8, likes_acoustic=False
============================================================
1. Sunrise City by Neon Echo
   Score: 4.47  (pop / happy)
     - genre match: pop (+2.0)
     - mood match: happy (+1.0)
     - energy 0.82 vs target 0.80 (+1.47)

2. Gym Hero by Max Pulse
   Score: 3.30  (pop / intense)
     - genre match: pop (+2.0)
     - energy 0.93 vs target 0.80 (+1.30)

3. Rooftop Lights by Indigo Parade
   Score: 2.44  (indie pop / happy)
     - mood match: happy (+1.0)
     - energy 0.76 vs target 0.80 (+1.44)

4. Concrete Crown by Kairo Vex
   Score: 1.47  (hip-hop / confident)
     - energy 0.78 vs target 0.80 (+1.47)

5. Glass Heartbeat by Starlit Vow
   Score: 1.43  (k-pop / euphoric)
     - energy 0.85 vs target 0.80 (+1.43)

============================================================
Profile: Lofi / Chill
  favorite_genre=lofi, favorite_mood=chill, target_energy=0.4, likes_acoustic=True
============================================================
1. Midnight Coding by LoRoom
   Score: 4.97  (lofi / chill)
     - genre match: lofi (+2.0)
     - mood match: chill (+1.0)
     - energy 0.42 vs target 0.40 (+1.47)
     - acoustic sound: 0.71 (+0.5)

2. Library Rain by Paper Lanterns
   Score: 4.92  (lofi / chill)
     - genre match: lofi (+2.0)
     - mood match: chill (+1.0)
     - energy 0.35 vs target 0.40 (+1.42)
     - acoustic sound: 0.86 (+0.5)

3. Focus Flow by LoRoom
   Score: 4.00  (lofi / focused)
     - genre match: lofi (+2.0)
     - energy 0.40 vs target 0.40 (+1.50)
     - acoustic sound: 0.78 (+0.5)

4. Spacewalk Thoughts by Orbit Bloom
   Score: 2.82  (ambient / chill)
     - mood match: chill (+1.0)
     - energy 0.28 vs target 0.40 (+1.32)
     - acoustic sound: 0.92 (+0.5)

5. Coffee Shop Stories by Slow Stereo
   Score: 1.96  (jazz / relaxed)
     - energy 0.37 vs target 0.40 (+1.46)
     - acoustic sound: 0.89 (+0.5)
```

These match my expectations for the pop/happy profile. *Sunrise City* is the only song that matches genre, mood and energy, so it wins clearly. *Gym Hero* (pop but intense) ranks above *Rooftop Lights* (indie pop but happy) because a genre match is worth more than a mood match. That's the genre bias I expected. After the top 3, only energy separates the songs, so places 4–5 go to hip-hop and k-pop tracks with energy near 0.8.

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

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




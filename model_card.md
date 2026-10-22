# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**TuneJudge 1.0**: a small, rule-based music recommender that "judges" every song against your taste and shows its reasoning.

---

## 2. Intended Use  

**Goal / task:** TuneJudge suggests the 5 songs from a small catalog that best fit one listener's stated taste. It doesn't predict clicks or learn from behavior. It scores how well each song's labels and numbers match what the user says they want, and explains each pick.

**Assumptions about the user:**
- They can name one favorite genre and one favorite mood.
- They can describe how energetic they want the music to be, from 0 (calm) to 1 (intense).
- Their taste doesn't change with time of day or activity.

**Intended use:**
- Classroom exploration of how recommenders turn data into rankings.
- Experimenting with weights and seeing how the results change.
- Showing how bias can come from both the scoring rules and the data.

**Not intended for:**
- Real users or a real music app. The catalog is 20 made-up songs.
- Judging what music is "good." The scores only measure fit with one profile.
- Making decisions about artists, such as promotion or payouts. The system favors genres that happen to have more songs.
- Users whose taste can't be described by one genre and one mood.

---

## 3. How the Model Works  

The recommender works like a judge giving points to every song in the catalog, one at a time, based on how well the song fits what the listener says they like.

**What it knows about the listener:** their favorite genre (like pop or lofi), their favorite mood (like happy or chill), how energetic they want the music to be (on a scale from 0 = very calm to 1 = very intense), and whether they like acoustic-sounding music.

**What it looks at in each song:** the song's genre, mood, energy level, and how acoustic it sounds. Each song also lists tempo, "happiness" (valence) and danceability, but these aren't scored. In this catalog, tempo and danceability mostly go up and down with energy, so counting them would just count energy again.

**How a song earns points:**
- **Same genre as the listener's favorite:** 2 points. This is the biggest reward, because hearing the wrong genre usually feels like the app ignored you.
- **Same mood as the listener's favorite:** 1 point.
- **Energy close to what the listener wants:** up to 1.5 points. A song exactly at the listener's energy level gets all 1.5, and the further away it is (too calm *or* too intense), the fewer points it gets. The point is to find songs that are *close*, not just the most or least energetic ones.
- **Acoustic sound, for listeners who like that:** a small half-point bonus.

**How it picks the winners:** after every song has a score, it lines them up from highest to lowest and shows the top five. If two songs tie, the one listed earlier in the catalog goes first, so the results are the same every time. Each recommendation comes with its reasons (for example, "genre match: pop (+2.0)"), so the listener can see exactly why it was chosen.

**Changes from the starter:** the starter code returned the first few songs in the file no matter who was asking. I replaced that with the point system above and the ranking step. I also expanded the catalog from 10 to 20 songs so it covers more genres and moods, including sad and quiet songs.

---

## 4. Data  

**Size:** 20 songs in `data/songs.csv`. The starter file had 10. I added 10 more (generated with AI help) to cover genres and moods that were missing, especially sad, quiet and very loud songs.

**Features per song:** title, artist, genre, mood, energy, tempo (BPM), valence (happiness), danceability and acousticness. Everything except tempo is on a 0–1 scale.

**Coverage:**
- **17 genres:** lofi (3), pop (2), and one song each for rock, ambient, jazz, synthwave, indie pop, folk, hip-hop, r&b, metal, classical, country, edm, reggae, blues and k-pop.
- **16 moods**, from sad and melancholic to happy, euphoric and angry.

**Limits:**
- **Tiny.** Most genres have just one song, so a genre fan gets at most one true match.
- **Not real data.** The songs and their numbers are made up. They reflect my guesses (and the AI's) about how a genre "should" sound.
- **Features move together.** Energy, tempo, danceability and acousticness rise and fall almost in step (acousticness vs. energy: r ≈ −0.97). Louder songs are almost never acoustic.
- **Gaps in taste.** There's nothing about lyrics, language, vocals vs. instrumental, era, or how a song actually sounds. There are very few songs that are sad *and* energetic, or loud *and* acoustic.

---

## 5. Strengths  

- **Clear, consistent tastes work well.** Pop/happy, lofi/chill, rock/intense and metal/angry all got the obvious best song at #1, usually by a wide margin of 2+ points.
- **Opposite users get opposite lists.** The lofi and rock profiles share no songs at all, so the system really does separate calm from intense.
- **"Close to" works better than "more is better."** A calm listener isn't handed the loudest songs. The energy rule rewards songs near the target from either direction.
- **Every pick is explained.** Each song shows exactly where its points came from (for example, "genre match: pop (+2.0)"), so it's easy to see why something ranked where it did, and to spot mistakes.
- **It's predictable.** The same input always gives the same output, and ties are broken the same way every time.

---

## 6. Limitations and Bias 

**Main weakness: once the genre matches run out, the system becomes a "loudness bubble."** Fifteen of the 17 genres in the catalog have only one song, so a fan of rock, metal, blues or most other genres gets one song that truly matches and four slots filled by energy alone. Because those leftover slots ignore genre and mood, the same few high-energy songs (Gym Hero and Glass Heartbeat) land in 5 of my 8 test profiles' top 5, while quiet songs like *Broken Compass* (folk) and *Moonlit Sonata No. 2* (classical) never appear for anyone. The energy-gap math itself treats all users fairly, but the catalog doesn't: only 1 song sits within 0.1 of a very calm target (0.1), compared with 5 songs near 0.4, 0.8 or 0.95, so very calm listeners and listeners in the middle (around 0.6–0.7) get worse matches. In short, the system works best for people whose taste matches what the catalog happens to have the most of: lofi, pop and high energy.

**Other biases found:**
- **"Acoustic" secretly means "calm."** All 9 songs that earn the acoustic bonus have energy 0.58 or lower. A listener who wants loud *and* acoustic music gets pulled toward quiet songs: the metal fan was offered a country song purely for the bonus.
- **Exact label matching.** `"pop"` doesn't match `"indie pop"`, `"chill"` doesn't match `"relaxed"`, and even `" pop"` with a stray space doesn't match `"pop"`. Near misses earn nothing.
- **No sense of happy vs. sad.** Valence isn't scored, so a listener's mood is only respected when a song carries the exact same mood label.
- **No diversity rule.** The lofi listener gets three near-identical lofi tracks, two of them by the same artist.
- **Unknown tastes fail silently.** A genre or mood that isn't in the catalog quietly turns the system into "closest energy wins," with no warning to the user.

---

## 7. Evaluation  

I tested 8 user profiles in `src/main.py`: 3 normal listeners and 5 adversarial or edge-case profiles meant to trick the scoring logic. For each one I checked whether the top 5 made sense, whether the reasons matched the scores, and whether bad input caused strange results.

I also ran one weight experiment (details in the README, "Experiments You Tried"). I doubled the energy weight and halved the genre weight. Only 2 of the 8 rankings changed: the happy indie-pop song moved above the intense workout song for the pop fan, and the country song dropped out of the metal fan's list. But genre became almost meaningless, so I went back to the original weights. Both automated tests in `tests/` pass.

| Profile | Type | Result |
|---|---|---|
| High-Energy Pop | Normal | ✅ As expected; genre bias visible at #2 |
| Chill Lofi | Normal | ✅ As expected; low diversity |
| Deep Intense Rock | Normal | ✅ #1 correct; #3–5 decided by energy alone |
| Sad but Hyped | Conflicting prefs | ⚠️ Labels beat energy; no sad *and* energetic songs exist |
| Ghost Genre | Unknown genre/mood | ⚠️ Silent fallback to energy only |
| Acoustic Headbanger | Contradictory | ⚠️ Acoustic bonus overrides a large energy gap |
| Messy Input | Whitespace/case | ❌ Bug: `" Pop "` doesn't match `"pop"` |
| Energy Overload | Out of range (1.8) | ❌ Bug: no validation, negative energy points |

#### High-Energy Pop

```
============================================================
Profile: High-Energy Pop
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
```

**Expected.** Sunrise City matches all three. Gym Hero (pop, intense) beats Rooftop Lights (indie pop, happy) because genre outweighs mood.

#### Chill Lofi

```
============================================================
Profile: Chill Lofi
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

**Expected.** All three lofi tracks come first. But the top 3 are nearly identical, and two are by the same artist, because there's no diversity rule.

#### Deep Intense Rock

```
============================================================
Profile: Deep Intense Rock
  favorite_genre=rock, favorite_mood=intense, target_energy=0.9, likes_acoustic=False
============================================================
1. Storm Runner by Voltline
   Score: 4.48  (rock / intense)
     - genre match: rock (+2.0)
     - mood match: intense (+1.0)
     - energy 0.91 vs target 0.90 (+1.48)

2. Gym Hero by Max Pulse
   Score: 2.46  (pop / intense)
     - mood match: intense (+1.0)
     - energy 0.93 vs target 0.90 (+1.46)

3. Pulse Reactor by Kinetica
   Score: 1.43  (edm / energetic)
     - energy 0.95 vs target 0.90 (+1.43)

4. Glass Heartbeat by Starlit Vow
   Score: 1.42  (k-pop / euphoric)
     - energy 0.85 vs target 0.90 (+1.42)

5. Iron Tempest by Grave Signal
   Score: 1.40  (metal / angry)
     - energy 0.97 vs target 0.90 (+1.40)
```

**Mostly expected.** Storm Runner wins clearly. After that only energy decides, so k-pop (euphoric) ranks above metal (angry), which a rock fan would probably prefer.

#### Sad but Hyped

```
============================================================
Profile: Sad but Hyped
  favorite_genre=blues, favorite_mood=sad, target_energy=0.9, likes_acoustic=False
============================================================
1. Empty Platform by Grey Avenue
   Score: 3.60  (blues / sad)
     - genre match: blues (+2.0)
     - mood match: sad (+1.0)
     - energy 0.30 vs target 0.90 (+0.60)

2. Storm Runner by Voltline
   Score: 1.48  (rock / intense)
     - energy 0.91 vs target 0.90 (+1.48)

3. Gym Hero by Max Pulse
   Score: 1.46  (pop / intense)
     - energy 0.93 vs target 0.90 (+1.46)

4. Pulse Reactor by Kinetica
   Score: 1.43  (edm / energetic)
     - energy 0.95 vs target 0.90 (+1.43)

5. Glass Heartbeat by Starlit Vow
   Score: 1.42  (k-pop / euphoric)
     - energy 0.85 vs target 0.90 (+1.42)
```

**Adversarial: conflicting preferences.** The only blues/sad song wins on labels alone, even though its energy (0.30) is far from the 0.9 target. Places 2–5 are upbeat hype songs. The system can't find "sad and energetic" songs because it doesn't score valence, and the catalog has almost none anyway.

#### Ghost Genre

```
============================================================
Profile: Ghost Genre
  favorite_genre=indie, favorite_mood=dreamy, target_energy=0.5, likes_acoustic=False
============================================================
1. Velvet Hours by Luna Marie
   Score: 1.47  (r&b / romantic)
     - energy 0.48 vs target 0.50 (+1.47)

2. Island Breeze by Tide Kings
   Score: 1.42  (reggae / uplifting)
     - energy 0.55 vs target 0.50 (+1.42)

3. Dirt Road Summer by Wade Callahan
   Score: 1.38  (country / nostalgic)
     - energy 0.58 vs target 0.50 (+1.38)

4. Midnight Coding by LoRoom
   Score: 1.38  (lofi / chill)
     - energy 0.42 vs target 0.50 (+1.38)

5. Focus Flow by LoRoom
   Score: 1.35  (lofi / focused)
     - energy 0.40 vs target 0.50 (+1.35)
```

**Adversarial: genre/mood not in the catalog.** Nothing matches, so the system quietly falls back to energy only and recommends r&b, reggae and country, with no warning to the user. All scores sit within 0.12 of each other, so the ranking is close to arbitrary.

#### Acoustic Headbanger

```
============================================================
Profile: Acoustic Headbanger
  favorite_genre=metal, favorite_mood=angry, target_energy=0.95, likes_acoustic=True
============================================================
1. Iron Tempest by Grave Signal
   Score: 4.47  (metal / angry)
     - genre match: metal (+2.0)
     - mood match: angry (+1.0)
     - energy 0.97 vs target 0.95 (+1.47)

2. Pulse Reactor by Kinetica
   Score: 1.50  (edm / energetic)
     - energy 0.95 vs target 0.95 (+1.50)

3. Gym Hero by Max Pulse
   Score: 1.47  (pop / intense)
     - energy 0.93 vs target 0.95 (+1.47)

4. Dirt Road Summer by Wade Callahan
   Score: 1.45  (country / nostalgic)
     - energy 0.58 vs target 0.95 (+0.95)
     - acoustic sound: 0.62 (+0.5)

5. Storm Runner by Voltline
   Score: 1.44  (rock / intense)
     - energy 0.91 vs target 0.95 (+1.44)
```

**Adversarial: contradictory taste.** Iron Tempest wins correctly. At #4, the acoustic bonus (+0.5) pulls in Dirt Road Summer (country, nostalgic) even though its energy is 0.37 away from the target. A small bonus is enough to override a large energy mismatch.

#### Messy Input

```
============================================================
Profile: Messy Input
  favorite_genre= Pop , favorite_mood=HAPPY, target_energy=0.8, likes_acoustic=False
============================================================
1. Sunrise City by Neon Echo
   Score: 2.47  (pop / happy)
     - mood match: happy (+1.0)
     - energy 0.82 vs target 0.80 (+1.47)

2. Rooftop Lights by Indigo Parade
   Score: 2.44  (indie pop / happy)
     - mood match: happy (+1.0)
     - energy 0.76 vs target 0.80 (+1.44)

3. Concrete Crown by Kairo Vex
   Score: 1.47  (hip-hop / confident)
     - energy 0.78 vs target 0.80 (+1.47)

4. Glass Heartbeat by Starlit Vow
   Score: 1.43  (k-pop / euphoric)
     - energy 0.85 vs target 0.80 (+1.43)

5. Night Drive Loop by Neon Echo
   Score: 1.42  (synthwave / moody)
     - energy 0.75 vs target 0.80 (+1.42)
```

**Bug found: whitespace.** `"HAPPY"` still matched, because comparisons ignore case, but `" Pop "` with spaces did *not* match `"pop"`. The genre bonus disappeared and Gym Hero dropped out of the top 5 entirely. The fix is to `.strip()` the inputs.

#### Energy Overload

```
============================================================
Profile: Energy Overload
  favorite_genre=edm, favorite_mood=energetic, target_energy=1.8, likes_acoustic=False
============================================================
1. Pulse Reactor by Kinetica
   Score: 3.22  (edm / energetic)
     - genre match: edm (+2.0)
     - mood match: energetic (+1.0)
     - energy 0.95 vs target 1.80 (+0.22)

2. Iron Tempest by Grave Signal
   Score: 0.25  (metal / angry)
     - energy 0.97 vs target 1.80 (+0.25)

3. Gym Hero by Max Pulse
   Score: 0.20  (pop / intense)
     - energy 0.93 vs target 1.80 (+0.20)

4. Storm Runner by Voltline
   Score: 0.16  (rock / intense)
     - energy 0.91 vs target 1.80 (+0.16)

5. Glass Heartbeat by Starlit Vow
   Score: 0.07  (k-pop / euphoric)
     - energy 0.85 vs target 1.80 (+0.07)
```

**Bug found: no input validation.** A target of 1.8 is outside the 0–1 scale. The closeness rule then just means "higher energy is better", scores collapse toward 0, and low-energy songs further down the list get *negative* energy points (e.g. 1.5 × (1 − 1.65) ≈ −0.98). The target should be clamped to 0–1.

### Accuracy and Surprises

**Does High-Energy Pop feel right?** Mostly. *Sunrise City* at #1 is exactly what I'd pick. *Rooftop Lights* (happy indie pop) feels like a better #2 than *Gym Hero* (intense workout pop), but the 2.0 genre weight puts Gym Hero first. Places 4–5 (hip-hop, k-pop) feel random, because they're chosen on energy alone.

**Why *Sunrise City* ranked first:** it is the only song that earns both label bonuses, genre (+2.0) and mood (+1.0), and its energy (0.82) is just 0.02 from the target, for +1.47. That totals **4.47**, 1.17 points ahead of Gym Hero (3.30). Gym Hero has no mood match (−1.0) and its energy is 0.13 off (−0.17 more). Only a song that matches both labels can get close to that score, so changing the energy weight would not change #1.

**Does the same song keep showing up?** Not at #1: all 8 profiles get a different #1 (Messy Input repeats Sunrise City because it's the same profile with messy typing). But in the top-5 lists, *Gym Hero* and *Glass Heartbeat* each appear in **5 of 8** lists, and *Storm Runner* and *Pulse Reactor* in 4. **The cause is not the genre weight.** Once the 1–3 songs that match genre or mood are used up, the remaining slots are filled by energy alone. Six of my eight profiles target energy ≥ 0.8, so the same high-energy songs fill those slots every time. Meanwhile *Broken Compass* (folk, melancholic) and *Moonlit Sonata No. 2* (classical, peaceful) never appear in any list. The fix is partly a better test set (add low-energy profiles) and partly the scoring itself (a valence term or partial mood credit would make these filler slots less uniform).

### What Surprised Me

- **Gym Hero shows up everywhere.** It appeared for the pop fan, the rock fan, the "sad but hyped" listener, the metal fan, and the out-of-range EDM profile. That's 5 of 8 lists.
- **The acoustic preference is really a "calm" preference,** because every acoustic song in the catalog is low energy.
- **Big weight changes barely mattered.** Doubling energy and halving genre (Experiment 1 in the README) changed the order for only 2 of the 8 profiles.
- **A single stray space** in `" Pop "` was enough to wipe out the genre bonus and change the list.

**Why does "Gym Hero" keep showing up for someone who just wants happy pop?** The system can't hear music. It only reads labels and numbers. Gym Hero's label says "pop," so it gets the big "right genre" reward, and its energy number is high, close to what an upbeat listener asked for. The system never checks that Gym Hero is an *intense workout* song rather than a *happy* one. The mood mismatch costs it only 1 point, which is less than the 2 points it gained from the genre label. To the system, it looks like an almost perfect pop song.

### Comparing Profiles

I compared each pair of normal profiles, and each edge case against the normal profile closest to it:

- **High-Energy Pop vs. Chill Lofi:** no songs in common. Pop gets bright, electronic, high-energy tracks (energy around 0.8). Lofi shifts to quiet, acoustic study music (energy around 0.4), and only lofi gets the acoustic bonus. This makes sense: the two profiles disagree on every preference.
- **Chill Lofi vs. Deep Intense Rock:** also no overlap. They sit at opposite ends of the energy scale (0.4 vs. 0.9), so even the songs ranked purely on energy are completely different. Rock's list is all loud tracks; lofi's is all soft ones.
- **High-Energy Pop vs. Deep Intense Rock:** different #1 songs (Sunrise City vs. Storm Runner), because the genre and mood labels pick the winner. But they share Gym Hero and Glass Heartbeat lower down, because both listeners want high energy. Gym Hero earns its points differently for each: the *pop* label for the pop fan, the *intense* label for the rock fan.
- **Deep Intense Rock vs. Sad but Hyped:** both target energy 0.9, so four of their five songs are the same. The only difference is #1: Sad but Hyped's single blues/sad song wins on labels despite being low energy (0.30). This shows that when labels don't match, identical energy targets give almost identical lists.
- **Chill Lofi vs. Ghost Genre:** Ghost Genre asks for a genre and mood that don't exist, so it gets no label bonuses and its scores are all bunched between 1.35 and 1.47. The lofi songs Midnight Coding and Focus Flow still show up at #4–5, but only because their energy is close to 0.5. That's what the lofi list looks like with the labels stripped away.
- **Deep Intense Rock vs. Acoustic Headbanger:** both want loud music, and metal's #1 (Iron Tempest) makes sense. The difference is #4: the acoustic bonus pulls in *Dirt Road Summer*, a mid-energy country song. Every acoustic song in the catalog is calm, so wanting "acoustic" quietly drags a loud listener toward quieter music.
- **High-Energy Pop vs. Messy Input:** these are the same preferences, typed differently. Capital letters ("HAPPY") still matched, but the spaces in " Pop " broke the genre match. Sunrise City's score dropped from 4.47 to 2.47, Gym Hero fell out of the list entirely, and Night Drive Loop took its place. The output changed even though the listener's taste didn't, which is a bug, not a valid result.
- **Deep Intense Rock vs. Energy Overload:** both lists contain the same five loud songs, but in a different order. With an impossible target of 1.8, "closest energy" turns into "loudest wins," so the songs are sorted almost exactly by energy (0.97 → 0.85) after the EDM match. The scores also collapse toward zero. The ranking direction makes sense, but the scores themselves aren't meaningful.

---

## 8. Future Work  

1. **Clean and check user input.** Strip spaces and keep the energy target between 0 and 1. That fixes the two bugs found in testing (`" Pop "` not matching, and negative scores for a 1.8 target). Also warn the user when their genre or mood isn't in the catalog, instead of failing silently.
2. **Give partial credit and score happiness.** Treat related labels as near matches: "indie pop" ≈ "pop", "chill" ≈ "relaxed" ≈ "peaceful". Add a `target_valence` so happy vs. sad is scored directly instead of depending on exact mood labels. This would stop sad blues from showing up for a chill listener.
3. **Add a diversity rule to the ranking.** Allow at most one song per artist, and at most two per genre, in the top 5. This would break up the near-identical lofi list and spread the leftover slots beyond the same few high-energy songs.

Further ideas: let users list several favorite genres, grow the catalog so each genre has several songs, and test raising the mood weight to 1.5 as a gentler alternative to Experiment 1.

---

## 9. Personal Reflection  

**Biggest learning moment:** realizing that recommending is just two steps: score every song, then sort. Before this project, I imagined recommenders "knowing" what I like. In TuneJudge, a single score like 3.30 means nothing on its own. It only becomes a recommendation once it's compared with every other song in the catalog. Splitting the work into a scoring rule (one song) and a ranking rule (the whole list) made the system much easier to understand, test and change.

**How AI tools helped, and when I double-checked them:** AI helped me analyze the dataset, compare weighting strategies with real numbers, write the code, and come up with edge-case profiles I wouldn't have thought of. But I had to check its work in three places:
- **The generated songs.** The 10 songs I added were invented with AI help, including their energy, valence and other numbers. They reflect the AI's guesses about how a genre "should" sound, not real measurements, and that is one source of bias in my results.
- **Numbers that went stale.** After the dataset grew from 10 to 20 songs, a correlation claim in my README was no longer accurate and had to be updated, and one count of single-song genres was wrong (13 instead of 15). AI-written facts need to be rechecked whenever the data changes.
- **The starter bug.** `python -m src.main`, the command in the README, crashed with an import error that was in the starter code all along. It only showed up when I actually ran the program. Reading the code wasn't enough; I had to run it.

**What surprised me:** how much a few simple rules can *feel* like a real recommendation, while also showing that the system can't actually hear music. On paper, *Gym Hero* looks like an almost perfect pop song for a happy-pop listener: the right genre label and high energy. Anyone who listened to it would know it's an intense workout track, not a happy one. The system only sees labels and numbers, so it is confidently wrong in a way a person never would be. Real apps hide this better, but they still depend on whatever their data can describe.

**What I'd try next:**
- **Collaborative filtering:** simulate several users' likes and skips, recommend songs based on similar users, and compare the results to my content-based version.
- **A bigger, real dataset:** real songs with real audio features, so genres have more than one song and the numbers aren't guesses.
- **Great visuals and UI:** replace the terminal output with an interface where users can set their preferences with sliders and see each song's score breakdown visually.  

# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Example: **VibeFinder 1.0**  

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
- What assumptions does it make about the user  
- Is this for real users or classroom exploration  

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

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
- What genres or moods are represented  
- Did you add or remove data  
- Are there parts of musical taste missing in the dataset  

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

No need for numeric metrics unless you created some.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  

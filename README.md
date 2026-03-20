# PlotTwist 🎬

**A context-aware, emotionally intelligent hybrid movie recommendation system.**

> *Watch Different. Feel Everything.*

🌐 **Live Demo:** [plottwistui.vercel.app](https://plottwistui.vercel.app)
🔧 **API:** [adithya112-plottwist.hf.space](https://adithya112-plottwist.hf.space)

---

## What Makes PlotTwist Different

Most recommendation systems ask *"what have you watched?"*

PlotTwist asks *"who are you right now?"*

It combines four engines into a single hybrid scorer — delivering recommendations that adapt to your mood, the time of day, and your evolving taste profile.

---

## Architecture

```
User Request
     │
     ├── Two-Tower Neural CF  ──→  FAISS ANN Retrieval (500 candidates)
     │                                        │
     ├── TF-IDF Content Engine ───────────────┤
     │                                        │
     ├── Emotional Arc Engine ────────────────┤
     │                                        ▼
     └── Context Engine ──────→  Unified Hybrid Scorer
                                              │
                                              ▼
                                    Top-K Recommendations
                                    + Diversity Re-ranking
```

---

## Engines

### 1. Two-Tower Neural Collaborative Filtering
- PyTorch implementation trained with **BPR (Bayesian Personalised Ranking) loss**
- Separate MLP towers for users and movies — same architecture used by YouTube and Pinterest at scale
- Trained on **MovieLens 10M** (8M ratings, 59K users, 10K movies)

### 2. FAISS Approximate Nearest Neighbor Retrieval
- **IVFPQ compressed index** — 369x smaller than flat index (0.3MB vs 427MB)
- Retrieves 500 candidates per request in <10ms
- Replaces brute-force scoring of all 10K movies

### 3. TF-IDF Content-Based Filtering
- Genre, tag and title features vectorized with **TF-IDF (10K vocab, bigrams)**
- Sparse matrix compression: 427MB → 1.2MB
- Builds per-user taste profile from rating history

### 4. Emotional Arc Engine
- Each movie tagged with one of 7 emotional arcs:
  `uplifting · tense_release · cathartic · thought_provoking · bittersweet · draining · neutral_fun`
- Arc tags derived from **VADER sentiment** on tags + genre signal classification
- Mood input shifts recommendations toward emotionally compatible films

### 5. Context Engine
- Lightweight time-of-day multiplier
- Late night → thriller/noir, Weekend → drama/epic, Weekday → comedy/light

### 6. Unified Hybrid Scorer
```python
final_score = w_cf * cf_score + w_cbf * cbf_score + w_emotional * emotional_score
# Context applied as genre multiplier, not additive signal
# Weights adapt per user — cold start users get boosted CBF weight
```

### 7. Diversity Re-ranker
- Enforces genre and arc caps across top-K results
- Prevents single-genre dominance (max 3 per genre, 4 per arc)

---

## Evaluation Results

Evaluated on **300 users** from the held-out test set:

| Engine | P@10 | R@10 | NDCG@10 | HR@10 |
|---|---|---|---|---|
| CF Only | 0.0760 | 0.0187 | 0.0837 | 0.3433 |
| CBF Only | 0.0773 | 0.0191 | 0.0887 | 0.3600 |
| **Hybrid** | **0.1037** | **0.0351** | **0.1191** | **0.4167** |
| Hybrid + Mood | 0.0863–0.0913 | — | 0.0962–0.0965 | 0.38–0.39 |

**Hybrid beats CF alone by 36% on P@10.**

---

## Features

- 🎬 **Personalized recommendations** — hybrid CF + CBF + emotional matching
- 😄 **Mood selector** — 7 moods shift recommendations in real time
- 🔥 **Live TMDB rows** — Trending, Now Playing, Top Rated
- 🎥 **Movie modal** — trailer, cast, plot, runtime, TMDB rating
- ▶️ **YouTube trailers** — embedded and playable inline
- 💾 **Watchlist** — save movies across sessions
- ⭐ **Rate movies** — feeds back into your taste profile
- 👨‍👩‍👧 **Family mode** — minimum regret group recommendations
- 🔍 **Search** — search any movie via TMDB
- 👤 **Profile** — emotional fingerprint from your watchlist
- 🚀 **Onboarding** — rate 5 seed movies to bootstrap your taste profile

---

## Tech Stack

| Layer | Technology |
|---|---|
| CF Engine | PyTorch — Two-Tower Neural Network |
| ANN Retrieval | FAISS IVFPQ |
| CBF Engine | scikit-learn TF-IDF |
| Emotional Arc | VADER + genre signal classification |
| Backend API | FastAPI + Pydantic |
| Frontend | React + Vite + Framer Motion |
| Dataset | MovieLens 10M + TMDB API |
| Deployment | HuggingFace Spaces (API) + Vercel (Frontend) |

---


## Memory Optimizations

| Artifact | Before | After |
|---|---|---|
| TF-IDF matrix | 427 MB dense | 1.2 MB sparse |
| User seen-movies | 276 MB train.csv | 22 MB seen_index.pkl |
| FAISS index | flat + embeddings | IVFPQ 0.3 MB |
| **Total deployment** | **~1.4 GB** | **~330 MB** |

---

## Project Structure

```
plottwist/
├── api/                    # FastAPI backend
├── engines/
│   ├── cf/                 # Two-Tower Neural CF
│   ├── cbf/                # TF-IDF Content-Based
│   ├── emotional/          # Emotional Arc Engine
│   ├── context/            # Context multiplier
│   ├── faiss_index/        # FAISS ANN retrieval
│   └── scorer.py           # Unified hybrid scorer
├── data/
│   ├── models/             # Trained model artifacts
│   └── processed/          # Processed datasets
├── evaluation/             # Offline evaluation scripts
├── scripts/                # Data pipeline + optimization
└── frontend/               # React + Vite app
```

---

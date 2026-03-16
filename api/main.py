import sys
import random
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent / "engines"))
from scorer import plottwistScorer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)


# ── Diversity re-ranker ────────────────────────────────────────────────────

def diversify(results: list, max_per_genre: int = 3, max_per_arc: int = 4) -> list:
    """
    Re-rank results to enforce genre and arc diversity.
    results is a list of dicts with keys: rank, movie_idx, title, genres, arc, score
    """
    genre_count: dict = defaultdict(int)
    arc_count:   dict = defaultdict(int)
    top      = []
    leftover = []

    for r in results:
        genres_str = str(r.get("genres", ""))
        genres     = [g.strip() for g in genres_str.split() if g.strip()]
        arc        = str(r.get("arc", "unknown"))

        genre_ok = all(genre_count[g] < max_per_genre for g in genres) if genres else True
        arc_ok   = arc_count[arc] < max_per_arc

        if genre_ok and arc_ok:
            top.append(r)
            for g in genres:
                genre_count[g] += 1
            arc_count[arc] += 1
        else:
            leftover.append(r)

    random.shuffle(leftover)
    diversified = top + leftover

    # Re-assign ranks after reordering
    for i, r in enumerate(diversified):
        r["rank"] = i + 1

    return diversified


# ── Scorer ─────────────────────────────────────────────────────────────────

scorer: Optional[plottwistScorer] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scorer
    log.info("Loading plottwist scorer...")
    scorer = plottwistScorer()
    log.info("API ready.")
    yield
    log.info("Shutting down.")


# ── App ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "plottwist  API",
    description = "Context-aware hybrid movie recommendation engine",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = [
    "http://localhost:5173",
    "https://plottwistui.vercel.app",],
    allow_methods = ["*"],
    allow_headers = ["*"],
)


# ── Schemas ────────────────────────────────────────────────────────────────

class RecommendRequest(BaseModel):
    user_idx    : int                  = Field(..., ge=0)
    mood        : Optional[str]        = Field(None)
    watch_group : Optional[List[int]]  = Field(None)
    top_k       : int                  = Field(10, ge=1, le=50)
    w_cf        : float                = Field(0.50, ge=0, le=1)
    w_cbf       : float                = Field(0.20, ge=0, le=1)
    w_emotional : float                = Field(0.20, ge=0, le=1)

class MovieResult(BaseModel):
    rank      : int
    movie_idx : int
    title     : str
    genres    : str
    arc       : str
    score     : float

class RecommendResponse(BaseModel):
    user_idx    : int
    mood        : Optional[str]
    family_mode : bool
    timestamp   : str
    results     : List[MovieResult]


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "scorer_loaded": scorer is not None}


@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    if scorer is None:
        raise HTTPException(status_code=503, detail="Scorer not loaded yet")

    valid_moods = {
        "happy", "sad", "excited", "stressed",
        "bored", "reflective", "angry"
    }
    if req.mood and req.mood not in valid_moods:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid mood '{req.mood}'. Valid: {sorted(valid_moods)}"
        )

    if req.user_idx >= scorer.cf_n_users:
        raise HTTPException(
            status_code=404,
            detail=f"user_idx {req.user_idx} out of range (max: {scorer.cf_n_users - 1})"
        )

    now = datetime.now()

    try:
        # Fetch extra candidates so diversity re-ranker has room to work
        candidate_k = min(req.top_k * 3, 50)
        results = scorer.recommend(
            user_idx    = req.user_idx,
            mood        = req.mood,
            timestamp   = now,
            watch_group = req.watch_group,
            top_k       = candidate_k,
            w_cf        = req.w_cf,
            w_cbf       = req.w_cbf,
            w_emotional = req.w_emotional,
        )
    except Exception as e:
        log.error(f"Scorer error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    # Diversify then trim to requested top_k
    diversified = diversify(results, max_per_genre=3, max_per_arc=4)
    diversified = diversified[:req.top_k]

    return RecommendResponse(
        user_idx    = req.user_idx,
        mood        = req.mood,
        family_mode = bool(req.watch_group and len(req.watch_group) > 1),
        timestamp   = now.isoformat(),
        results     = [MovieResult(**r) for r in diversified],
    )


@app.get("/moods")
def list_moods():
    from emotional.emotional_engine import MOOD_TO_ARCS
    return {"moods": MOOD_TO_ARCS}


@app.get("/user/{user_idx}/history")
def user_history(user_idx: int, top_n: int = 10):
    if scorer is None:
        raise HTTPException(status_code=503, detail="Scorer not loaded")
    if user_idx >= scorer.cf_n_users:
        raise HTTPException(status_code=404, detail="User not found")

    user_df = scorer.train_df[
        scorer.train_df["user_idx"] == user_idx
    ].sort_values("timestamp", ascending=False).head(top_n)

    history = []
    for _, row in user_df.iterrows():
        movie_row = scorer.corpus_df[
            scorer.corpus_df["movie_idx"] == row["movie_idx"]]
        if movie_row.empty:
            continue
        history.append({
            "movie_idx": int(row["movie_idx"]),
            "title"    : movie_row["title_clean"].values[0],
            "genres"   : movie_row["genres_clean"].values[0],
            "rating"   : row["rating"],
        })
    return {"user_idx": user_idx, "history": history}
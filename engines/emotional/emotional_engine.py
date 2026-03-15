import numpy as np
import pandas as pd
import pickle
from pathlib import Path
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)

PROCESSED = Path("data/processed")
MODELS    = Path("data/models")
MODELS.mkdir(parents=True, exist_ok=True)


# ── 1. Arc taxonomy ────────────────────────────────────────────────────────

# 7 emotional arcs — each defined by genre signals + sentiment pattern
ARC_TAXONOMY = {
    "uplifting"        : ["animation", "children", "musical", "comedy", "fantasy"],
    "tense_release"    : ["thriller", "mystery", "crime", "action"],
    "cathartic"        : ["drama", "war", "romance"],
    "thought_provoking": ["sci fi", "documentary", "film noir"],
    "bittersweet"      : ["drama", "romance", "indie"],
    "draining"         : ["horror", "war", "film noir"],
    "neutral_fun"      : ["comedy", "adventure", "animation"],
}

# Mood input → compatible arcs (used at recommendation time)
MOOD_TO_ARCS = {
    "happy"    : ["uplifting", "neutral_fun", "tense_release"],
    "sad"      : ["cathartic", "bittersweet", "uplifting"],
    "stressed" : ["neutral_fun", "uplifting", "thought_provoking"],
    "bored"    : ["tense_release", "thought_provoking", "neutral_fun"],
    "excited"  : ["tense_release", "uplifting", "neutral_fun"],
    "reflective": ["thought_provoking", "cathartic", "bittersweet"],
    "scared"   : ["uplifting", "neutral_fun", "cathartic"],
    "angry"    : ["cathartic", "thought_provoking", "neutral_fun"],
}


# ── 2. Tag movies with arc ─────────────────────────────────────────────────

def tag_movies_with_arc(corpus_df):
    """
    Assign each movie a primary emotional arc based on:
    - Genre overlap with arc taxonomy (primary signal)
    - VADER sentiment on tags/corpus (secondary signal)
    """
    log.info("Tagging movies with emotional arcs...")
    analyzer = SentimentIntensityAnalyzer()

    arc_scores_list = []

    for _, row in corpus_df.iterrows():
        genres_text = row["genres_clean"].lower()
        corpus_text = row["corpus"].lower()

        # Score each arc by genre overlap
        arc_scores = {}
        for arc, keywords in ARC_TAXONOMY.items():
            overlap = sum(1 for kw in keywords if kw in genres_text)
            arc_scores[arc] = overlap

        # VADER sentiment modifier
        sentiment = analyzer.polarity_scores(corpus_text)
        compound  = sentiment["compound"]   # -1 to +1

        # Sentiment nudges
        if compound > 0.3:
            arc_scores["uplifting"]   = arc_scores.get("uplifting", 0)   + 1
            arc_scores["neutral_fun"] = arc_scores.get("neutral_fun", 0) + 0.5
        elif compound < -0.3:
            arc_scores["draining"]    = arc_scores.get("draining", 0)    + 1
            arc_scores["cathartic"]   = arc_scores.get("cathartic", 0)   + 0.5

        # Assign primary arc = highest scoring
        primary_arc = max(arc_scores, key=arc_scores.get)

        # Store normalized arc score vector for soft matching
        total = sum(arc_scores.values()) + 1e-8
        arc_vector = {arc: score / total for arc, score in arc_scores.items()}

        arc_scores_list.append({
            "movieId"    : row["movieId"],
            "movie_idx"  : row["movie_idx"],
            "primary_arc": primary_arc,
            "sentiment"  : compound,
            **{f"arc_{k}": v for k, v in arc_vector.items()}
        })

    arc_df = pd.DataFrame(arc_scores_list)
    log.info(f"Arc distribution:\n{arc_df['primary_arc'].value_counts().to_string()}")
    return arc_df


# ── 3. Build user emotional fingerprint ───────────────────────────────────

def build_emotional_fingerprint(user_idx, train_df, arc_df, rating_threshold=3.5):
    """
    User's emotional fingerprint = weighted average of arc vectors
    of movies they liked. Higher rating = more weight.
    """
    user_ratings = train_df[
        (train_df["user_idx"] == user_idx) &
        (train_df["rating"] >= rating_threshold)
    ]

    if len(user_ratings) == 0:
        return None

    arc_cols = [c for c in arc_df.columns if c.startswith("arc_")]

    # Merge with arc data
    merged = user_ratings.merge(
        arc_df[["movie_idx"] + arc_cols],
        on="movie_idx", how="inner"
    )

    if len(merged) == 0:
        return None

    weights = merged["rating"].values - rating_threshold + 0.5
    weights = weights / weights.sum()

    fingerprint = (merged[arc_cols].values * weights[:, None]).sum(axis=0)
    return dict(zip(arc_cols, fingerprint))


# ── 4. Get emotional arc scores ───────────────────────────────────────────

def get_emotional_scores(user_idx, mood, train_df, arc_df,
                         seen_movie_idxs=None):
    """
    Combines:
    - Mood-to-arc mapping (what arcs fit your current mood)
    - User's emotional fingerprint (what arcs you historically enjoy)
    Returns score array of shape (n_movies,)
    """
    arc_cols   = [c for c in arc_df.columns if c.startswith("arc_")]
    arc_names  = [c.replace("arc_", "") for c in arc_cols]
    n_movies   = arc_df["movie_idx"].max() + 1

    # Mood signal — binary boost for compatible arcs
    mood_vector = np.zeros(len(arc_cols))
    if mood and mood in MOOD_TO_ARCS:
        compatible = MOOD_TO_ARCS[mood]
        for i, arc in enumerate(arc_names):
            if arc in compatible:
                # Primary arc gets full weight, others get partial
                mood_vector[i] = 1.0 if arc == compatible[0] else 0.5

    # User fingerprint signal
    fingerprint = build_emotional_fingerprint(user_idx, train_df, arc_df)
    if fingerprint:
        fp_vector = np.array([fingerprint.get(c, 0) for c in arc_cols])
    else:
        fp_vector = np.ones(len(arc_cols)) / len(arc_cols)  # uniform fallback

    # Blend mood + fingerprint (60% mood, 40% fingerprint)
    if mood and mood in MOOD_TO_ARCS:
        target_vector = 0.6 * mood_vector + 0.4 * fp_vector
    else:
        target_vector = fp_vector

    # Score each movie by dot product with target vector
    movie_arc_matrix = arc_df[arc_cols].values   # (n_movies, n_arcs)
    raw_scores       = movie_arc_matrix @ target_vector

    # Map back to movie_idx space
    scores = np.zeros(n_movies)
    scores[arc_df["movie_idx"].values] = raw_scores

    if seen_movie_idxs is not None:
        scores[seen_movie_idxs] = -np.inf

    return scores


# ── 5. Post-watch emotion logger ───────────────────────────────────────────

def log_post_watch_emotion(user_idx, movie_idx, emotion, emotion_log_path):
    """
    Stores how a user felt AFTER watching a movie.
    Used to refine emotional fingerprint over time.
    Emotions: happy, sad, excited, scared, moved, bored, satisfied, unsettled
    """
    entry = pd.DataFrame([{
        "user_idx" : user_idx,
        "movie_idx": movie_idx,
        "emotion"  : emotion,
    }])
    if emotion_log_path.exists():
        existing = pd.read_csv(emotion_log_path)
        entry    = pd.concat([existing, entry], ignore_index=True)
    entry.to_csv(emotion_log_path, index=False)


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Loading data...")
    corpus_df = pd.read_csv(PROCESSED / "corpus.csv")
    train_df  = pd.read_csv(PROCESSED / "train.csv")

    # Tag movies
    arc_df = tag_movies_with_arc(corpus_df)
    arc_df.to_csv(PROCESSED / "movie_arcs.csv", index=False)

    # Test on sample user + mood
    sample_user = train_df["user_idx"].iloc[0]
    scores = get_emotional_scores(
        user_idx         = sample_user,
        mood             = "excited",
        train_df         = train_df,
        arc_df           = arc_df,
    )

    top5_idx = np.argsort(scores)[::-1][:5]
    top5_arcs = arc_df[arc_df["movie_idx"].isin(top5_idx)][
        ["movie_idx", "primary_arc"]].set_index("movie_idx")

    log.info(f"Sample user {sample_user} | mood=excited | top 5 movie_idxs: {top5_idx}")
    for idx in top5_idx:
        arc = top5_arcs.loc[idx, "primary_arc"] if idx in top5_arcs.index else "?"
        log.info(f"  movie_idx={idx} | arc={arc}")

    with open(MODELS / "emotional_config.pkl", "wb") as f:
        pickle.dump({
            "arc_taxonomy" : ARC_TAXONOMY,
            "mood_to_arcs" : MOOD_TO_ARCS,
        }, f)

    log.info("✅ Emotional arc engine complete.")
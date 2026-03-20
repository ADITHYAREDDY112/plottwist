import numpy as np
import pandas as pd
import pickle
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)

PROCESSED = Path("data/processed")
MODELS    = Path("data/models")
MODELS.mkdir(parents=True, exist_ok=True)


# ── 1. Build movie text corpus ─────────────────────────────────────────────

def build_corpus(movies, movie_tags, movie_map):
    """
    Build corpus aligned to movie_idx used in train/val/test.
    Critical: corpus row position must match movie_idx exactly.
    """
    log.info("Building text corpus...")

    # Merge movie_map so we know each movie's training index
    df = movies[["movieId", "title_clean", "genres", "year"]].copy()
    df = df.merge(movie_map, on="movieId", how="inner")  # only keep mapped movies
    df = df.merge(movie_tags, on="movieId", how="left")
    df["tags_text"] = df["tags_text"].fillna("")

    df["genres_clean"] = df["genres"].str.replace("|", " ", regex=False)\
                                     .str.replace("-", " ", regex=False)\
                                     .str.lower()

    df["corpus"] = (
        df["title_clean"].str.lower() + " " +
        df["genres_clean"] + " " +
        df["genres_clean"] + " " +
        df["tags_text"]
    )

    # ── CRITICAL: sort by movie_idx so row 0 = movie_idx 0 ──
    df = df.sort_values("movie_idx").reset_index(drop=True)

    log.info(f"Corpus built for {len(df):,} movies | "
             f"movie_idx range: {df['movie_idx'].min()}–{df['movie_idx'].max()}")
    return df


# ── 2. TF-IDF vectors ─────────────────────────────────────────────────────

def build_tfidf_vectors(corpus_df):
    """
    TF-IDF on the combined corpus.
    Captures genre/tag keyword overlap between movies.
    """
    log.info("Building TF-IDF vectors...")

    vectorizer = TfidfVectorizer(
        max_features = 10_000,
        ngram_range  = (1, 2),   # unigrams + bigrams
        min_df       = 2,        # ignore terms appearing in < 2 movies
        max_df       = 0.95,     # ignore terms in > 95% of movies
        sublinear_tf = True,     # log normalization
    )

    tfidf_matrix = vectorizer.fit_transform(corpus_df["corpus"])
    tfidf_matrix = normalize(tfidf_matrix, norm="l2")

    log.info(f"TF-IDF matrix: {tfidf_matrix.shape} | "
             f"Vocab size: {len(vectorizer.vocabulary_):,}")

    return tfidf_matrix, vectorizer


# ── 3. Sentence embeddings ────────────────────────────────────────────────

def build_semantic_vectors(corpus_df, model_name="all-MiniLM-L6-v2"):
    """
    Dense semantic embeddings via sentence-transformers.
    Captures meaning beyond keyword overlap —
    e.g. 'space exploration' ≈ 'interstellar journey'
    """
    log.info(f"Building semantic embeddings with {model_name}...")
    log.info("(First run downloads ~90MB model — subsequent runs use cache)")

    model = SentenceTransformer(model_name)

    # Use title + genres only for semantic embedding
    # Tags are noisy for semantic meaning
    semantic_text = (
        corpus_df["title_clean"] + " " +
        corpus_df["genres_clean"]
    ).tolist()

    embeddings = model.encode(
        semantic_text,
        batch_size    = 256,
        show_progress_bar = True,
        normalize_embeddings = True,   # L2 normalize for cosine similarity
    )

    log.info(f"Semantic embeddings: {embeddings.shape}")
    return embeddings, model


# ── 4. Fuse TF-IDF + semantic into one vector ─────────────────────────────

def fuse_vectors(tfidf_matrix, semantic_embeddings, alpha=0.4):
    """
    Final movie vector = alpha * semantic + (1-alpha) * tfidf
    alpha=0.4 means 40% semantic meaning, 60% keyword/genre matching.
    Tunable — increase alpha for more semantic, decrease for more genre-exact.
    """
    log.info(f"Fusing vectors | alpha(semantic)={alpha}")

    # Convert sparse TF-IDF to dense for fusion
    tfidf_dense = tfidf_matrix.toarray().astype(np.float32)

    # Pad or truncate to match dimensions if needed
    sem_dim   = semantic_embeddings.shape[1]   # 384 for MiniLM
    tfidf_dim = tfidf_dense.shape[1]           # 10,000

    # Keep them separate — fuse at score time via weighted sum
    # Storing both allows flexible reweighting later
    log.info(f"TF-IDF dim: {tfidf_dim} | Semantic dim: {sem_dim}")
    return tfidf_dense, semantic_embeddings


# ── 5. Build user CBF profile ─────────────────────────────────────────────

def build_user_profile(user_idx, train_df, tfidf_dense, semantic_embeddings,
                       rating_threshold=3.5):
    """
    User profile = weighted average of movie vectors for movies they liked.
    Weight = (rating - threshold) so higher ratings contribute more.
    """
    user_ratings = train_df[
        (train_df["user_idx"] == user_idx) &
        (train_df["rating"] >= rating_threshold)
    ]

    if len(user_ratings) == 0:
        return None, None

    movie_idxs = user_ratings["movie_idx"].values
    weights    = (user_ratings["rating"].values - rating_threshold + 0.5)
    weights    = weights / weights.sum()

    # Filter to valid indices
    valid = movie_idxs < len(tfidf_dense)
    movie_idxs = movie_idxs[valid]
    weights    = weights[valid]

    if len(movie_idxs) == 0:
        return None, None

    tfidf_profile   = (tfidf_dense[movie_idxs] * weights[:, None]).sum(axis=0)
    semantic_profile = None
    if semantic_embeddings is not None:
        semantic_profile = (semantic_embeddings[movie_idxs] * weights[:, None]).sum(axis=0)

    # L2 normalize profiles
    tfidf_norm = np.linalg.norm(tfidf_profile)
    if tfidf_norm > 0:
        tfidf_profile /= tfidf_norm

    if semantic_profile is not None:
        sem_norm = np.linalg.norm(semantic_profile)
        if sem_norm > 0:
            semantic_profile /= sem_norm

    return tfidf_profile, semantic_profile


# ── 6. Get CBF scores for a user ──────────────────────────────────────────

def get_cbf_scores(user_idx, train_df, tfidf_dense, semantic_embeddings,
                   alpha=0.4, seen_movie_idxs=None):
    tfidf_profile, semantic_profile = build_user_profile(
        user_idx, train_df, tfidf_dense, semantic_embeddings)

    if tfidf_profile is None:
        return None

    scores = tfidf_dense @ tfidf_profile

    # ── Normalize to [0,1] ──
    def minmax(arr):
        mn, mx = arr.min(), arr.max()
        return (arr - mn) / (mx - mn + 1e-8)

    scores = minmax(scores)

    if semantic_profile is not None and semantic_embeddings is not None:
        semantic_scores = semantic_embeddings @ semantic_profile
        semantic_scores = minmax(semantic_scores)
        scores = alpha * semantic_scores + (1 - alpha) * scores

    if seen_movie_idxs is not None:
        scores[seen_movie_idxs] = -np.inf

    return scores

# ── 7. Evaluate CBF P@10 ──────────────────────────────────────────────────

def evaluate_cbf(val_df, train_df, tfidf_dense, semantic_embeddings,
                 k=10, n_sample=500):
    log.info(f"Evaluating CBF P@{k} on {n_sample} sampled users...")

    positives = val_df[val_df["rating"] >= 3.5]
    user_pos  = positives.groupby("user_idx")["movie_idx"].apply(set).to_dict()
    sampled   = list(user_pos.keys())
    np.random.shuffle(sampled)
    sampled   = sampled[:n_sample]

    hits = 0
    total = 0

    for user_idx in sampled:
        true_pos = user_pos[user_idx]
        scores   = get_cbf_scores(user_idx, train_df,
                                  tfidf_dense, semantic_embeddings)
        if scores is None:
            continue

        top_k = np.argsort(scores)[::-1][:k]
        hits  += len(set(top_k) & true_pos)
        total += k

    p_at_k = hits / total if total > 0 else 0.0
    log.info(f"CBF P@{k} = {p_at_k:.4f}")
    return p_at_k


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Loading processed data...")
    movies     = pd.read_csv(PROCESSED / "movies.csv")
    movie_tags = pd.read_csv(PROCESSED / "movie_tags.csv")
    movie_map  = pd.read_csv(PROCESSED / "movie_map.csv")   # ← added
    train_df   = pd.read_csv(PROCESSED / "train.csv")
    val_df     = pd.read_csv(PROCESSED / "val.csv")

    # Build corpus — now index-aligned
    corpus_df = build_corpus(movies, movie_tags, movie_map)  # ← pass movie_map

    # Build vectors
    tfidf_matrix, vectorizer        = build_tfidf_vectors(corpus_df)
    semantic_embeddings, sent_model  = build_semantic_vectors(corpus_df)

    # Fuse
    tfidf_dense, semantic_embeddings = fuse_vectors(
    tfidf_matrix, semantic_embeddings, alpha=0.6)

    # Evaluate
    evaluate_cbf(val_df, train_df, tfidf_dense, semantic_embeddings)

    # Save
    log.info("Saving CBF artifacts...")
    np.save(MODELS / "tfidf_dense.npy",         tfidf_dense)
    np.save(MODELS / "semantic_embeddings.npy",  semantic_embeddings)

    corpus_df[["movieId", "movie_idx", "title_clean",
               "genres_clean", "corpus"]].to_csv(
        PROCESSED / "corpus.csv", index=False)

    with open(MODELS / "tfidf_vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)

    with open(MODELS / "cbf_config.pkl", "wb") as f:
        pickle.dump({"alpha": 0.6, "n_movies": len(corpus_df)}, f)

    log.info("✅ CBF engine complete.")

 
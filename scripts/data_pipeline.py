import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)

RAW       = Path("data/raw/ml-10M100K")
PROCESSED = Path("data/processed")
PROCESSED.mkdir(parents=True, exist_ok=True)


# ── 1. Load ────────────────────────────────────────────────────────────────

def load_raw():
    log.info("Loading raw files...")

    ratings = pd.read_csv(
        RAW / "ratings.dat",
        sep="::", engine="python", header=None,
        names=["userId", "movieId", "rating", "timestamp"]
    )
    movies = pd.read_csv(
        RAW / "movies.dat",
        sep="::", engine="python", header=None,
        names=["movieId", "title", "genres"],
        encoding="latin-1"
    )
    tags = pd.read_csv(
        RAW / "tags.dat",
        sep="::", engine="python", header=None,
        names=["userId", "movieId", "tag", "timestamp"],
        encoding="latin-1"
    )

    log.info(f"Ratings: {len(ratings):,} | Movies: {len(movies):,} | Tags: {len(tags):,}")
    return ratings, movies, tags


# ── 2. Filter cold users ───────────────────────────────────────────────────

def filter_cold_users(ratings, min_ratings=20):
    log.info(f"Filtering users with < {min_ratings} ratings...")
    counts       = ratings.groupby("userId")["movieId"].count()
    valid_users  = counts[counts >= min_ratings].index
    filtered     = ratings[ratings["userId"].isin(valid_users)].copy()
    log.info(f"Users: {counts.shape[0]:,} → {len(valid_users):,} "
             f"| Ratings: {len(ratings):,} → {len(filtered):,}")
    return filtered


# ── 3. Clean movies ────────────────────────────────────────────────────────

def clean_movies(movies):
    log.info("Cleaning movies...")

    movies["year"] = movies["title"].str.extract(r"\((\d{4})\)$").astype(float)
    movies["title_clean"] = movies["title"].str.replace(
        r"\s*\(\d{4}\)$", "", regex=True).str.strip()

    movies["genre_list"] = movies["genres"].apply(
        lambda g: g.split("|") if g != "(no genres listed)" else [])

    all_genres = sorted({g for gl in movies["genre_list"] for g in gl})
    for genre in all_genres:
        movies[f"genre_{genre.lower().replace('-', '_')}"] = \
            movies["genre_list"].apply(lambda gl: int(genre in gl))

    log.info(f"Genres found: {all_genres}")
    return movies


# ── 4. Clean tags ──────────────────────────────────────────────────────────

def clean_tags(tags, valid_movie_ids):
    log.info("Cleaning tags...")
    tags = tags[tags["movieId"].isin(valid_movie_ids)].copy()
    tags["tag"] = tags["tag"].str.lower().str.strip()
    tags = tags.dropna(subset=["tag"])

    movie_tags = (tags.groupby("movieId")["tag"]
                      .apply(lambda t: " ".join(t.unique()))
                      .reset_index()
                      .rename(columns={"tag": "tags_text"}))
    log.info(f"Movies with tags: {len(movie_tags):,}")
    return movie_tags


# ── 5. Stats ───────────────────────────────────────────────────────────────

def compute_stats(ratings):
    log.info("Computing interaction stats...")
    stats = {
        "n_users"    : ratings["userId"].nunique(),
        "n_movies"   : ratings["movieId"].nunique(),
        "n_ratings"  : len(ratings),
        "sparsity"   : 1 - len(ratings) / (
            ratings["userId"].nunique() * ratings["movieId"].nunique()),
        "rating_mean": ratings["rating"].mean(),
        "rating_std" : ratings["rating"].std(),
    }
    for k, v in stats.items():
        log.info(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v:,}")
    return stats


# ── 6. Remap IDs ───────────────────────────────────────────────────────────

def remap_ids(ratings):
    log.info("Remapping IDs to contiguous integers...")
    user_map  = {uid: i for i, uid in enumerate(ratings["userId"].unique())}
    movie_map = {mid: i for i, mid in enumerate(ratings["movieId"].unique())}
    ratings   = ratings.copy()
    ratings["user_idx"]  = ratings["userId"].map(user_map)
    ratings["movie_idx"] = ratings["movieId"].map(movie_map)
    return ratings, user_map, movie_map


# ── 7. Temporal split ──────────────────────────────────────────────────────

def temporal_split(ratings, val_frac=0.1, test_frac=0.1):
    log.info("Splitting train / val / test by timestamp...")
    ratings    = ratings.sort_values("timestamp")
    n          = len(ratings)
    val_start  = int(n * (1 - val_frac - test_frac))
    test_start = int(n * (1 - test_frac))
    train = ratings.iloc[:val_start]
    val   = ratings.iloc[val_start:test_start]
    test  = ratings.iloc[test_start:]
    log.info(f"  Train: {len(train):,} | Val: {len(val):,} | Test: {len(test):,}")
    return train, val, test


# ── 8. Save ────────────────────────────────────────────────────────────────

def save(train, val, test, movies, movie_tags, user_map, movie_map):
    log.info("Saving processed files...")
    train.to_csv(PROCESSED / "train.csv",           index=False)
    val.to_csv(PROCESSED / "val.csv",               index=False)
    test.to_csv(PROCESSED / "test.csv",             index=False)
    movies.to_csv(PROCESSED / "movies.csv",         index=False)
    movie_tags.to_csv(PROCESSED / "movie_tags.csv", index=False)

    pd.DataFrame(list(user_map.items()),
                 columns=["userId", "user_idx"]).to_csv(
                 PROCESSED / "user_map.csv", index=False)
    pd.DataFrame(list(movie_map.items()),
             columns=["movieId","movie_idx"]).to_csv(
             PROCESSED / "movie_map.csv", index=False)

    log.info("All files saved to data/processed/")


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ratings, movies, tags = load_raw()
    ratings    = filter_cold_users(ratings, min_ratings=20)
    movies     = clean_movies(movies)
    movie_tags = clean_tags(tags, valid_movie_ids=movies["movieId"].unique())
    stats      = compute_stats(ratings)
    ratings, user_map, movie_map = remap_ids(ratings)
    train, val, test = temporal_split(ratings)
    save(train, val, test, movies, movie_tags, user_map, movie_map)
    log.info("✅ Pipeline complete.")
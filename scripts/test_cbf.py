import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from pathlib import Path

PROCESSED = Path("data/processed")
MODELS    = Path("data/models")

tfidf_dense         = np.load(MODELS / "tfidf_dense.npy")
semantic_embeddings = np.load(MODELS / "semantic_embeddings.npy")
corpus_df           = pd.read_csv(PROCESSED / "corpus.csv")
train_df            = pd.read_csv(PROCESSED / "train.csv")

from engines.cbf.cbf_engine import get_cbf_scores, build_user_profile

# Pick a user who liked action movies
sample_user = 36071
user_ratings = train_df[
    (train_df["user_idx"] == sample_user) &
    (train_df["rating"] >= 3.5)
]

print(f"\n=== User {sample_user} liked these movies ===")
liked_idxs = user_ratings["movie_idx"].values[:8]
print(corpus_df[corpus_df["movie_idx"].isin(liked_idxs)][
    ["title_clean", "genres_clean"]].to_string(index=False))

print(f"\n=== CBF Top 10 Recommendations ===")
seen = train_df[train_df["user_idx"] == sample_user]["movie_idx"].values
scores = get_cbf_scores(sample_user, train_df, tfidf_dense,
                        semantic_embeddings, seen_movie_idxs=seen)
top10  = np.argsort(scores)[::-1][:10]
print(corpus_df[corpus_df["movie_idx"].isin(top10)][
    ["title_clean", "genres_clean"]].to_string(index=False))
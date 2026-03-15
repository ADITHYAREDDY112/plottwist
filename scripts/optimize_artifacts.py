import numpy as np
import pandas as pd
import scipy.sparse as sp
import pickle
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)

PROCESSED = Path("data/processed")
MODELS    = Path("data/models")


# ── 1. Convert tfidf_dense.npy → sparse ───────────────────────────────────

log.info("Converting TF-IDF dense → sparse...")
tfidf_dense = np.load(MODELS / "tfidf_dense.npy")
log.info(f"Dense shape: {tfidf_dense.shape} | "
         f"Size: {tfidf_dense.nbytes / 1e6:.1f} MB")

tfidf_sparse = sp.csr_matrix(tfidf_dense)
sp.save_npz(MODELS / "tfidf_sparse.npz", tfidf_sparse)

sparse_size = (MODELS / "tfidf_sparse.npz").stat().st_size / 1e6
log.info(f"Sparse saved | Size: {sparse_size:.1f} MB")
log.info(f"Compression ratio: {tfidf_dense.nbytes / 1e6 / sparse_size:.1f}x")


# ── 2. Precompute seen-movies index from train.csv ─────────────────────────

log.info("Building compact seen-movies index from train.csv...")
train_df = pd.read_csv(PROCESSED / "train.csv",
                       usecols=["user_idx", "movie_idx"])

seen_index = (train_df.groupby("user_idx")["movie_idx"]
                       .apply(list)
                       .to_dict())

with open(MODELS / "seen_index.pkl", "wb") as f:
    pickle.dump(seen_index, f)

size = (MODELS / "seen_index.pkl").stat().st_size / 1e6
log.info(f"Seen index saved | {len(seen_index):,} users | Size: {size:.1f} MB")


log.info("✅ Optimization complete.")
log.info("You can now delete train.csv from deployment.")
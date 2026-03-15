import numpy as np
import pandas as pd
import pickle
import faiss
import torch
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)

MODELS  = Path("data/models")
DEVICE  = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ── 1. Build FAISS index from movie embeddings ─────────────────────────────

def build_faiss_index(cf_model, n_movies):
    """
    Extract movie embeddings from Two-Tower model and build FAISS index.
    Index type: IVF (Inverted File) with flat quantizer — good balance
    of speed and accuracy for ~10K movies.
    """
    log.info("Extracting movie embeddings from Two-Tower model...")
    cf_model.eval()

    batch_size = 512
    all_embeddings = []

    with torch.no_grad():
        for start in range(0, n_movies, batch_size):
            end     = min(start + batch_size, n_movies)
            ids     = torch.arange(start, end, dtype=torch.long).to(DEVICE)
            embeds  = cf_model.forward_movie(ids).cpu().numpy()
            all_embeddings.append(embeds)

    movie_embeddings = np.vstack(all_embeddings).astype(np.float32)
    log.info(f"Movie embeddings shape: {movie_embeddings.shape}")

    # L2 normalize for cosine similarity search
    faiss.normalize_L2(movie_embeddings)

    # Build IVF index
    dim        = movie_embeddings.shape[1]   # embed_dim = 64
    n_clusters = min(64, n_movies // 10)     # rule of thumb: sqrt(n)

    quantizer  = faiss.IndexFlatIP(dim)      # inner product = cosine after L2 norm
    index      = faiss.IndexIVFFlat(quantizer, dim, n_clusters,
                                    faiss.METRIC_INNER_PRODUCT)

    log.info(f"Training FAISS index | dim={dim} clusters={n_clusters}...")
    index.train(movie_embeddings)
    index.add(movie_embeddings)
    index.nprobe = 16    # search 16 clusters per query — accuracy/speed tradeoff

    log.info(f"FAISS index built | {index.ntotal} vectors")
    return index, movie_embeddings


def save_faiss_index(index, movie_embeddings):
    faiss.write_index(index, str(MODELS / "faiss_index.bin"))
    np.save(MODELS / "movie_embeddings.npy", movie_embeddings)
    log.info("FAISS index saved → data/models/faiss_index.bin")


def load_faiss_index():
    index            = faiss.read_index(str(MODELS / "faiss_index.bin"))
    movie_embeddings = np.load(MODELS / "movie_embeddings.npy")
    index.nprobe     = 16
    log.info(f"FAISS index loaded | {index.ntotal} vectors")
    return index, movie_embeddings


# ── 2. Get FAISS candidates for a user ────────────────────────────────────

def get_faiss_candidates(cf_model, user_idx, faiss_index,
                         n_candidates=500, seen_movie_idxs=None):
    """
    Use FAISS ANN to retrieve top n_candidates movies for a user.
    Returns array of candidate movie indices.
    """
    cf_model.eval()

    with torch.no_grad():
        u_tensor = torch.tensor([user_idx], dtype=torch.long).to(DEVICE)
        u_vec    = cf_model.forward_user(u_tensor).cpu().numpy().astype(np.float32)

    # L2 normalize user vector
    faiss.normalize_L2(u_vec)

    # Search — retrieve more than needed to account for filtering seen items
    fetch_k      = min(n_candidates * 2, faiss_index.ntotal)
    scores, idxs = faiss_index.search(u_vec, fetch_k)

    candidates = idxs[0]   # shape (fetch_k,)
    scores     = scores[0]

    # Filter out seen movies
    if seen_movie_idxs is not None and len(seen_movie_idxs) > 0:
        seen_set   = set(seen_movie_idxs.tolist())
        mask       = np.array([i not in seen_set for i in candidates])
        candidates = candidates[mask]
        scores     = scores[mask]

    return candidates[:n_candidates], scores[:n_candidates]


# ── Main: build and save index ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from cf.cf_engine import TwoTowerNCF
    import pickle

    log.info("Loading CF model...")
    with open(MODELS / "cf_config.pkl", "rb") as f:
        cf_config = pickle.load(f)

    model = TwoTowerNCF(
        n_users     = cf_config["n_users"],
        n_movies    = cf_config["n_movies"],
        embed_dim   = cf_config["embed_dim"],
        hidden_dims = cf_config["hidden_dims"],
    ).to(DEVICE)
    model.load_state_dict(
        torch.load(MODELS / "cf_model_best.pt", map_location=DEVICE))
    model.eval()

    index, embeddings = build_faiss_index(model, cf_config["n_movies"])
    save_faiss_index(index, embeddings)
    log.info("✅ FAISS index complete.")
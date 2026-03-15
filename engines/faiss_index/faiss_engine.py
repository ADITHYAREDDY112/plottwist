import numpy as np
import pickle
import faiss
import torch
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)

MODELS = Path("data/models")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ── 1. Build compressed FAISS index ───────────────────────────────────────

def build_faiss_index(cf_model, n_movies):
    """
    Build IVFPQ compressed FAISS index from Two-Tower movie embeddings.
    IVFPQ = Inverted File Index + Product Quantization
    - IVF partitions space into clusters for fast search
    - PQ compresses each vector from float32 → compact codes
    - Result: 70-90% memory reduction vs flat index
    """
    log.info("Extracting movie embeddings from Two-Tower model...")
    cf_model.eval()

    batch_size     = 512
    all_embeddings = []

    with torch.no_grad():
        for start in range(0, n_movies, batch_size):
            end    = min(start + batch_size, n_movies)
            ids    = torch.arange(start, end, dtype=torch.long).to(DEVICE)
            embeds = cf_model.forward_movie(ids).cpu().numpy()
            all_embeddings.append(embeds)

    # Stack and convert to float16 for compression, then back to float32 for FAISS
    movie_embeddings = np.vstack(all_embeddings)
    movie_embeddings = movie_embeddings.astype(np.float16).astype(np.float32)
    log.info(f"Movie embeddings shape: {movie_embeddings.shape}")

    # L2 normalize for cosine similarity
    faiss.normalize_L2(movie_embeddings)

    dim        = movie_embeddings.shape[1]   # 64
    n_vectors  = movie_embeddings.shape[0]   # ~10669

    # IVFPQ parameters
    n_clusters = min(64, n_vectors // 10)    # number of IVF cells
    m          = 8                           # number of sub-quantizers
    # m must divide dim evenly: 64 / 8 = 8 ✅
    nbits      = 8                           # bits per sub-quantizer (256 centroids)

    log.info(f"Building IVFPQ index | dim={dim} clusters={n_clusters} "
             f"m={m} nbits={nbits}...")

    quantizer = faiss.IndexFlatIP(dim)
    index     = faiss.IndexIVFPQ(
        quantizer, dim, n_clusters, m, nbits,
        faiss.METRIC_INNER_PRODUCT
    )

    log.info("Training IVFPQ index...")
    index.train(movie_embeddings)
    index.add(movie_embeddings)
    index.nprobe = 16   # search 16 clusters per query

    log.info(f"IVFPQ index built | {index.ntotal} vectors | "
             f"estimated size: ~{index.ntotal * m * nbits // 8 / 1e6:.1f} MB")

    return index


def save_faiss_index(index):
    path = str(MODELS / "faiss_index.bin")
    faiss.write_index(index, path)
    size = Path(path).stat().st_size / 1e6
    log.info(f"FAISS index saved → {path} ({size:.1f} MB)")


def load_faiss_index():
    """Load only the FAISS index — no raw embeddings needed."""
    path  = str(MODELS / "faiss_index.bin")
    index = faiss.read_index(path)
    index.nprobe = 16
    log.info(f"FAISS index loaded | {index.ntotal} vectors")
    return index


# ── 2. Get candidates ──────────────────────────────────────────────────────

def get_faiss_candidates(cf_model, user_idx, faiss_index,
                         n_candidates=500, seen_movie_idxs=None):
    """
    Two-Tower user embedding → FAISS ANN search → candidate movie indices.
    No raw embedding matrix needed at query time.
    """
    cf_model.eval()

    with torch.no_grad():
        u_tensor = torch.tensor([user_idx], dtype=torch.long).to(DEVICE)
        u_vec    = cf_model.forward_user(u_tensor).cpu().numpy().astype(np.float32)

    faiss.normalize_L2(u_vec)

    fetch_k      = min(n_candidates * 2, faiss_index.ntotal)
    scores, idxs = faiss_index.search(u_vec, fetch_k)

    candidates = idxs[0]
    scores     = scores[0]

    # Remove invalid indices (-1 means not found)
    valid      = candidates >= 0
    candidates = candidates[valid]
    scores     = scores[valid]

    # Filter seen
    if seen_movie_idxs is not None and len(seen_movie_idxs) > 0:
        seen_set   = set(seen_movie_idxs.tolist())
        mask       = np.array([i not in seen_set for i in candidates])
        candidates = candidates[mask]
        scores     = scores[mask]

    return candidates[:n_candidates], scores[:n_candidates]


# ── Main: rebuild and save index ───────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from cf.cf_engine import TwoTowerNCF

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

    index = build_faiss_index(model, cf_config["n_movies"])
    save_faiss_index(index)

    # Verify it loads and searches correctly
    log.info("Verifying index...")
    test_index = load_faiss_index()
    test_vec   = np.random.randn(1, cf_config["embed_dim"]).astype(np.float32)
    faiss.normalize_L2(test_vec)
    _, test_ids = test_index.search(test_vec, 5)
    log.info(f"Test search result: {test_ids[0]}")
    log.info("✅ FAISS IVFPQ index complete.")
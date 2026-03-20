import sys
import pickle
import logging
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import scipy.sparse as sp
import torch

warnings.filterwarnings("ignore", category=RuntimeWarning)

sys.path.insert(0, str(Path(__file__).parent))

from cf.cf_engine import TwoTowerNCF, get_cf_scores
from cbf.cbf_engine import get_cbf_scores
from emotional.emotional_engine import get_emotional_scores, MOOD_TO_ARCS
from context.context_engine import get_context_score
from faiss_index.faiss_engine import load_faiss_index, get_faiss_candidates

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)

PROCESSED = Path("data/processed")
MODELS    = Path("data/models")
DEVICE    = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class plottwistScorer:

    def __init__(self):
        log.info("Loading all engine artifacts...")

        # ── CF ─────────────────────────────────────────────────────────────
        with open(MODELS / "cf_config.pkl", "rb") as f:
            cf_config = pickle.load(f)

        self.cf_n_movies = cf_config["n_movies"]
        self.cf_n_users  = cf_config["n_users"]

        self.cf_model = TwoTowerNCF(
            n_users     = cf_config["n_users"],
            n_movies    = cf_config["n_movies"],
            embed_dim   = cf_config["embed_dim"],
            hidden_dims = cf_config["hidden_dims"],
        ).to(DEVICE)
        self.cf_model.load_state_dict(
            torch.load(MODELS / "cf_model_best.pt", map_location=DEVICE))
        self.cf_model.eval()
        log.info("✅ CF model loaded")

        # ── FAISS IVFPQ index — no raw embeddings loaded ───────────────────
        if (MODELS / "faiss_index.bin").exists():
            self.faiss_index = load_faiss_index()
            self.use_faiss   = True
            log.info("✅ FAISS index loaded")
        else:
            self.faiss_index = None
            self.use_faiss   = False
            log.info("ℹ️  FAISS index not found — using brute force scoring")

        # ── CBF — sparse TF-IDF only, no semantic embeddings ──────────────
        if (MODELS / "tfidf_sparse.npz").exists():
            tfidf_sparse     = sp.load_npz(MODELS / "tfidf_sparse.npz")
            self.tfidf_dense = np.array(tfidf_sparse.todense(), dtype=np.float32)
            log.info("✅ CBF TF-IDF loaded (sparse → dense)")
        else:
            self.tfidf_dense = np.load(MODELS / "tfidf_dense.npy")
            log.info("✅ CBF TF-IDF loaded (dense)")

        # No semantic embeddings — FAISS handles semantic retrieval
        self.semantic_embeddings = None
        log.info("ℹ️  Semantic embeddings skipped — FAISS handles semantic search")

        # ── Emotional arc ──────────────────────────────────────────────────
        self.arc_df = pd.read_csv(PROCESSED / "movie_arcs.csv")
        log.info("✅ Emotional arc data loaded")

        # ── Seen index ────────────────────────────────────────────────────
        train_path = PROCESSED / "train_slim.parquet"
        if not train_path.exists():
            train_path = PROCESSED / "train_slim.csv"
        if not train_path.exists():
            train_path = PROCESSED / "train.csv"

        if (MODELS / "seen_index.pkl").exists():
            with open(MODELS / "seen_index.pkl", "rb") as f:
                self.seen_index = pickle.load(f)
            
            # Read header to check columns
            if train_path.suffix == ".parquet":
                import pyarrow.parquet as pq
                available_cols = pq.read_schema(train_path).names
                use_cols = ["user_idx", "movie_idx", "rating"]
                if "timestamp" in available_cols:
                    use_cols.append("timestamp")
                self.train_df = pd.read_parquet(train_path, columns=use_cols)
            else:
                available_cols = pd.read_csv(train_path, nrows=0).columns.tolist()
                use_cols = ["user_idx", "movie_idx", "rating"]
                if "timestamp" in available_cols:
                    use_cols.append("timestamp")
                self.train_df = pd.read_csv(train_path, usecols=use_cols)

            if "timestamp" not in self.train_df.columns:
                self.train_df["timestamp"] = datetime.now()

            log.info(f"✅ Seen index + {train_path.name} loaded")
        else:
            if train_path.suffix == ".parquet":
                self.train_df = pd.read_parquet(train_path)
            else:
                self.train_df = pd.read_csv(train_path)
            
            if "timestamp" not in self.train_df.columns:
                self.train_df["timestamp"] = datetime.now()

            self.seen_index = (
                self.train_df.groupby("user_idx")["movie_idx"]
                             .apply(list).to_dict()
            )
            log.info(f"✅ {train_path.name} loaded")

        # ── Load Core Data ────────────────────────────────────────────────
        self.movies_df = pd.read_csv(PROCESSED / "movies.csv")
        self.corpus_df = pd.read_csv(PROCESSED / "corpus.csv")
        self.movie_map = pd.read_csv(PROCESSED / "movie_map.csv")
        self.user_map  = pd.read_csv(PROCESSED / "user_map.csv")

        # ── REBUILD METADATA FROM SOURCE OF TRUTH ─────────────────────────
        # Bypasses the corrupted/shifted corpus.csv for user-facing info
        meta = self.movies_df[["movieId", "title_clean", "genres"]].copy()
        meta = meta.merge(self.movie_map, on="movieId", how="inner")
        
        links_path = PROCESSED / "links.csv"
        if links_path.exists():
            links_df = pd.read_csv(links_path, usecols=["movieId", "tmdbId"])
            links_df["tmdbId"] = pd.to_numeric(links_df["tmdbId"], errors="coerce").fillna(-1).astype(int)
            meta = meta.merge(links_df.rename(columns={"tmdbId": "tmdb_id"}), on="movieId", how="left")
        else:
            meta["tmdb_id"] = -1
            
        meta["tmdb_id"]   = meta["tmdb_id"].fillna(-1).astype(int)
        meta["movie_idx"] = meta["movie_idx"].astype(int)
        self.metadata_df  = meta.sort_values("movie_idx").reset_index(drop=True)

        # ── Align corpus for scoring ─────────────────────────────────────
        # We only need corpus content for TF-IDF/FAISS, but row order MUST match movie_idx
        if "movie_idx" in self.corpus_df.columns:
            self.corpus_df = self.corpus_df.drop(columns=["movie_idx"])
        if "tmdb_id" in self.corpus_df.columns:
            self.corpus_df = self.corpus_df.drop(columns=["tmdb_id"])
            
        self.corpus_df = self.corpus_df.merge(self.movie_map, on="movieId", how="inner")
        self.corpus_df = self.corpus_df.sort_values("movie_idx").reset_index(drop=True)

        log.info(f"✅ Data loaded | Metadata built for {len(self.metadata_df):,} movies")

        # ── Canonical movie count ──────────────────────────────────────────
        self.n_movies = max(
            self.cf_n_movies,
            len(self.tfidf_dense),
            int(self.arc_df["movie_idx"].max()) + 1,
        )
        log.info(f"Canonical n_movies: {self.n_movies}")
        log.info("plottwist Scorer ready.")


    # ── Helpers ────────────────────────────────────────────────────────────

    def _pad(self, arr, target_size):
        arr = np.array(arr, dtype=float)
        if len(arr) >= target_size:
            return arr[:target_size]
        padded = np.zeros(target_size)
        padded[:len(arr)] = arr
        return padded

    def _minmax(self, arr):
        arr  = np.array(arr, dtype=float)
        mask = arr != -np.inf
        if mask.sum() == 0:
            return arr
        mn, mx = arr[mask].min(), arr[mask].max()
        arr[mask] = (arr[mask] - mn) / (mx - mn + 1e-8)
        return arr

    def _minmax_safe(self, arr):
        if arr is None:
            return np.zeros(self.n_movies)
        return self._minmax(self._pad(arr, self.n_movies))

    def get_seen(self, user_idx):
        return np.array(self.seen_index.get(int(user_idx), []), dtype=np.int64)

    def is_cold_start(self, user_idx, min_ratings=5):
        return len(self.seen_index.get(int(user_idx), [])) < min_ratings

    def _get_cf_scores_for_candidates(self, user_idx, candidates):
        """Score only FAISS candidate movies."""
        self.cf_model.eval()
        with torch.no_grad():
            u_tensor = torch.tensor([user_idx], dtype=torch.long).to(DEVICE)
            u_vec    = self.cf_model.forward_user(u_tensor)
            c_tensor = torch.tensor(candidates, dtype=torch.long).to(DEVICE)
            m_vecs   = self.cf_model.forward_movie(c_tensor)
            scores   = (u_vec * m_vecs).sum(dim=-1).cpu().numpy()
        return scores


    # ── Per-user score computation ─────────────────────────────────────────

    def _score_user(self, user_idx, mood, w_cf, w_cbf, w_emotional,
                    mask_seen=True):
        seen = self.get_seen(user_idx)

        # Cold start — boost CBF
        if self.is_cold_start(user_idx):
            w_cf, w_cbf = 0.15, 0.55

        # ── Stage 1: FAISS candidate retrieval ─────────────────────────────
        if self.use_faiss:
            valid_seen_cf  = seen[seen < self.cf_n_movies] if mask_seen else None
            candidates, _  = get_faiss_candidates(
                self.cf_model, user_idx, self.faiss_index,
                n_candidates    = 500,
                seen_movie_idxs = valid_seen_cf,
            )
            cf_raw             = np.full(self.n_movies, -np.inf)
            candidate_scores   = self._get_cf_scores_for_candidates(
                user_idx, candidates)
            cf_raw[candidates] = candidate_scores
        else:
            valid_seen_cf = seen[seen < self.cf_n_movies] if mask_seen else None
            cf_raw        = get_cf_scores(
                self.cf_model, user_idx, self.cf_n_movies,
                seen_movie_idxs=valid_seen_cf,
            )

        cf_scores = self._minmax(self._pad(cf_raw, self.n_movies))

        # ── CBF — TF-IDF only ──────────────────────────────────────────────
        cbf_raw    = get_cbf_scores(
            user_idx, self.train_df,
            self.tfidf_dense,
            semantic_embeddings=None,
            seen_movie_idxs=seen if mask_seen else None,
        )
        cbf_scores = self._minmax_safe(cbf_raw)

        # ── Emotional ──────────────────────────────────────────────────────
        if mood:
            emo_raw    = get_emotional_scores(
                user_idx, mood, self.train_df, self.arc_df,
                seen_movie_idxs=seen if mask_seen else None,
            )
            emo_scores = self._minmax_safe(emo_raw)
        else:
            emo_scores  = np.zeros(self.n_movies)
            w_emotional = 0.0
            w_cf       += 0.20

        # ── Blend ──────────────────────────────────────────────────────────
        scores = w_cf * cf_scores + w_cbf * cbf_scores + w_emotional * emo_scores

        # Mask seen
        if mask_seen and len(seen) > 0:
            valid_seen = seen[seen < self.n_movies]
            scores[valid_seen] = -np.inf

        return scores


    # ── Family mode ────────────────────────────────────────────────────────

    def _family_mode(self, watch_group, mood, w_cf, w_cbf, w_emotional):
        log.info(f"Family mode | group size: {len(watch_group)}")
        member_scores = []

        for member_idx in watch_group:
            scores = self._score_user(
                member_idx, mood, w_cf, w_cbf, w_emotional,
                mask_seen=False,
            )
            member_scores.append(scores)

        stack       = np.stack(member_scores, axis=0)
        min_scores  = stack.min(axis=0)
        mean_scores = stack.mean(axis=0)

        combined_seen = np.concatenate([self.get_seen(u) for u in watch_group])
        valid_seen    = combined_seen[combined_seen < self.n_movies]
        min_scores[valid_seen]  = -np.inf
        mean_scores[valid_seen] = -np.inf

        return 0.5 * min_scores + 0.5 * mean_scores


    # ── Context multiplier ─────────────────────────────────────────────────

    def _apply_context(self, scores, timestamp):
        multiplier = get_context_score(timestamp)
        if multiplier == 1.0:
            return scores

        hour       = timestamp.hour
        is_weekend = timestamp.weekday() >= 5

        if hour >= 21 or hour < 6:
            boost_genres = ["thriller", "horror", "noir", "crime"]
        elif is_weekend:
            boost_genres = ["drama", "adventure", "sci fi"]
        else:
            boost_genres = ["comedy", "animation", "romance"]

        # Vectorized boost
        boosted = scores.copy()
        
        # Pre-filter corpus_df to movies that match any boost_genres
        # Note: corpus_df row index corresponds to predicted score indices
        mask = self.corpus_df["genres_clean"].str.contains("|".join(boost_genres), case=False, na=False)
        boost_indices = self.corpus_df[mask].index.values
        
        # Limit to valid indices in boosted array
        boost_indices = boost_indices[boost_indices < len(boosted)]
        
        boosted[boost_indices] *= multiplier
        return boosted


    # ── Format results ─────────────────────────────────────────────────────

    def _format_results(self, top_k_idx, scores):
        results = []
        for rank, movie_idx_int in enumerate(top_k_idx, 1):
            movie_idx_int = int(movie_idx_int)
            if movie_idx_int >= len(self.corpus_df):
                continue
                
            movie_row = self.metadata_df.iloc[movie_idx_int]
            
            arc_row = self.arc_df[self.arc_df["movie_idx"] == movie_idx_int]
            arc     = arc_row["primary_arc"].values[0] \
                      if not arc_row.empty else "unknown"
            
            # Clean genres: replace | with space for frontend
            genres_clean = str(movie_row["genres"]).replace("|", " ")

            results.append({
                "rank"      : rank,
                "movie_idx" : movie_idx_int,
                "tmdb_id"   : int(movie_row["tmdb_id"]),
                "title"     : movie_row["title_clean"],
                "genres"    : genres_clean,
                "arc"       : arc,
                "score"     : round(float(scores[movie_idx_int]), 4),
            })
        return results


    # ── Main recommend ─────────────────────────────────────────────────────

    def recommend(
        self,
        user_idx,
        mood        = None,
        timestamp   = None,
        watch_group = None,
        top_k       = 10,
        w_cf        = 0.50,
        w_cbf       = 0.20,
        w_emotional = 0.20,
    ):
        timestamp = timestamp or datetime.now()

        if watch_group and len(watch_group) > 1:
            final_scores = self._family_mode(
                watch_group, mood, w_cf, w_cbf, w_emotional)
        else:
            final_scores = self._score_user(
                user_idx, mood, w_cf, w_cbf, w_emotional, mask_seen=True)

        final_scores = self._apply_context(final_scores, timestamp)
        top_k_idx    = np.argsort(final_scores)[::-1][:top_k]
        return self._format_results(top_k_idx, final_scores)

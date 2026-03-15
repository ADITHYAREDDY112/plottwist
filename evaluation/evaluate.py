import sys
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
import logging

sys.path.insert(0, str(Path(__file__).parent.parent / "engines"))
from scorer import plottwistScorer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)

PROCESSED = Path("data/processed")
RESULTS   = Path("evaluation")
RESULTS.mkdir(exist_ok=True)


# ── Metrics ────────────────────────────────────────────────────────────────

def precision_at_k(recommended, relevant, k):
    rec = recommended[:k]
    return len(set(rec) & relevant) / k

def recall_at_k(recommended, relevant, k):
    if not relevant: return 0.0
    rec = recommended[:k]
    return len(set(rec) & relevant) / len(relevant)

def ndcg_at_k(recommended, relevant, k):
    rec  = recommended[:k]
    dcg  = sum(1 / np.log2(i + 2)
               for i, m in enumerate(rec) if m in relevant)
    idcg = sum(1 / np.log2(i + 2)
               for i in range(min(len(relevant), k)))
    return dcg / idcg if idcg > 0 else 0.0

def hit_rate_at_k(recommended, relevant, k):
    return 1.0 if set(recommended[:k]) & relevant else 0.0


# ── Evaluate one engine ────────────────────────────────────────────────────

def evaluate_engine(
    scorer,
    engine       : str,
    test_df      : pd.DataFrame,
    train_df     : pd.DataFrame,
    k_values     : list = [5, 10, 20],
    n_users      : int  = 500,
    mood         : str  = None,
):
    """
    Evaluate a specific engine configuration on test set.
    engine: 'cf_only' | 'cbf_only' | 'hybrid' | 'hybrid_mood'
    """
    log.info(f"Evaluating engine='{engine}' mood='{mood}' on {n_users} users...")

    # Build ground truth from test set
    positives   = test_df[test_df["rating"] >= 3.5]
    user_pos    = positives.groupby("user_idx")["movie_idx"].apply(set).to_dict()

    # Sample users that appear in both train and test
    train_users = set(train_df["user_idx"].unique())
    test_users  = [u for u in user_pos if u in train_users]
    np.random.shuffle(test_users)
    test_users  = test_users[:n_users]

    # Engine weight configs
    weight_configs = {
        "cf_only"     : dict(w_cf=1.0,  w_cbf=0.0,  w_emotional=0.0),
        "cbf_only"    : dict(w_cf=0.0,  w_cbf=1.0,  w_emotional=0.0),
        "hybrid"      : dict(w_cf=0.50, w_cbf=0.20, w_emotional=0.0),
        "hybrid_mood" : dict(w_cf=0.50, w_cbf=0.20, w_emotional=0.20),
    }
    weights = weight_configs.get(engine, weight_configs["hybrid"])

    metrics = defaultdict(list)

    for user_idx in test_users:
        true_pos = user_pos.get(user_idx, set())
        if not true_pos:
            continue

        try:
            results = scorer.recommend(
                user_idx    = user_idx,
                mood        = mood,
                top_k       = max(k_values),
                **weights,
            )
        except Exception as e:
            log.warning(f"Scorer error for user {user_idx}: {e}")
            continue

        recommended = [r["movie_idx"] for r in results]

        for k in k_values:
            metrics[f"P@{k}"].append(
                precision_at_k(recommended, true_pos, k))
            metrics[f"R@{k}"].append(
                recall_at_k(recommended, true_pos, k))
            metrics[f"NDCG@{k}"].append(
                ndcg_at_k(recommended, true_pos, k))
            metrics[f"HR@{k}"].append(
                hit_rate_at_k(recommended, true_pos, k))

    # Average metrics
    results_dict = {
        "engine": engine,
        "mood"  : mood or "none",
        "n_users_evaluated": len(test_users),
    }
    for metric, values in metrics.items():
        results_dict[metric] = round(np.mean(values), 4)

    return results_dict


# ── Coverage metric ────────────────────────────────────────────────────────

def catalog_coverage(scorer, n_users=200, k=10):
    """
    What % of the catalog does the system actually recommend?
    Low coverage = popularity bias problem.
    """
    log.info(f"Computing catalog coverage on {n_users} users...")
    all_recommended = set()
    sample_users    = np.random.choice(scorer.cf_n_users, n_users, replace=False)

    for user_idx in sample_users:
        try:
            results = scorer.recommend(user_idx=int(user_idx), top_k=k)
            all_recommended.update(r["movie_idx"] for r in results)
        except: continue

    coverage = len(all_recommended) / scorer.n_movies
    log.info(f"Catalog coverage: {len(all_recommended)} / "
             f"{scorer.n_movies} = {coverage:.4f}")
    return round(coverage, 4)


# ── Diversity metric ───────────────────────────────────────────────────────

def intra_list_diversity(scorer, n_users=200, k=10):
    """
    Average pairwise genre distance within recommendation lists.
    Higher = more diverse recommendations.
    """
    log.info(f"Computing intra-list diversity on {n_users} users...")
    diversities  = []
    sample_users = np.random.choice(scorer.cf_n_users, n_users, replace=False)

    for user_idx in sample_users:
        try:
            results = scorer.recommend(user_idx=int(user_idx), top_k=k)
        except: continue

        arcs = [r["arc"] for r in results]
        if len(arcs) < 2: continue

        # Count unique arcs — higher = more diverse
        unique_arcs = len(set(arcs))
        diversities.append(unique_arcs / len(arcs))

    avg = round(np.mean(diversities), 4) if diversities else 0.0
    log.info(f"Intra-list diversity (arc): {avg}")
    return avg


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Loading scorer...")
    scorer   = plottwistScorer()
    test_df  = pd.read_csv(PROCESSED / "test.csv")
    train_df = pd.read_csv(PROCESSED / "train.csv")

    log.info("=" * 60)
    log.info("PlotTwist Recommendation System — Offline Evaluation")
    log.info("=" * 60)

    # Evaluate all engine configs
    configs = [
        ("cf_only",      None),
        ("cbf_only",     None),
        ("hybrid",       None),
        ("hybrid_mood",  "excited"),
        ("hybrid_mood",  "sad"),
        ("hybrid_mood",  "bored"),
    ]

    all_results = []
    for engine, mood in configs:
        result = evaluate_engine(
            scorer, engine, test_df, train_df,
            k_values=[5, 10, 20], n_users=300, mood=mood,
        )
        all_results.append(result)

        # Print nicely
        log.info(f"\n── {engine.upper()} | mood={result['mood']} ──")
        for k in [5, 10, 20]:
            log.info(f"  P@{k}={result[f'P@{k}']:.4f} | "
                     f"R@{k}={result[f'R@{k}']:.4f} | "
                     f"NDCG@{k}={result[f'NDCG@{k}']:.4f} | "
                     f"HR@{k}={result[f'HR@{k}']:.4f}")

    # System-level metrics
    log.info("\n── SYSTEM METRICS ──")
    coverage  = catalog_coverage(scorer,          n_users=200, k=10)
    diversity = intra_list_diversity(scorer,       n_users=200, k=10)
    log.info(f"  Catalog Coverage:       {coverage:.4f} "
             f"({coverage*100:.1f}% of {scorer.n_movies} movies)")
    log.info(f"  Intra-List Diversity:   {diversity:.4f}")

    # Save results to CSV
    results_df = pd.DataFrame(all_results)
    results_df.to_csv(RESULTS / "eval_results.csv", index=False)
    log.info(f"\nResults saved → evaluation/eval_results.csv")

    # Print summary table
    log.info("\n" + "=" * 60)
    log.info("SUMMARY TABLE")
    log.info("=" * 60)
    print(results_df[[
        "engine", "mood", "P@10", "R@10", "NDCG@10", "HR@10"
    ]].to_string(index=False))
    log.info("=" * 60)
    log.info("✅ Evaluation complete.")
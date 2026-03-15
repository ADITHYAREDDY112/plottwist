import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
import pickle
import logging
from tqdm import tqdm
import scipy.sparse as sp

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = logging.getLogger(__name__)

PROCESSED = Path("data/processed")
MODELS    = Path("data/models")
MODELS.mkdir(parents=True, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
log.info(f"Using device: {DEVICE}")


# ── 1. Dataset ─────────────────────────────────────────────────────────────

class BPRDataset(Dataset):
    """
    Bayesian Personalised Ranking dataset.
    For each (user, positive_movie), samples a random negative_movie.
    Teaches the model: score(user, positive) > score(user, negative)
    """
    def __init__(self, df, n_movies, rating_threshold=3.5, neg_per_pos=1):
        positives = df[df["rating"] >= rating_threshold]

        self.users     = positives["user_idx"].values.astype(np.int64)
        self.pos_items = positives["movie_idx"].values.astype(np.int64)
        self.n_movies  = n_movies
        self.neg_per_pos = neg_per_pos

        # Build set of seen movies per user for negative sampling
        log.info("Building seen-items index for negative sampling...")
        self.seen = (
            df.groupby("user_idx")["movie_idx"]
              .apply(set)
              .to_dict()
        )

    def __len__(self):
        return len(self.users) * self.neg_per_pos

    def __getitem__(self, idx):
        real_idx = idx % len(self.users)
        user     = self.users[real_idx]
        pos      = self.pos_items[real_idx]

        # Sample a negative movie the user hasn't seen
        seen = self.seen.get(user, set())
        while True:
            neg = np.random.randint(0, self.n_movies)
            if neg not in seen:
                break

        return (
            torch.tensor(user, dtype=torch.long),
            torch.tensor(pos,  dtype=torch.long),
            torch.tensor(neg,  dtype=torch.long),
        )


# ── 2. Two-Tower Neural CF Model ───────────────────────────────────────────

class TwoTowerNCF(nn.Module):
    """
    Two-Tower architecture:
      - User tower: embedding → MLP → user_vec
      - Movie tower: embedding → MLP → movie_vec
      - Score = dot(user_vec, movie_vec)

    Same architecture used by YouTube & Pinterest at scale.
    """
    def __init__(self, n_users, n_movies, embed_dim=64, hidden_dims=[128, 64]):
        super().__init__()

        # Embeddings
        self.user_embedding  = nn.Embedding(n_users,  embed_dim, sparse=False)
        self.movie_embedding = nn.Embedding(n_movies, embed_dim, sparse=False)

        # User tower MLP
        user_layers = []
        in_dim = embed_dim
        for h in hidden_dims:
            user_layers += [nn.Linear(in_dim, h), nn.ReLU(), nn.Dropout(0.2)]
            in_dim = h
        user_layers.append(nn.Linear(in_dim, embed_dim))
        self.user_tower = nn.Sequential(*user_layers)

        # Movie tower MLP
        movie_layers = []
        in_dim = embed_dim
        for h in hidden_dims:
            movie_layers += [nn.Linear(in_dim, h), nn.ReLU(), nn.Dropout(0.2)]
            in_dim = h
        movie_layers.append(nn.Linear(in_dim, embed_dim))
        self.movie_tower = nn.Sequential(*movie_layers)

        # Weight init
        nn.init.normal_(self.user_embedding.weight,  std=0.01)
        nn.init.normal_(self.movie_embedding.weight, std=0.01)

    def forward_user(self, user_ids):
        return self.user_tower(self.user_embedding(user_ids))

    def forward_movie(self, movie_ids):
        return self.movie_tower(self.movie_embedding(movie_ids))

    def forward(self, user_ids, movie_ids):
        u = self.forward_user(user_ids)
        m = self.forward_movie(movie_ids)
        return (u * m).sum(dim=-1)   # dot product → scalar score


# ── 3. BPR Loss ────────────────────────────────────────────────────────────

def bpr_loss(pos_scores, neg_scores):
    """
    BPR: maximise P(pos > neg) = sigmoid(pos_score - neg_score)
    Loss = -mean(log(sigmoid(pos - neg)))
    """
    return -torch.log(torch.sigmoid(pos_scores - neg_scores) + 1e-8).mean()


# ── 4. Train ───────────────────────────────────────────────────────────────

def train(train_df, val_df, n_users, n_movies,
          embed_dim=64, epochs=10, batch_size=4096, lr=1e-3):

    log.info(f"Building datasets...")
    train_ds = BPRDataset(train_df, n_movies)
    train_dl = DataLoader(
    train_ds,
    batch_size  = batch_size,
    shuffle     = True,
    num_workers = 0,   # Windows fix — no subprocess workers
    pin_memory  = False,
)

    model = TwoTowerNCF(n_users, n_movies, embed_dim=embed_dim).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-6)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.5)

    log.info(f"Model params: {sum(p.numel() for p in model.parameters()):,}")
    log.info(f"Training | epochs={epochs} | batch={batch_size} | device={DEVICE}")

    best_loss  = float("inf")
    best_state = None

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0
        batches    = 0

        pbar = tqdm(train_dl, desc=f"Epoch {epoch}/{epochs}", leave=False)
        for users, pos_items, neg_items in pbar:
            users     = users.to(DEVICE)
            pos_items = pos_items.to(DEVICE)
            neg_items = neg_items.to(DEVICE)

            pos_scores = model(users, pos_items)
            neg_scores = model(users, neg_items)
            loss = bpr_loss(pos_scores, neg_scores)

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            total_loss += loss.item()
            batches    += 1
            pbar.set_postfix(loss=f"{loss.item():.4f}")

        avg_loss = total_loss / batches
        scheduler.step()

        # Validation: sample-based P@10
        p_at_10 = evaluate_precision(model, val_df, n_movies, k=10, n_sample=2000)
        log.info(f"Epoch {epoch:>2} | Loss={avg_loss:.4f} | P@10={p_at_10:.4f} "
                 f"| LR={scheduler.get_last_lr()[0]:.5f}")

        if avg_loss < best_loss:
            best_loss  = avg_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            torch.save(best_state, MODELS / "cf_model_best.pt")

    # Restore best weights
    model.load_state_dict({k: v.to(DEVICE) for k, v in best_state.items()})
    log.info(f"Best loss: {best_loss:.4f}")
    return model


# ── 5. Evaluation ──────────────────────────────────────────────────────────

def evaluate_precision(model, val_df, n_movies, k=10, n_sample=2000):
    """
    Sample-based Precision@K on val set.
    Samples n_sample users for speed.
    """
    model.eval()
    positives = val_df[val_df["rating"] >= 3.5]
    user_pos  = positives.groupby("user_idx")["movie_idx"].apply(set).to_dict()
    sampled   = list(user_pos.keys())
    np.random.shuffle(sampled)
    sampled   = sampled[:n_sample]

    hits = 0
    total = 0

    with torch.no_grad():
        for user_idx in sampled:
            if user_idx not in user_pos:
                continue
            true_pos = user_pos[user_idx]

            u_tensor = torch.tensor([user_idx], dtype=torch.long).to(DEVICE)
            u_vec    = model.forward_user(u_tensor)   # (1, embed_dim)

            all_movies = torch.arange(n_movies, dtype=torch.long).to(DEVICE)
            m_vecs     = model.forward_movie(all_movies)  # (n_movies, embed_dim)

            scores = (u_vec * m_vecs).sum(dim=-1).cpu().numpy()
            top_k  = np.argsort(scores)[::-1][:k]

            hits  += len(set(top_k) & true_pos)
            total += k

    return hits / total if total > 0 else 0.0


# ── 6. Get CF scores for one user ─────────────────────────────────────────

def get_cf_scores(model, user_idx, n_movies, seen_movie_idxs=None):
    """
    Returns score array of shape (n_movies,) for a given user.
    Masks out seen movies with -inf.
    """
    model.eval()
    with torch.no_grad():
        u_tensor   = torch.tensor([user_idx], dtype=torch.long).to(DEVICE)
        u_vec      = model.forward_user(u_tensor)
        all_movies = torch.arange(n_movies, dtype=torch.long).to(DEVICE)
        m_vecs     = model.forward_movie(all_movies)
        scores     = (u_vec * m_vecs).sum(dim=-1).cpu().numpy()

    if seen_movie_idxs is not None:
        scores[seen_movie_idxs] = -np.inf

    return scores


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Loading processed data...")
    train_df = pd.read_csv(PROCESSED / "train.csv")
    val_df   = pd.read_csv(PROCESSED / "val.csv")

    n_users  = int(train_df["user_idx"].max() + 1)
    n_movies = int(train_df["movie_idx"].max() + 1)
    log.info(f"Matrix: {n_users:,} users × {n_movies:,} movies")

    pd.DataFrame({"n_users": [n_users], "n_movies": [n_movies]}).to_csv(
        PROCESSED / "matrix_shape.csv", index=False)

    model = train(train_df, val_df, n_users, n_movies,
              embed_dim=64, epochs=10, batch_size=2048)

    torch.save(model.state_dict(), MODELS / "cf_model_final.pt")

    # Save model config for loading later
    config = {"n_users": n_users, "n_movies": n_movies,
              "embed_dim": 64, "hidden_dims": [128, 64]}
    with open(MODELS / "cf_config.pkl", "wb") as f:
        pickle.dump(config, f)

    log.info("✅ CF engine complete.")
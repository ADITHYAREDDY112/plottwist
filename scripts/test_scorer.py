import sys
sys.path.insert(0, "engines")

from scorer import plottwist Scorer
from datetime import datetime

scorer = plottwist Scorer()

# ── Test 1: Single user, mood=excited ─────────────────────────────────────
print("\n=== Single User | mood=excited ===")
results = scorer.recommend(
    user_idx  = 0,
    mood      = "excited",
    timestamp = datetime.now(),
    top_k     = 10,
)
for r in results:
    print(f"  {r['rank']:>2}. {r['title']:<45} | {r['genres']:<35} | arc={r['arc']}")

# ── Test 2: Family mode ────────────────────────────────────────────────────
print("\n=== Family Mode | group=[0,1,2] | mood=happy ===")
results = scorer.recommend(
    user_idx    = 0,
    mood        = "happy",
    watch_group = [0, 1, 2],
    top_k       = 10,
)
for r in results:
    print(f"  {r['rank']:>2}. {r['title']:<45} | {r['genres']:<35} | arc={r['arc']}")

# ── Test 3: Cold start user ────────────────────────────────────────────────
print("\n=== Cold Start User (idx=999) | no mood ===")
results = scorer.recommend(
    user_idx = 999,
    top_k    = 10,
)
for r in results:
    print(f"  {r['rank']:>2}. {r['title']:<45} | {r['genres']:<35} | arc={r['arc']}")
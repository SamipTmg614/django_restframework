

import numpy as np
import pandas as pd
from django.core.cache import cache
from base.models import OrderItem
CACHE_KEY_SIMILARITY = "item_similarity_matrix"
CACHE_KEY_ITEM_IDS = "item_similarity_item_ids"
CACHE_KEY_USER_IDS = "item_similarity_user_ids"
CACHE_KEY_MATRIX = "user_item_matrix"
CACHE_TIMEOUT_SECONDS = 60 * 60  


def build_user_item_matrix():
    """STEP 1: build R from raw OrderItem rows. Returns (R, user_ids, item_ids)."""
    qs = OrderItem.objects.all().values("order__user_id", "product_id", "quantity")
    df = pd.DataFrame(list(qs))
    if df.empty:
        return None, None, None

    df = df.groupby(["order__user_id", "product_id"], as_index=False)["quantity"].sum()
    R_df = df.pivot_table(
        index="order__user_id", columns="product_id", values="quantity", fill_value=0
    )
    R = R_df.to_numpy(dtype=float)
    return R, R_df.index.to_numpy(), R_df.columns.to_numpy()


def cosine_similarity_matrix(R):
    """STEP 2: item-item cosine similarity, same math as before."""
    item_norms = np.sqrt((R ** 2).sum(axis=0))
    item_norms[item_norms == 0] = 1e-10
    dot_products = R.T @ R
    norm_products = np.outer(item_norms, item_norms)
    return dot_products / norm_products


def predict_scores(user_vector, S):
    """STEP 3: similarity-weighted score for every item, given one user's purchases."""
    purchased_mask = user_vector > 0
    relevant_similarities = S[:, purchased_mask]
    relevant_quantities = user_vector[purchased_mask]

    numerator = relevant_similarities @ relevant_quantities
    denominator = np.abs(relevant_similarities).sum(axis=1)
    denominator[denominator == 0] = 1e-10
    return numerator / denominator


def get_or_build_similarity_matrix():
    """
    Returns (S, user_ids, item_ids), using Django's cache to avoid recomputing
    the full similarity matrix on every request. Numpy arrays aren't directly
    cacheable by default backends in all configurations, so we store them as
    lists and convert back — fine at this data scale.
    """
    S = cache.get(CACHE_KEY_SIMILARITY)
    user_ids = cache.get(CACHE_KEY_USER_IDS)
    item_ids = cache.get(CACHE_KEY_ITEM_IDS)

    if S is not None and user_ids is not None and item_ids is not None:
        return np.array(S), np.array(user_ids), np.array(item_ids)

    R, user_ids_arr, item_ids_arr = build_user_item_matrix()
    if R is None:
        return None, None, None

    S = cosine_similarity_matrix(R)

    cache.set(CACHE_KEY_SIMILARITY, S.tolist(), CACHE_TIMEOUT_SECONDS)
    cache.set(CACHE_KEY_USER_IDS, user_ids_arr.tolist(), CACHE_TIMEOUT_SECONDS)
    cache.set(CACHE_KEY_ITEM_IDS, item_ids_arr.tolist(), CACHE_TIMEOUT_SECONDS)
    # Cache R itself too, so we can look up any user's purchase vector without
    # re-querying the DB on every call.
    cache.set(CACHE_KEY_MATRIX, R.tolist(), CACHE_TIMEOUT_SECONDS)

    return S, user_ids_arr, item_ids_arr


def get_recommendations_for_user(user_id, top_n=5):

    S, user_ids, item_ids = get_or_build_similarity_matrix()
    if S is None or user_id not in user_ids:
        return None

    R = np.array(cache.get(CACHE_KEY_MATRIX))
    user_row_idx = np.where(user_ids == user_id)[0][0]
    user_vector = R[user_row_idx]

    scores = predict_scores(user_vector, S)

    already_purchased_mask = user_vector > 0
    scores[already_purchased_mask] = -np.inf

    top_indices = np.argsort(scores)[::-1][:top_n]

    return [
        {"item_id": int(item_ids[idx]), "score": float(scores[idx])}
        for idx in top_indices
    ]


def invalidate_similarity_cache():

    cache.delete(CACHE_KEY_SIMILARITY)
    cache.delete(CACHE_KEY_USER_IDS)
    cache.delete(CACHE_KEY_ITEM_IDS)
    cache.delete(CACHE_KEY_MATRIX)
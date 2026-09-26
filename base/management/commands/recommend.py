
import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand
from base.models import OrderItem, Item


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--user_id", type=int, required=True)
        parser.add_argument("--top_n", type=int, default=5)

    def handle(self, *args, **options):
        user_id = options["user_id"]
        top_n = options["top_n"]

        # ---- Load raw purchase data ----
        qs = OrderItem.objects.all().values(
            "order__user_id", "product_id", "quantity"
        )
        df = pd.DataFrame(list(qs))
        if df.empty:
            self.stdout.write(self.style.ERROR("No order data found. Run seed_data first."))
            return

        # Multiple line items for the same user+product across different orders
        # should be summed into one total purchase quantity.
        df = df.groupby(["order__user_id", "product_id"], as_index=False)["quantity"].sum()

        # ---- STEP 1: Build the user-item matrix R ----
        # Rows = users, columns = items, values = total quantity purchased.
        # Missing combinations (never purchased) become 0.
        R_df = df.pivot_table(
            index="order__user_id",
            columns="product_id",
            values="quantity",
            fill_value=0,
        )
        R = R_df.to_numpy(dtype=float)  # shape: (n_users, n_items)
        item_ids = R_df.columns.to_numpy()
        user_ids = R_df.index.to_numpy()

        self.stdout.write(f"User-item matrix shape: {R.shape[0]} users x {R.shape[1]} items")

        if user_id not in user_ids:
            self.stdout.write(self.style.ERROR(
                f"User {user_id} has no purchase history in this matrix."
            ))
            return

        # ---- STEP 2: Compute item-item cosine similarity, from scratch ----
        S = self._cosine_similarity_matrix(R)  # shape: (n_items, n_items)

        # ---- STEP 3 + 4: Score and rank candidate items for this user ----
        user_row_idx = np.where(user_ids == user_id)[0][0]
        user_vector = R[user_row_idx]  # this user's purchase quantities across all items

        scores = self._predict_scores(user_vector, S)

        # Exclude items the user has already purchased
        already_purchased_mask = user_vector > 0
        scores[already_purchased_mask] = -np.inf  # push already-owned items to the bottom

        top_indices = np.argsort(scores)[::-1][:top_n]
        recommended_item_ids = item_ids[top_indices]
        recommended_scores = scores[top_indices]

        # ---- Display results with item names ----
        items = {item.id: item.name for item in Item.objects.filter(id__in=recommended_item_ids)}

        self.stdout.write(self.style.SUCCESS(f"\nTop {top_n} recommendations for user {user_id}:\n"))
        for item_id, score in zip(recommended_item_ids, recommended_scores):
            name = items.get(int(item_id), f"item {item_id}")
            self.stdout.write(f"  score={score:.4f}   {name}")

        already_bought = [
            items_lookup for items_lookup in
            Item.objects.filter(id__in=item_ids[already_purchased_mask]).values_list("name", flat=True)
        ]
        self.stdout.write(f"\n(For reference, this user already purchased: {already_bought[:10]})")


    def _cosine_similarity_matrix(self, R):

        item_norms = np.sqrt((R ** 2).sum(axis=0))  # shape: (n_items,)

        item_norms[item_norms == 0] = 1e-10

        dot_products = R.T @ R  # shape: (n_items, n_items)


        norm_products = np.outer(item_norms, item_norms)

        S = dot_products / norm_products
        return S  # S[i][j] is the cosine similarity between item i and item j

    def _predict_scores(self, user_vector, S):

        # Which items has this user purchased? Only those contribute to the sum.
        purchased_mask = user_vector > 0


        relevant_similarities = S[:, purchased_mask]  # S[i][j] for purchased j only
        relevant_quantities = user_vector[purchased_mask]  # R[u][j] for purchased j only


        numerator = relevant_similarities @ relevant_quantities  # shape: (n_items,)

        denominator = np.abs(relevant_similarities).sum(axis=1)  # shape: (n_items,)
        denominator[denominator == 0] = 1e-10  # avoid division by zero

        scores = numerator / denominator
        return scores
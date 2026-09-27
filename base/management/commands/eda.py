"""

INSTALL DEPENDENCIES:
  pip install pandas matplotlib seaborn

RUN:
  python manage.py eda

OUTPUT:
  - Printed stats in the terminal
  - PNG charts saved to eda_output/ in your project root
"""

import os
from collections import Counter
from itertools import combinations

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # no display needed, just save files
import matplotlib.pyplot as plt
import seaborn as sns

from django.core.management.base import BaseCommand
from base.models import User, Item, Order, OrderItem 

OUTPUT_DIR = "eda_output"


class Command(BaseCommand):
    def handle(self, *args, **options):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        sns.set_theme(style="whitegrid")

        items_df = self._load_items()
        orders_df = self._load_orders()
        order_items_df = self._load_order_items()

        self.stdout.write(self.style.SUCCESS("\n=== BASIC COUNTS ===\n"))
        self._basic_counts(items_df, orders_df, order_items_df)

        self.stdout.write(self.style.SUCCESS("\n=== ITEM STATS ===\n"))
        self._item_stats(items_df)

        self.stdout.write(self.style.SUCCESS("\n=== ORDER STATS ===\n"))
        self._order_stats(orders_df, order_items_df)

        self.stdout.write(self.style.SUCCESS("\n=== ITEM POPULARITY ===\n"))
        self._item_popularity(order_items_df, items_df)

        self.stdout.write(self.style.SUCCESS("\n=== USER PURCHASE BEHAVIOR ===\n"))
        self._user_behavior(orders_df, order_items_df)

        self.stdout.write(self.style.SUCCESS("\n=== CO-PURCHASE VALIDATION (does clustering exist?) ===\n"))
        self._co_purchase_check(order_items_df, items_df)

        self.stdout.write(self.style.SUCCESS(f"\nCharts saved to ./{OUTPUT_DIR}/\n"))

    # ---------- Data loading ----------

    def _load_items(self):
        qs = Item.objects.all().values("id", "name", "price", "stock", "created")
        return pd.DataFrame(list(qs))

    def _load_orders(self):
        qs = Order.objects.all().values("order_id", "user_id", "created_at", "status")
        return pd.DataFrame(list(qs))

    def _load_order_items(self):
        qs = OrderItem.objects.all().values(
            "order_id", "product_id", "quantity",
            "product__price", "product__name", "order__user_id"
        )
        df = pd.DataFrame(list(qs))
        if not df.empty:
            df["line_total"] = df["quantity"] * df["product__price"].astype(float)
        return df

    # ---------- Analyses ----------

    def _basic_counts(self, items_df, orders_df, order_items_df):
        print(f"Users placing orders: {orders_df['user_id'].nunique() if not orders_df.empty else 0}")
        print(f"Items: {len(items_df)}")
        print(f"Orders: {len(orders_df)}")
        print(f"Order line items: {len(order_items_df)}")
        print(f"\nMissing values per table:")
        print("Items:\n", items_df.isnull().sum())
        print("Orders:\n", orders_df.isnull().sum())

    def _item_stats(self, items_df):
        print(items_df[["price", "stock"]].describe())
        out_of_stock = (items_df["stock"] == 0).sum()
        print(f"\nOut-of-stock items: {out_of_stock} ({out_of_stock / len(items_df):.1%})")

        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        sns.histplot(items_df["price"], bins=30, ax=axes[0])
        axes[0].set_title("Item Price Distribution")
        sns.histplot(items_df["stock"], bins=30, ax=axes[1])
        axes[1].set_title("Item Stock Distribution")
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/item_distributions.png")
        plt.close()

    def _order_stats(self, orders_df, order_items_df):
        print("Order status breakdown:")
        print(orders_df["status"].value_counts())

        items_per_order = order_items_df.groupby("order_id").size()
        print(f"\nItems per order — mean: {items_per_order.mean():.2f}, "
              f"median: {items_per_order.median()}, max: {items_per_order.max()}")

        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        orders_df["status"].value_counts().plot(kind="bar", ax=axes[0])
        axes[0].set_title("Order Status Breakdown")
        sns.histplot(items_per_order, bins=range(1, items_per_order.max() + 2), ax=axes[1])
        axes[1].set_title("Items per Order")
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/order_stats.png")
        plt.close()

    def _item_popularity(self, order_items_df, items_df):
        popularity = (
            order_items_df.groupby(["product_id", "product__name"])["quantity"]
            .sum()
            .reset_index()
            .sort_values("quantity", ascending=False)
        )
        print("Top 10 best-selling items:")
        print(popularity.head(10)[["product__name", "quantity"]].to_string(index=False))

        revenue = (
            order_items_df.groupby(["product_id", "product__name"])["line_total"]
            .sum()
            .reset_index()
            .sort_values("line_total", ascending=False)
        )
        print("\nTop 10 items by revenue:")
        print(revenue.head(10)[["product__name", "line_total"]].to_string(index=False))

        plt.figure(figsize=(10, 5))
        sns.barplot(data=popularity.head(15), x="quantity", y="product__name")
        plt.title("Top 15 Best-Selling Items")
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/item_popularity.png")
        plt.close()

    def _user_behavior(self, orders_df, order_items_df):
        orders_per_user = orders_df.groupby("user_id").size()
        print(f"Orders per user — mean: {orders_per_user.mean():.2f}, "
              f"median: {orders_per_user.median()}, max: {orders_per_user.max()}")

        spend_per_user = order_items_df.groupby("order__user_id")["line_total"].sum()
        print(f"\nSpend per user — mean: ${spend_per_user.mean():.2f}, "
              f"median: ${spend_per_user.median():.2f}, max: ${spend_per_user.max():.2f}")

        plt.figure(figsize=(8, 4))
        sns.histplot(orders_per_user, bins=range(1, int(orders_per_user.max()) + 2))
        plt.title("Orders per User")
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/orders_per_user.png")
        plt.close()

    def _co_purchase_check(self, order_items_df, items_df):

        pair_counts = Counter()
        for order_id, group in order_items_df.groupby("order_id"):
            product_ids = group["product_id"].tolist()
            for a, b in combinations(sorted(set(product_ids)), 2):
                pair_counts[(a, b)] += 1

        top_pairs = pair_counts.most_common(10)
        id_to_name = items_df.set_index("id")["name"].to_dict()

        print("Top 10 most frequently co-purchased item pairs:")
        for (a, b), count in top_pairs:
            name_a = id_to_name.get(a, f"item {a}")
            name_b = id_to_name.get(b, f"item {b}")
            print(f"  {count}x  {name_a}  <->  {name_b}")

        if not top_pairs or top_pairs[0][1] <= 2:
            print("\nWARNING: co-purchase counts look low/flat — clustering signal may be weak. "
                  "Consider re-running seed_data with more orders, or increasing the "
                  "'preferred theme' bias in the seed script.")
        else:
            print("\nClustering signal looks present — good foundation for collaborative filtering.")
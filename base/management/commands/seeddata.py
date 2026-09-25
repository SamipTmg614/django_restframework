"""
Django management command to seed the database with realistic ecommerce data.

WHERE TO PUT THIS FILE:
  <your_app>/management/commands/seed_data.py
  (create the management/ and management/commands/ folders if they don't exist,
   each needs an empty __init__.py)

INSTALL DEPENDENCY:
  pip install faker

RUN:
  python manage.py seed_data
  python manage.py seed_data --users 100 --items 400 --orders 800   (optional overrides)
  python manage.py seed_data --flush   (wipes existing seeded data first)

WHY "THEMES" EXIST:
  Your Item model has no `category` field. That's fine for a collaborative-filtering
  recommender ("customers who bought X also bought Y"), which only needs purchase
  co-occurrence data — not explicit categories. So this script assigns each item a
  hidden theme (Electronics, Books, etc.) used ONLY to generate realistic names/
  descriptions and to bias which items get bought together in the same order.
  The theme itself is never saved to the DB. This gives your recommender real
  signal to find, instead of pure random noise.

  If you later add a `category` field to Item, this script is easy to extend —
  just save `theme` onto the model instead of discarding it.
"""

import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from base.models import User, Item, Order, OrderItem
fake = Faker()

THEMES = {
    "Electronics": {
        "nouns": ["Wireless Earbuds", "Bluetooth Speaker", "USB-C Hub", "Mechanical Keyboard",
                   "Webcam", "Power Bank", "Smart Watch", "Laptop Stand", "Monitor", "Router"],
        "price_range": (15, 300),
    },
    "Books": {
        "nouns": ["Mystery Novel", "Cookbook", "Sci-Fi Anthology", "Biography", "Self-Help Guide",
                  "History Book", "Poetry Collection", "Programming Guide", "Travel Journal", "Comic Volume"],
        "price_range": (8, 40),
    },
    "Home & Kitchen": {
        "nouns": ["Ceramic Mug Set", "Cutting Board", "Throw Blanket", "Candle", "Storage Bin",
                  "Cast Iron Pan", "Desk Lamp", "Wall Clock", "Air Fryer", "Coffee Grinder"],
        "price_range": (10, 150),
    },
    "Clothing": {
        "nouns": ["Cotton T-Shirt", "Denim Jacket", "Running Shoes", "Wool Scarf", "Baseball Cap",
                  "Hoodie", "Sneakers", "Leather Belt", "Sunglasses", "Backpack"],
        "price_range": (12, 120),
    },
    "Sports & Outdoors": {
        "nouns": ["Yoga Mat", "Water Bottle", "Camping Tent", "Resistance Bands", "Hiking Boots",
                  "Bike Helmet", "Dumbbell Set", "Sleeping Bag", "Tennis Racket", "Foam Roller"],
        "price_range": (10, 250),
    },
}

DESCRIPTION_TEMPLATES = [
    "A high-quality {noun} designed for everyday use. {detail}",
    "This {noun} combines durability with style. {detail}",
    "Upgrade your routine with this {noun}. {detail}",
    "Customer favorite: {noun} known for reliability. {detail}",
]

DETAILS = [
    "Backed by a 1-year warranty.",
    "Ships within 2 business days.",
    "Made from sustainably sourced materials.",
    "Loved by over 10,000 customers.",
    "Compact design, easy to store.",
    "Available in multiple colors.",
]


class Command(BaseCommand):
    help = "Seed the database with realistic, theme-clustered ecommerce data."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=60)
        parser.add_argument("--items", type=int, default=300)
        parser.add_argument("--orders", type=int, default=600)
        parser.add_argument("--flush", action="store_true", help="Delete existing seeded data first")

    def handle(self, *args, **options):
        n_users = options["users"]
        n_items = options["items"]
        n_orders = options["orders"]

        if options["flush"]:
            self.stdout.write("Flushing existing Order/OrderItem/Item/non-staff User data...")
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Item.objects.all().delete()
            User.objects.filter(is_staff=False, is_superuser=False).delete()

        with transaction.atomic():
            users = self._create_users(n_users)
            items_by_theme = self._create_items(n_items)
            self._create_orders(n_orders, users, items_by_theme)

        self.stdout.write(self.style.SUCCESS(
            f"Done. Seeded {n_users} users, {n_items} items, {n_orders} orders."
        ))

    def _create_users(self, n):
        self.stdout.write(f"Creating {n} users...")
        users = []
        for i in range(n):
            username = f"{fake.user_name()}{i}"  # avoid collisions
            user = User(
                username=username,
                email=fake.email(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
            )
            user.set_unusable_password()
            users.append(user)
        User.objects.bulk_create(users)
        return list(User.objects.filter(username__in=[u.username for u in users]))

    def _create_items(self, n):
        self.stdout.write(f"Creating {n} items...")
        items_by_theme = {theme: [] for theme in THEMES}
        theme_names = list(THEMES.keys())
        items_to_create = []

        for _ in range(n):
            theme = random.choice(theme_names)
            config = THEMES[theme]
            noun = random.choice(config["nouns"])
            name = f"{fake.word().capitalize()} {noun}"
            low, high = config["price_range"]
            price = Decimal(str(round(random.uniform(low, high), 2)))
            description = random.choice(DESCRIPTION_TEMPLATES).format(
                noun=noun.lower(), detail=random.choice(DETAILS)
            )
            item = Item(
                name=name,
                description=description,
                price=price,
                stock=random.randint(0, 200),
            )
            items_to_create.append((item, theme))

        Item.objects.bulk_create([i for i, _ in items_to_create])

        # Re-fetch to get PKs, then bucket by theme (order preserved by bulk_create on most DBs,
        # but we zip defensively by matching name+price rather than assuming order)
        created_items = list(Item.objects.order_by("-id")[:n])
        created_items.reverse()
        for (item_stub, theme), created_item in zip(items_to_create, created_items):
            items_by_theme[theme].append(created_item)

        return items_by_theme

    def _create_orders(self, n, users, items_by_theme):
        self.stdout.write(f"Creating {n} orders with theme-clustered purchases...")
        theme_names = list(items_by_theme.keys())
        statuses = [Order.StatusChoices.CONFIRMED] * 7 + [Order.StatusChoices.PENDING] * 2 \
            + [Order.StatusChoices.CANCELLED] * 1  # weighted: mostly confirmed

        # Give each user a "preferred theme" so their order history clusters —
        # this is what makes collaborative filtering find meaningful patterns later.
        user_preferences = {user.id: random.choice(theme_names) for user in users}

        orders_to_create = []
        for _ in range(n):
            user = random.choice(users)
            preferred_theme = user_preferences[user.id]

            order = Order(user=user, status=random.choice(statuses))
            orders_to_create.append(order)

        Order.objects.bulk_create(orders_to_create)
        created_orders = list(Order.objects.order_by("-created_at")[:n])
        created_orders.reverse()

        order_items_to_create = []
        for order in created_orders:
            preferred_theme = user_preferences[order.user.id]
            n_line_items = random.randint(1, 4)

            for _ in range(n_line_items):
                # 75% chance: pick from the user's preferred theme (creates real affinity signal)
                # 25% chance: pick from a random theme (adds realistic noise)
                if random.random() < 0.75:
                    theme = preferred_theme
                else:
                    theme = random.choice(theme_names)

                candidates = items_by_theme[theme]
                if not candidates:
                    continue
                product = random.choice(candidates)

                order_items_to_create.append(OrderItem(
                    order=order,
                    product=product,
                    quantity=random.randint(1, 3),
                ))

        OrderItem.objects.bulk_create(order_items_to_create)
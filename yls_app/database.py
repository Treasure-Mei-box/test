import sqlite3
from pathlib import Path
from flask import g

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "yls_store.db"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_one(sql, params=()):
    return get_db().execute(sql, params).fetchone()


def query_all(sql, params=()):
    return get_db().execute(sql, params).fetchall()


def execute(sql, params=()):
    db = get_db()
    cursor = db.execute(sql, params)
    db.commit()
    return cursor


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    cursor = db.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL CHECK(role IN ('CUSTOMER', 'STAFF')),
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        address TEXT
    );

    CREATE TABLE IF NOT EXISTS product_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category_id INTEGER NOT NULL,
        price REAL NOT NULL CHECK(price >= 0),
        stock_quantity INTEGER NOT NULL CHECK(stock_quantity >= 0),
        description TEXT,
        FOREIGN KEY(category_id) REFERENCES product_categories(id)
    );

    CREATE TABLE IF NOT EXISTS cart_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL CHECK(quantity > 0),
        UNIQUE(customer_id, product_id),
        FOREIGN KEY(customer_id) REFERENCES users(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        total_amount REAL NOT NULL,
        order_status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        delivery_address TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS order_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL CHECK(quantity > 0),
        price_at_purchase REAL NOT NULL CHECK(price_at_purchase >= 0),
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    );

    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL UNIQUE,
        total_amount REAL NOT NULL,
        generated_at TEXT NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL UNIQUE,
        payment_method TEXT NOT NULL,
        payment_status TEXT NOT NULL,
        processed_at TEXT,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    );

    CREATE TABLE IF NOT EXISTS shipments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL UNIQUE,
        shipment_status TEXT NOT NULL,
        tracking_number TEXT,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    );
    """)

    seed_data(cursor)
    db.commit()
    db.close()


def seed_data(cursor):
    categories = ["Food", "Drinks", "Household", "Specialty"]
    for category in categories:
        cursor.execute(
            "INSERT OR IGNORE INTO product_categories(name) VALUES (?)",
            (category,),
        )

    cursor.execute("""
        INSERT OR IGNORE INTO users(role, name, email, password, address)
        VALUES ('CUSTOMER', 'Demo Customer', 'customer@yls.com', '1234', '1 Hawthorn Street')
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO users(role, name, email, password, address)
        VALUES ('STAFF', 'Demo Staff', 'staff@yls.com', '1234', 'Your Local Shop, Hawthorn')
    """)

    product_count = cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if product_count > 0:
        return

    category_rows = cursor.execute("SELECT id, name FROM product_categories").fetchall()
    category_ids = {row[1]: row[0] for row in category_rows}

    products = [
        ("Milk 1L", "Drinks", 3.20, 20, "Fresh full cream milk."),
        ("Bread Loaf", "Food", 2.80, 15, "Soft white bread loaf."),
        ("Instant Noodles", "Food", 1.50, 50, "Convenient quick meal."),
        ("Dishwashing Liquid", "Household", 4.90, 12, "Lemon scented dishwashing liquid."),
        ("Local Honey", "Specialty", 12.00, 8, "Specialty local honey jar."),
    ]

    for name, category, price, stock, description in products:
        cursor.execute("""
            INSERT INTO products(name, category_id, price, stock_quantity, description)
            VALUES (?, ?, ?, ?, ?)
        """, (name, category_ids[category], price, stock, description))

import sqlite3

conn = sqlite3.connect("store.db", check_same_thread=False)
cursor = conn.cursor()

conn.execute("PRAGMA journal_mode=WAL")

# جدول المنتجات - السعر بالدولار
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price_usd REAL NOT NULL,
    stock INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1
)
''')

# جدول المخزون
cursor.execute('''
CREATE TABLE IF NOT EXISTS stock_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    sold INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id)
)
''')

# جدول الفواتير - يحفظ المبلغ بالدولار والـ LTC
cursor.execute('''
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    amount_usd REAL NOT NULL,
    amount_ltc REAL NOT NULL,
    address TEXT UNIQUE NOT NULL,
    txid TEXT,
    paid INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()


# ── المنتجات ──────────────────────────────────────────
def add_product(name, description, price_usd):
    cursor.execute(
        "INSERT INTO products (name, description, price_usd) VALUES (?, ?, ?)",
        (name, description, price_usd)
    )
    conn.commit()
    return cursor.lastrowid

def get_all_products():
    cursor.execute("SELECT * FROM products WHERE active=1")
    return cursor.fetchall()

def get_product(product_id):
    cursor.execute("SELECT * FROM products WHERE id=?", (product_id,))
    return cursor.fetchone()

def delete_product(product_id):
    cursor.execute("UPDATE products SET active=0 WHERE id=?", (product_id,))
    conn.commit()

def update_product_price(product_id, price_usd):
    cursor.execute("UPDATE products SET price_usd=? WHERE id=?", (price_usd, product_id))
    conn.commit()


# ── المخزون ──────────────────────────────────────────
def add_stock(product_id, content):
    cursor.execute(
        "INSERT INTO stock_items (product_id, content) VALUES (?, ?)",
        (product_id, content)
    )
    cursor.execute(
        "UPDATE products SET stock = stock + 1 WHERE id=?",
        (product_id,)
    )
    conn.commit()

def get_available_item(product_id):
    cursor.execute(
        "SELECT id, content FROM stock_items WHERE product_id=? AND sold=0 LIMIT 1",
        (product_id,)
    )
    return cursor.fetchone()

def mark_item_sold(item_id, product_id):
    cursor.execute("UPDATE stock_items SET sold=1 WHERE id=?", (item_id,))
    cursor.execute(
        "UPDATE products SET stock = stock - 1 WHERE id=? AND stock > 0",
        (product_id,)
    )
    conn.commit()

def get_stock_count(product_id):
    cursor.execute(
        "SELECT COUNT(*) FROM stock_items WHERE product_id=? AND sold=0",
        (product_id,)
    )
    return cursor.fetchone()[0]


# ── الفواتير ──────────────────────────────────────────
def add_payment(user_id, product_id, amount_usd, amount_ltc, address):
    cursor.execute(
        "INSERT INTO payments (user_id, product_id, amount_usd, amount_ltc, address) VALUES (?, ?, ?, ?, ?)",
        (user_id, product_id, amount_usd, amount_ltc, address)
    )
    conn.commit()
    return cursor.lastrowid

def get_payment_by_address(address):
    cursor.execute("SELECT * FROM payments WHERE address=?", (address,))
    return cursor.fetchone()

def mark_paid(txid, address):
    cursor.execute(
        "UPDATE payments SET paid=1, txid=? WHERE address=? AND paid=0",
        (txid, address)
    )
    conn.commit()
    return cursor.rowcount

def get_user_orders(user_id):
    cursor.execute(
        "SELECT p.*, pr.name FROM payments p "
        "JOIN products pr ON p.product_id = pr.id "
        "WHERE p.user_id=? ORDER BY p.created_at DESC LIMIT 10",
        (user_id,)
    )
    return cursor.fetchall()


# ── إحصائيات ──────────────────────────────────────────
def get_stats():
    cursor.execute("SELECT COUNT(*) FROM payments WHERE paid=1")
    total_orders = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(amount_usd) FROM payments WHERE paid=1")
    total_usd = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(amount_ltc) FROM payments WHERE paid=1")
    total_ltc = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM payments WHERE paid=1")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM payments WHERE paid=0")
    pending = cursor.fetchone()[0]

    return {
        "total_orders": total_orders,
        "total_usd": round(total_usd, 2),
        "total_ltc": round(total_ltc, 8),
        "total_users": total_users,
        "pending": pending
    }

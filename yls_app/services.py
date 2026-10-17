from datetime import datetime
import sqlite3
from .database import query_one, query_all, execute
from .models import OrderStatus, PaymentStatus, PaymentMethod, ShipmentStatus


class ValidationError(Exception):
    """Raised when user input violates business validation rules."""


class AuthService:
    @staticmethod
    def register_customer(name, email, password, address):
        name = name.strip()
        email = email.strip().lower()
        password = password.strip()
        address = address.strip()

        if not name or not email or not password or not address:
            raise ValidationError("All registration fields are required.")

        if "@" not in email:
            raise ValidationError("Email address must contain @.")

        try:
            execute("""
                INSERT INTO users(role, name, email, password, address)
                VALUES ('CUSTOMER', ?, ?, ?, ?)
            """, (name, email, password, address))
        except sqlite3.IntegrityError as exc:
            raise ValidationError("This email address is already registered.") from exc

    @staticmethod
    def authenticate(email, password):
        return query_one(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email.strip().lower(), password.strip()),
        )


class StoreCatalogueService:
    @staticmethod
    def list_categories():
        return query_all("SELECT * FROM product_categories ORDER BY name")

    @staticmethod
    def list_products(category_id=None):
        if category_id:
            return query_all("""
                SELECT p.*, c.name AS category
                FROM products p
                JOIN product_categories c ON c.id = p.category_id
                WHERE c.id = ?
                ORDER BY p.name
            """, (category_id,))

        return query_all("""
            SELECT p.*, c.name AS category
            FROM products p
            JOIN product_categories c ON c.id = p.category_id
            ORDER BY p.name
        """)

    @staticmethod
    def get_product(product_id):
        return query_one("""
            SELECT p.*, c.name AS category
            FROM products p
            JOIN product_categories c ON c.id = p.category_id
            WHERE p.id = ?
        """, (product_id,))


class ProductService:
    @staticmethod
    def create_product(name, category_id, price, stock_quantity, description):
        if not name.strip():
            raise ValidationError("Product name is required.")
        if category_id is None:
            raise ValidationError("Product category is required.")
        if price is None or price < 0:
            raise ValidationError("Product price cannot be negative.")
        if stock_quantity is None or stock_quantity < 0:
            raise ValidationError("Stock quantity cannot be negative.")

        execute("""
            INSERT INTO products(name, category_id, price, stock_quantity, description)
            VALUES (?, ?, ?, ?, ?)
        """, (name.strip(), category_id, price, stock_quantity, description.strip()))

    @staticmethod
    def update_product(product_id, name, price, stock_quantity, description):
        if not name.strip():
            raise ValidationError("Product name is required.")
        if price is None or price < 0:
            raise ValidationError("Product price cannot be negative.")
        if stock_quantity is None or stock_quantity < 0:
            raise ValidationError("Stock quantity cannot be negative.")

        execute("""
            UPDATE products
            SET name = ?, price = ?, stock_quantity = ?, description = ?
            WHERE id = ?
        """, (name.strip(), price, stock_quantity, description.strip(), product_id))


class CartService:
    @staticmethod
    def get_cart_items(customer_id):
        return query_all("""
            SELECT ci.id AS cart_item_id, ci.quantity,
                   p.id AS product_id, p.name, p.price, p.stock_quantity
            FROM cart_items ci
            JOIN products p ON p.id = ci.product_id
            WHERE ci.customer_id = ?
            ORDER BY p.name
        """, (customer_id,))

    @staticmethod
    def add_to_cart(customer_id, product_id, quantity):
        if product_id is None:
            raise ValidationError("Product is required.")
        if quantity is None or quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        product = query_one("SELECT * FROM products WHERE id = ?", (product_id,))
        if not product:
            raise ValidationError("Product does not exist.")

        if quantity > product["stock_quantity"]:
            raise ValidationError("Requested quantity exceeds available stock.")

        existing = query_one("""
            SELECT * FROM cart_items
            WHERE customer_id = ? AND product_id = ?
        """, (customer_id, product_id))

        if existing:
            new_quantity = existing["quantity"] + quantity
            if new_quantity > product["stock_quantity"]:
                raise ValidationError("Cart quantity exceeds available stock.")
            execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (new_quantity, existing["id"]))
        else:
            execute("""
                INSERT INTO cart_items(customer_id, product_id, quantity)
                VALUES (?, ?, ?)
            """, (customer_id, product_id, quantity))

    @staticmethod
    def update_quantity(customer_id, cart_item_id, quantity):
        if cart_item_id is None:
            raise ValidationError("Cart item is required.")
        if quantity is None or quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        item = query_one("""
            SELECT ci.*, p.stock_quantity
            FROM cart_items ci
            JOIN products p ON p.id = ci.product_id
            WHERE ci.id = ? AND ci.customer_id = ?
        """, (cart_item_id, customer_id))

        if not item:
            raise ValidationError("Cart item not found.")

        if quantity > item["stock_quantity"]:
            raise ValidationError("Requested quantity exceeds available stock.")

        execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (quantity, cart_item_id))

    @staticmethod
    def remove_item(customer_id, cart_item_id):
        execute("DELETE FROM cart_items WHERE id = ? AND customer_id = ?", (cart_item_id, customer_id))

    @staticmethod
    def calculate_total(customer_id):
        items = CartService.get_cart_items(customer_id)
        return sum(item["quantity"] * item["price"] for item in items)


class CheckoutService:
    @staticmethod
    def create_order_from_cart(customer):
        cart_items = CartService.get_cart_items(customer["id"])
        if not cart_items:
            raise ValidationError("Cannot checkout because the shopping cart is empty.")

        for item in cart_items:
            if item["quantity"] > item["stock_quantity"]:
                raise ValidationError(f"Not enough stock for {item['name']}.")

        total_amount = sum(item["quantity"] * item["price"] for item in cart_items)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        delivery_address = customer["address"] or "No address provided"

        cursor = execute("""
            INSERT INTO orders(customer_id, total_amount, order_status, created_at, delivery_address)
            VALUES (?, ?, ?, ?, ?)
        """, (customer["id"], total_amount, OrderStatus.CREATED.value, now, delivery_address))

        order_id = cursor.lastrowid

        for item in cart_items:
            execute("""
                INSERT INTO order_products(order_id, product_id, quantity, price_at_purchase)
                VALUES (?, ?, ?, ?)
            """, (order_id, item["product_id"], item["quantity"], item["price"]))

            execute("""
                UPDATE products
                SET stock_quantity = stock_quantity - ?
                WHERE id = ?
            """, (item["quantity"], item["product_id"]))

        execute("""
            INSERT INTO invoices(order_id, total_amount, generated_at)
            VALUES (?, ?, ?)
        """, (order_id, total_amount, now))

        execute("DELETE FROM cart_items WHERE customer_id = ?", (customer["id"],))
        return order_id


class PaymentService:
    @staticmethod
    def process_payment(customer_id, order_id, payment_method):
        if payment_method not in [method.value for method in PaymentMethod]:
            raise ValidationError("Invalid payment method.")

        order = query_one("""
            SELECT * FROM orders
            WHERE id = ? AND customer_id = ?
        """, (order_id, customer_id))

        if not order:
            raise ValidationError("Order not found.")

        existing_payment = query_one("SELECT * FROM payments WHERE order_id = ?", (order_id,))
        if existing_payment:
            raise ValidationError("Payment has already been processed for this order.")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        execute("""
            INSERT INTO payments(order_id, payment_method, payment_status, processed_at)
            VALUES (?, ?, ?, ?)
        """, (order_id, payment_method, PaymentStatus.PROCESSED.value, now))

        execute("""
            UPDATE orders
            SET order_status = ?
            WHERE id = ?
        """, (OrderStatus.PAID.value, order_id))


class ShipmentService:
    @staticmethod
    def list_paid_orders():
        return query_all("""
            SELECT o.*, u.name AS customer_name, s.shipment_status
            FROM orders o
            JOIN users u ON u.id = o.customer_id
            LEFT JOIN shipments s ON s.order_id = o.id
            WHERE o.order_status IN (?, ?, ?)
            ORDER BY o.id DESC
        """, (OrderStatus.PAID.value, OrderStatus.FULFILMENT.value, OrderStatus.COMPLETED.value))

    @staticmethod
    def update_shipment(order_id, shipment_status, tracking_number):
        valid_statuses = [status.value for status in ShipmentStatus]
        if shipment_status not in valid_statuses:
            raise ValidationError("Invalid shipment status.")

        order = query_one("SELECT * FROM orders WHERE id = ?", (order_id,))
        if not order:
            raise ValidationError("Order not found.")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        existing = query_one("SELECT * FROM shipments WHERE order_id = ?", (order_id,))

        if existing:
            execute("""
                UPDATE shipments
                SET shipment_status = ?, tracking_number = ?, updated_at = ?
                WHERE order_id = ?
            """, (shipment_status, tracking_number.strip(), now, order_id))
        else:
            execute("""
                INSERT INTO shipments(order_id, shipment_status, tracking_number, updated_at)
                VALUES (?, ?, ?, ?)
            """, (order_id, shipment_status, tracking_number.strip(), now))

        new_order_status = OrderStatus.COMPLETED.value if shipment_status == ShipmentStatus.DELIVERED.value else OrderStatus.FULFILMENT.value
        execute("UPDATE orders SET order_status = ? WHERE id = ?", (new_order_status, order_id))


class ReportService:
    @staticmethod
    def sales_report():
        orders = query_all("""
            SELECT o.*, u.name AS customer_name
            FROM orders o
            JOIN users u ON u.id = o.customer_id
            WHERE o.order_status IN (?, ?, ?)
            ORDER BY o.created_at DESC
        """, (OrderStatus.PAID.value, OrderStatus.FULFILMENT.value, OrderStatus.COMPLETED.value))

        total_sales = sum(order["total_amount"] for order in orders)
        return orders, total_sales

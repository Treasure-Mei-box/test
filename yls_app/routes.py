from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .database import query_one, query_all
from .services import (
    AuthService,
    StoreCatalogueService,
    ProductService,
    CartService,
    CheckoutService,
    PaymentService,
    ShipmentService,
    ReportService,
    ValidationError,
)
from .models import PaymentMethod, ShipmentStatus

main_bp = Blueprint("main", __name__)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return query_one("SELECT * FROM users WHERE id = ?", (user_id,))


@main_bp.app_context_processor
def inject_user():
    return {"current_user": current_user()}


def require_login(role=None):
    user = current_user()
    if not user:
        flash("Please log in first.")
        return None

    if role and user["role"] != role:
        flash("You do not have permission to access that page.")
        return None

    return user


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            AuthService.register_customer(
                request.form.get("name", ""),
                request.form.get("email", ""),
                request.form.get("password", ""),
                request.form.get("address", ""),
            )
            flash("Registration successful. Please log in.")
            return redirect(url_for("main.login"))
        except ValidationError as error:
            flash(str(error))

    return render_template("register.html")


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = AuthService.authenticate(
            request.form.get("email", ""),
            request.form.get("password", ""),
        )

        if not user:
            flash("Invalid username or password.")
            return redirect(url_for("main.login"))

        session["user_id"] = user["id"]
        flash(f"Welcome, {user['name']}.")
        return redirect(url_for("main.index"))

    return render_template("login.html")


@main_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for("main.index"))


@main_bp.route("/catalogue")
def catalogue():
    category_id = request.args.get("category_id", type=int)
    categories = StoreCatalogueService.list_categories()
    products = StoreCatalogueService.list_products(category_id)
    return render_template(
        "catalogue.html",
        categories=categories,
        products=products,
        selected_category_id=category_id,
    )


@main_bp.route("/cart/add", methods=["POST"])
def add_to_cart():
    user = require_login("CUSTOMER")
    if not user:
        return redirect(url_for("main.login"))

    try:
        CartService.add_to_cart(
            user["id"],
            request.form.get("product_id", type=int),
            request.form.get("quantity", type=int),
        )
        flash("Product added to cart.")
        return redirect(url_for("main.cart"))
    except ValidationError as error:
        flash(str(error))
        return redirect(url_for("main.catalogue"))


@main_bp.route("/cart")
def cart():
    user = require_login("CUSTOMER")
    if not user:
        return redirect(url_for("main.login"))

    items = CartService.get_cart_items(user["id"])
    total = CartService.calculate_total(user["id"])
    return render_template("cart.html", items=items, total=total)


@main_bp.route("/cart/update", methods=["POST"])
def update_cart():
    user = require_login("CUSTOMER")
    if not user:
        return redirect(url_for("main.login"))

    try:
        CartService.update_quantity(
            user["id"],
            request.form.get("cart_item_id", type=int),
            request.form.get("quantity", type=int),
        )
        flash("Cart updated.")
    except ValidationError as error:
        flash(str(error))

    return redirect(url_for("main.cart"))


@main_bp.route("/cart/remove", methods=["POST"])
def remove_cart_item():
    user = require_login("CUSTOMER")
    if not user:
        return redirect(url_for("main.login"))

    CartService.remove_item(
        user["id"],
        request.form.get("cart_item_id", type=int),
    )
    flash("Item removed from cart.")
    return redirect(url_for("main.cart"))


@main_bp.route("/checkout", methods=["POST"])
def checkout():
    user = require_login("CUSTOMER")
    if not user:
        return redirect(url_for("main.login"))

    try:
        order_id = CheckoutService.create_order_from_cart(user)
        flash("Order created and invoice generated.")
        return redirect(url_for("main.order_detail", order_id=order_id))
    except ValidationError as error:
        flash(str(error))
        return redirect(url_for("main.cart"))


@main_bp.route("/orders")
def my_orders():
    user = require_login("CUSTOMER")
    if not user:
        return redirect(url_for("main.login"))

    orders = query_all(
        "SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC",
        (user["id"],),
    )
    return render_template("my_orders.html", orders=orders)


@main_bp.route("/orders/<int:order_id>")
def order_detail(order_id):
    user = require_login()
    if not user:
        return redirect(url_for("main.login"))

    order = query_one("SELECT * FROM orders WHERE id = ?", (order_id,))
    if not order:
        flash("Order not found.")
        return redirect(url_for("main.index"))

    if user["role"] == "CUSTOMER" and order["customer_id"] != user["id"]:
        flash("You cannot view another customer's order.")
        return redirect(url_for("main.my_orders"))

    order_items = query_all("""
        SELECT op.*, p.name
        FROM order_products op
        JOIN products p ON p.id = op.product_id
        WHERE op.order_id = ?
    """, (order_id,))
    invoice = query_one("SELECT * FROM invoices WHERE order_id = ?", (order_id,))
    payment = query_one("SELECT * FROM payments WHERE order_id = ?", (order_id,))
    shipment = query_one("SELECT * FROM shipments WHERE order_id = ?", (order_id,))

    return render_template(
        "order_detail.html",
        order=order,
        order_items=order_items,
        invoice=invoice,
        payment=payment,
        shipment=shipment,
        payment_methods=[method.value for method in PaymentMethod],
    )


@main_bp.route("/orders/<int:order_id>/payment", methods=["POST"])
def process_payment(order_id):
    user = require_login("CUSTOMER")
    if not user:
        return redirect(url_for("main.login"))

    try:
        PaymentService.process_payment(
            user["id"],
            order_id,
            request.form.get("payment_method", ""),
        )
        flash("Payment processed successfully. No real banking transaction was performed.")
    except ValidationError as error:
        flash(str(error))

    return redirect(url_for("main.order_detail", order_id=order_id))


@main_bp.route("/staff/products")
def staff_products():
    user = require_login("STAFF")
    if not user:
        return redirect(url_for("main.login"))

    products = StoreCatalogueService.list_products()
    return render_template("staff_products.html", products=products)


@main_bp.route("/staff/products/add", methods=["GET", "POST"])
def add_product():
    user = require_login("STAFF")
    if not user:
        return redirect(url_for("main.login"))

    categories = StoreCatalogueService.list_categories()

    if request.method == "POST":
        try:
            ProductService.create_product(
                request.form.get("name", ""),
                request.form.get("category_id", type=int),
                request.form.get("price", type=float),
                request.form.get("stock_quantity", type=int),
                request.form.get("description", ""),
            )
            flash("Product added.")
            return redirect(url_for("main.staff_products"))
        except ValidationError as error:
            flash(str(error))

    return render_template("product_form.html", categories=categories, product=None)


@main_bp.route("/staff/products/<int:product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id):
    user = require_login("STAFF")
    if not user:
        return redirect(url_for("main.login"))

    product = StoreCatalogueService.get_product(product_id)
    if not product:
        flash("Product not found.")
        return redirect(url_for("main.staff_products"))

    categories = StoreCatalogueService.list_categories()

    if request.method == "POST":
        try:
            ProductService.update_product(
                product_id,
                request.form.get("name", ""),
                request.form.get("price", type=float),
                request.form.get("stock_quantity", type=int),
                request.form.get("description", ""),
            )
            flash("Product updated.")
            return redirect(url_for("main.staff_products"))
        except ValidationError as error:
            flash(str(error))

    return render_template("product_form.html", categories=categories, product=product)


@main_bp.route("/staff/shipments")
def staff_shipments():
    user = require_login("STAFF")
    if not user:
        return redirect(url_for("main.login"))

    orders = ShipmentService.list_paid_orders()
    return render_template("staff_shipments.html", orders=orders)


@main_bp.route("/staff/shipments/<int:order_id>", methods=["GET", "POST"])
def manage_shipment(order_id):
    user = require_login("STAFF")
    if not user:
        return redirect(url_for("main.login"))

    order = query_one("SELECT * FROM orders WHERE id = ?", (order_id,))
    if not order:
        flash("Order not found.")
        return redirect(url_for("main.staff_shipments"))

    shipment = query_one("SELECT * FROM shipments WHERE order_id = ?", (order_id,))
    shipment_statuses = [status.value for status in ShipmentStatus]

    if request.method == "POST":
        try:
            ShipmentService.update_shipment(
                order_id,
                request.form.get("shipment_status", ""),
                request.form.get("tracking_number", ""),
            )
            flash("Shipment updated.")
            return redirect(url_for("main.staff_shipments"))
        except ValidationError as error:
            flash(str(error))

    return render_template(
        "manage_shipment.html",
        order=order,
        shipment=shipment,
        shipment_statuses=shipment_statuses,
    )


@main_bp.route("/staff/reports")
def sales_report():
    user = require_login("STAFF")
    if not user:
        return redirect(url_for("main.login"))

    orders, total_sales = ReportService.sales_report()
    return render_template("sales_report.html", orders=orders, total_sales=total_sales)

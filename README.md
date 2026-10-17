# Your Local Shop, Flask + SQLite Implementation

This is a structured Flask implementation for SWE30003 Assignment 3.

## Implemented business-operation areas

1. Customer registration and login
2. Product catalogue browsing and filtering
3. Shopping cart management
4. Checkout, order creation, and invoice generation
5. Simulated payment processing
6. Staff product management
7. Shipment fulfilment updates
8. Sales report generation

## How to run

Open this folder in Visual Studio Code, then run:

```bash
pip install flask
python app.py
```

If your computer uses the Windows Python launcher:

```bash
py -m pip install flask
py app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Demo accounts

Customer:
- Email: customer@yls.com
- Password: 1234

Store staff:
- Email: staff@yls.com
- Password: 1234

## Notes for the report

The implementation uses SQLite linking tables called `cart_items` and `order_products` to store many-to-many product quantities. These are persistence-level database structures, not separate domain classes in the Assignment 2 UML. At the object-design level, product and quantity information remains handled by `ShoppingCart` before checkout and by `Order` after checkout.

Real payment gateway validation is not implemented. The payment step displays a simulated processed-payment result, matching the Assignment 3 simplification.

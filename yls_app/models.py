from dataclasses import dataclass
from enum import Enum


class OrderStatus(Enum):
    CREATED = "CREATED"
    PAID = "PAID"
    FULFILMENT = "FULFILMENT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PaymentStatus(Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class PaymentMethod(Enum):
    CARD = "CARD"
    ONLINE_BANKING = "ONLINE_BANKING"
    EWALLET = "EWALLET"


class ShipmentStatus(Enum):
    PREPARING = "PREPARING"
    PACKED = "PACKED"
    DISPATCHED = "DISPATCHED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


@dataclass
class User:
    id: int
    name: str
    email: str
    role: str


@dataclass
class Customer(User):
    address: str


@dataclass
class StoreStaff(User):
    pass


@dataclass
class Product:
    id: int
    name: str
    category: str
    price: float
    stock_quantity: int
    description: str = ""


@dataclass
class ShoppingCart:
    customer_id: int


@dataclass
class Order:
    id: int
    customer_id: int
    total_amount: float
    order_status: str


@dataclass
class Invoice:
    id: int
    order_id: int
    total_amount: float


@dataclass
class Payment:
    id: int
    order_id: int
    payment_method: str
    payment_status: str


@dataclass
class Shipment:
    id: int
    order_id: int
    shipment_status: str


@dataclass
class SalesReport:
    total_orders: int
    total_sales: float

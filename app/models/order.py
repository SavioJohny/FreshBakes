"""Order models."""

from datetime import datetime
import uuid
from app.extensions import db


class Order(db.Model):
    """Order model."""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bakery_id = db.Column(db.Integer, db.ForeignKey('bakeries.id'), nullable=False)
    delivery_address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'))
    
    # Pricing
    subtotal = db.Column(db.Float, default=0.0)
    delivery_fee = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    
    # Status
    status = db.Column(db.String(50), default='pending')
    # pending, confirmed, preparing, ready, out_for_delivery, delivered, cancelled
    
    # Payment
    payment_method = db.Column(db.String(20), default='cod')  # cod, online
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, failed, refunded
    
    # Additional info
    cancellation_reason = db.Column(db.String(500))
    special_instructions = db.Column(db.Text)
    
    # Timestamps
    estimated_delivery = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    status_history = db.relationship('OrderStatusHistory', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    delivery_address = db.relationship('Address', foreign_keys=[delivery_address_id])
    review = db.relationship('Review', backref='order', uselist=False)
    
    @staticmethod
    def generate_order_number():
        """Generate a unique order number."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M')
        unique_id = str(uuid.uuid4().hex)[:6].upper()
        return f'LC{timestamp}{unique_id}'
    
    def add_status_history(self, status, notes=None):
        """Add a status change to history."""
        history = OrderStatusHistory(
            order_id=self.id,
            status=status,
            notes=notes
        )
        db.session.add(history)
    
    def can_cancel(self):
        """Check if order can be cancelled."""
        return self.status in ['pending', 'confirmed']
    
    def __repr__(self):
        return f'<Order {self.order_number}>'


class OrderItem(db.Model):
    """Order item model."""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)  # Snapshot of product name
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    special_instructions = db.Column(db.String(500))
    
    def __repr__(self):
        return f'<OrderItem {self.product_name} x {self.quantity}>'


class OrderStatusHistory(db.Model):
    """Order status history model."""
    __tablename__ = 'order_status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<OrderStatusHistory {self.status}>'

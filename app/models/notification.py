"""Notification model."""

from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    """User notifications."""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='system')  # order, promo, system
    link = db.Column(db.String(255))  # Optional URL to redirect
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def create_order_notification(user_id, order_number, status):
        """Create an order status notification."""
        status_messages = {
            'confirmed': 'Your order has been confirmed by the bakery!',
            'preparing': 'The bakery is preparing your order.',
            'ready': 'Your order is ready for pickup/delivery!',
            'out_for_delivery': 'Your order is on its way!',
            'delivered': 'Your order has been delivered. Enjoy!',
            'cancelled': 'Your order has been cancelled.',
        }
        message = status_messages.get(status, f'Order status updated to: {status}')
        return Notification(
            user_id=user_id,
            title=f'Order {order_number}',
            message=message,
            type='order',
            link=f'/orders/{order_number}'
        )
    
    def __repr__(self):
        return f'<Notification {self.title}>'

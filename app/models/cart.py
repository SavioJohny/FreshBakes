"""Cart model."""

from datetime import datetime
from app.extensions import db


class CartItem(db.Model):
    """Shopping cart item model."""
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    special_instructions = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def subtotal(self):
        """Calculate subtotal for this cart item."""
        if self.product:
            return self.product.current_price * self.quantity
        return 0
    
    def __repr__(self):
        return f'<CartItem {self.product_id} x {self.quantity}>'

"""Review model."""

from datetime import datetime
from app.extensions import db


class Review(db.Model):
    """Review model for bakeries and products."""
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bakery_id = db.Column(db.Integer, db.ForeignKey('bakeries.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))  # Optional - for product-specific reviews
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    reply = db.Column(db.Text)  # Baker's reply
    reply_at = db.Column(db.DateTime)
    is_visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Review {self.rating} stars>'

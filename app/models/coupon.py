"""Coupon model."""

from datetime import datetime
from app.extensions import db


class Coupon(db.Model):
    """Discount coupon model."""
    __tablename__ = 'coupons'
    
    id = db.Column(db.Integer, primary_key=True)
    bakery_id = db.Column(db.Integer, db.ForeignKey('bakeries.id'))  # Null for platform-wide coupons
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))
    discount_type = db.Column(db.String(20), nullable=False)  # percentage, fixed
    discount_value = db.Column(db.Float, nullable=False)
    min_order_amount = db.Column(db.Float, default=0.0)
    max_discount = db.Column(db.Float)  # Maximum discount amount for percentage coupons
    usage_limit = db.Column(db.Integer)  # Null for unlimited
    used_count = db.Column(db.Integer, default=0)
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_valid(self, order_amount, bakery_id=None):
        """Check if coupon is valid for given order."""
        now = datetime.utcnow()
        
        # Check if active
        if not self.is_active:
            return False, 'Coupon is not active'
        
        # Check validity period
        if self.valid_from and now < self.valid_from:
            return False, 'Coupon is not yet valid'
        if self.valid_until and now > self.valid_until:
            return False, 'Coupon has expired'
        
        # Check usage limit
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, 'Coupon usage limit reached'
        
        # Check minimum order amount
        if order_amount < self.min_order_amount:
            return False, f'Minimum order amount is ₹{self.min_order_amount}'
        
        # Check bakery-specific coupon
        if self.bakery_id and bakery_id and self.bakery_id != bakery_id:
            return False, 'Coupon is not valid for this bakery'
        
        return True, 'Coupon is valid'
    
    def calculate_discount(self, order_amount):
        """Calculate discount amount."""
        if self.discount_type == 'percentage':
            discount = (order_amount * self.discount_value) / 100
            if self.max_discount:
                discount = min(discount, self.max_discount)
            return discount
        else:  # fixed
            return min(self.discount_value, order_amount)
    
    def __repr__(self):
        return f'<Coupon {self.code}>'

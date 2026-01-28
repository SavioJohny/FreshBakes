"""Bakery and Category models."""

from datetime import datetime
from slugify import slugify
from app.extensions import db


class Bakery(db.Model):
    """Bakery/store model."""
    __tablename__ = 'bakeries'
    
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(170), unique=True, index=True)
    description = db.Column(db.Text)
    address = db.Column(db.String(500), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    logo_url = db.Column(db.String(255), default='default-bakery.png')
    banner_url = db.Column(db.String(255))
    rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)
    min_order_amount = db.Column(db.Float, default=0.0)
    delivery_fee = db.Column(db.Float, default=0.0)
    delivery_time_mins = db.Column(db.Integer, default=30)
    is_approved = db.Column(db.Boolean, default=False)
    is_open = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    operating_hours = db.Column(db.JSON, default=lambda: {
        'monday': {'open': '09:00', 'close': '21:00', 'is_open': True},
        'tuesday': {'open': '09:00', 'close': '21:00', 'is_open': True},
        'wednesday': {'open': '09:00', 'close': '21:00', 'is_open': True},
        'thursday': {'open': '09:00', 'close': '21:00', 'is_open': True},
        'friday': {'open': '09:00', 'close': '21:00', 'is_open': True},
        'saturday': {'open': '09:00', 'close': '22:00', 'is_open': True},
        'sunday': {'open': '10:00', 'close': '20:00', 'is_open': True},
    })
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    categories = db.relationship('Category', backref='bakery', lazy='dynamic', cascade='all, delete-orphan')
    products = db.relationship('Product', backref='bakery', lazy='dynamic', cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='bakery', lazy='dynamic')
    reviews = db.relationship('Review', backref='bakery', lazy='dynamic')
    coupons = db.relationship('Coupon', backref='bakery', lazy='dynamic')
    
    def generate_slug(self):
        """Generate a unique slug for the bakery."""
        base_slug = slugify(self.name) if self.name else 'bakery'
        slug = base_slug
        counter = 1
        while Bakery.query.filter_by(slug=slug).first() is not None:
            slug = f"{base_slug}-{counter}"
            counter += 1
        self.slug = slug
    
    def update_rating(self):
        """Update bakery rating based on reviews."""
        reviews = self.reviews.filter_by(is_visible=True).all()
        if reviews:
            self.rating = sum(r.rating for r in reviews) / len(reviews)
            self.total_reviews = len(reviews)
        else:
            self.rating = 0.0
            self.total_reviews = 0
    
    def get_available_products(self):
        """Get all available products."""
        return self.products.filter_by(is_available=True).all()
    
    def __repr__(self):
        return f'<Bakery {self.name}>'


class Category(db.Model):
    """Product category model."""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    bakery_id = db.Column(db.Integer, db.ForeignKey('bakeries.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<Category {self.name}>'

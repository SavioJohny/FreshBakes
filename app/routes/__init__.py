"""Routes package - register all blueprints."""

from flask import Flask


def register_blueprints(app: Flask):
    """Register all blueprints with the application."""
    from .auth import auth_bp
    from .main import main_bp
    from .customer import customer_bp
    from .baker import baker_bp
    from .admin import admin_bp
    from .cart import cart_bp
    from .orders import orders_bp
    from .api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(baker_bp, url_prefix='/baker')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(cart_bp, url_prefix='/cart')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(api_bp, url_prefix='/api')

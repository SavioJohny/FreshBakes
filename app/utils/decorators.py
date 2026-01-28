"""Role-based access decorators."""

from functools import wraps
from flask import redirect, url_for, flash, abort
from flask_login import current_user


def customer_required(f):
    """Decorator to require customer role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_customer() and not current_user.is_admin():
            flash('Access denied.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def baker_required(f):
    """Decorator to require baker role with approved bakery."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_baker():
            flash('Access denied. Baker account required.', 'danger')
            return redirect(url_for('main.index'))
        if not current_user.bakery or not current_user.bakery.is_approved:
            flash('Your bakery is pending approval.', 'warning')
            return redirect(url_for('baker.pending_approval'))
        return f(*args, **kwargs)
    return decorated_function


def baker_or_pending_required(f):
    """Decorator for baker routes that work even when pending approval."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_baker():
            flash('Access denied. Baker account required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

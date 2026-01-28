"""Customer routes."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import User, Address, Order, Notification, Review
from app.utils.decorators import customer_required

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/dashboard')
@login_required
def dashboard():
    """Customer dashboard."""
    # Recent orders
    recent_orders = Order.query.filter_by(
        customer_id=current_user.id
    ).order_by(Order.created_at.desc()).limit(5).all()
    
    # Unread notifications
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    return render_template('customer/dashboard.html',
                         recent_orders=recent_orders,
                         unread_notifications=unread_notifications)


@customer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Customer profile management."""
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.phone = request.form.get('phone')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('customer.profile'))
    
    return render_template('customer/profile.html')


@customer_bp.route('/addresses')
@login_required
def addresses():
    """Manage delivery addresses."""
    user_addresses = Address.query.filter_by(user_id=current_user.id).all()
    return render_template('customer/addresses.html', addresses=user_addresses)


@customer_bp.route('/addresses/add', methods=['GET', 'POST'])
@login_required
def add_address():
    """Add new delivery address."""
    if request.method == 'POST':
        # If this is the first address, make it default
        is_first = Address.query.filter_by(user_id=current_user.id).count() == 0
        
        address = Address(
            user_id=current_user.id,
            label=request.form.get('label', 'Home'),
            full_address=request.form.get('full_address'),
            city=request.form.get('city'),
            pincode=request.form.get('pincode'),
            landmark=request.form.get('landmark'),
            is_default=is_first or request.form.get('is_default') == 'on'
        )
        
        # If setting as default, unset others
        if address.is_default:
            Address.query.filter_by(user_id=current_user.id).update({'is_default': False})
        
        db.session.add(address)
        db.session.commit()
        flash('Address added successfully!', 'success')
        return redirect(url_for('customer.addresses'))
    
    return render_template('customer/address_form.html', address=None)


@customer_bp.route('/addresses/<int:address_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_address(address_id):
    """Edit delivery address."""
    address = Address.query.filter_by(id=address_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        address.label = request.form.get('label', 'Home')
        address.full_address = request.form.get('full_address')
        address.city = request.form.get('city')
        address.pincode = request.form.get('pincode')
        address.landmark = request.form.get('landmark')
        
        if request.form.get('is_default') == 'on':
            Address.query.filter_by(user_id=current_user.id).update({'is_default': False})
            address.is_default = True
        
        db.session.commit()
        flash('Address updated successfully!', 'success')
        return redirect(url_for('customer.addresses'))
    
    return render_template('customer/address_form.html', address=address)


@customer_bp.route('/addresses/<int:address_id>/delete', methods=['POST'])
@login_required
def delete_address(address_id):
    """Delete delivery address."""
    address = Address.query.filter_by(id=address_id, user_id=current_user.id).first_or_404()
    db.session.delete(address)
    db.session.commit()
    flash('Address deleted successfully!', 'success')
    return redirect(url_for('customer.addresses'))


@customer_bp.route('/notifications')
@login_required
def notifications():
    """View all notifications."""
    page = request.args.get('page', 1, type=int)
    
    notifications_query = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc())
    
    pagination = notifications_query.paginate(page=page, per_page=20, error_out=False)
    
    return render_template('customer/notifications.html',
                         notifications=pagination.items,
                         pagination=pagination)


@customer_bp.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    """Mark all notifications as read."""
    Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    
    return redirect(url_for('customer.notifications'))


@customer_bp.route('/review/<int:order_id>', methods=['GET', 'POST'])
@login_required
def write_review(order_id):
    """Write a review for an order."""
    order = Order.query.filter_by(
        id=order_id,
        customer_id=current_user.id,
        status='delivered'
    ).first_or_404()
    
    # Check if already reviewed
    existing_review = Review.query.filter_by(order_id=order_id).first()
    if existing_review:
        flash('You have already reviewed this order.', 'info')
        return redirect(url_for('orders.order_detail', order_number=order.order_number))
    
    if request.method == 'POST':
        review = Review(
            user_id=current_user.id,
            bakery_id=order.bakery_id,
            order_id=order.id,
            rating=int(request.form.get('rating', 5)),
            comment=request.form.get('comment')
        )
        db.session.add(review)
        
        # Update bakery rating
        order.bakery.update_rating()
        
        db.session.commit()
        flash('Thank you for your review!', 'success')
        return redirect(url_for('orders.order_detail', order_number=order.order_number))
    
    return render_template('customer/write_review.html', order=order)


@customer_bp.route('/reviews')
@login_required
def my_reviews():
    """View user's reviews."""
    reviews = Review.query.filter_by(user_id=current_user.id).order_by(
        Review.created_at.desc()
    ).all()
    
    return render_template('customer/my_reviews.html', reviews=reviews)


@customer_bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_my_review(review_id):
    """Delete user's own review."""
    review = Review.query.filter_by(
        id=review_id,
        user_id=current_user.id
    ).first_or_404()
    
    bakery = review.bakery
    db.session.delete(review)
    db.session.commit()
    
    # Update bakery rating
    bakery.update_rating()
    
    flash('Review deleted.', 'success')
    return redirect(url_for('customer.my_reviews'))


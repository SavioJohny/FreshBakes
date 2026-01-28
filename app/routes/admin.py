"""Admin panel routes."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models import (User, Bakery, Order, Product, Review, 
                        Coupon, ContactMessage, Notification)
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with platform overview."""
    # Today's stats
    today = datetime.utcnow().date()
    
    # User stats
    total_users = User.query.count()
    total_customers = User.query.filter_by(role='customer').count()
    total_bakers = User.query.filter_by(role='baker').count()
    
    # Bakery stats
    total_bakeries = Bakery.query.count()
    approved_bakeries = Bakery.query.filter_by(is_approved=True).count()
    pending_bakeries = Bakery.query.filter_by(is_approved=False).count()
    
    # Order stats
    total_orders = Order.query.count()
    today_orders = Order.query.filter(
        func.date(Order.created_at) == today
    ).count()
    
    # Revenue
    total_revenue = db.session.query(
        func.sum(Order.total_amount)
    ).filter(Order.status == 'delivered').scalar() or 0
    
    today_revenue = db.session.query(
        func.sum(Order.total_amount)
    ).filter(
        Order.status == 'delivered',
        func.date(Order.created_at) == today
    ).scalar() or 0
    
    # Recent orders
    recent_orders = Order.query.order_by(
        Order.created_at.desc()
    ).limit(10).all()
    
    # Pending approvals
    pending_approvals = Bakery.query.filter_by(
        is_approved=False
    ).order_by(Bakery.created_at.desc()).limit(5).all()
    
    # Recent contact messages
    new_messages = ContactMessage.query.filter_by(
        status='new'
    ).count()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_customers=total_customers,
                         total_bakers=total_bakers,
                         total_bakeries=total_bakeries,
                         approved_bakeries=approved_bakeries,
                         pending_bakeries=pending_bakeries,
                         total_orders=total_orders,
                         today_orders=today_orders,
                         total_revenue=total_revenue,
                         today_revenue=today_revenue,
                         recent_orders=recent_orders,
                         pending_approvals=pending_approvals,
                         new_messages=new_messages)


# --- Baker Management ---
@admin_bp.route('/bakeries')
@login_required
@admin_required
def bakeries():
    """All bakeries list."""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Bakery.query
    
    if status == 'approved':
        query = query.filter_by(is_approved=True)
    elif status == 'pending':
        query = query.filter_by(is_approved=False)
    
    pagination = query.order_by(Bakery.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/bakeries.html',
                         bakeries=pagination.items,
                         pagination=pagination,
                         current_status=status)


@admin_bp.route('/bakeries/pending')
@login_required
@admin_required
def pending_approvals():
    """Pending baker approvals."""
    bakeries = Bakery.query.filter_by(
        is_approved=False
    ).order_by(Bakery.created_at.desc()).all()
    
    return render_template('admin/pending_approvals.html', bakeries=bakeries)


@admin_bp.route('/bakeries/<int:bakery_id>')
@login_required
@admin_required
def bakery_detail(bakery_id):
    """Bakery detail view."""
    bakery = Bakery.query.get_or_404(bakery_id)
    
    # Stats
    total_orders = Order.query.filter_by(bakery_id=bakery_id).count()
    total_products = Product.query.filter_by(bakery_id=bakery_id).count()
    total_revenue = db.session.query(
        func.sum(Order.total_amount)
    ).filter(
        Order.bakery_id == bakery_id,
        Order.status == 'delivered'
    ).scalar() or 0
    
    return render_template('admin/bakery_detail.html',
                         bakery=bakery,
                         total_orders=total_orders,
                         total_products=total_products,
                         total_revenue=total_revenue)


@admin_bp.route('/bakeries/<int:bakery_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_bakery(bakery_id):
    """Approve a bakery."""
    bakery = Bakery.query.get_or_404(bakery_id)
    bakery.is_approved = True
    
    # Notify baker
    notification = Notification(
        user_id=bakery.owner_id,
        title='Bakery Approved!',
        message=f'Congratulations! Your bakery "{bakery.name}" has been approved. You can now start selling!',
        type='system'
    )
    db.session.add(notification)
    db.session.commit()
    
    flash(f'Bakery "{bakery.name}" has been approved!', 'success')
    return redirect(url_for('admin.pending_approvals'))


@admin_bp.route('/bakeries/<int:bakery_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_bakery(bakery_id):
    """Reject a bakery application."""
    bakery = Bakery.query.get_or_404(bakery_id)
    reason = request.form.get('reason', 'Application rejected')
    
    # Notify baker
    notification = Notification(
        user_id=bakery.owner_id,
        title='Bakery Application Update',
        message=f'Your bakery "{bakery.name}" application was not approved. Reason: {reason}',
        type='system'
    )
    db.session.add(notification)
    
    # Delete bakery and user
    db.session.delete(bakery)
    db.session.commit()
    
    flash(f'Bakery application rejected.', 'info')
    return redirect(url_for('admin.pending_approvals'))


@admin_bp.route('/bakeries/<int:bakery_id>/toggle-featured', methods=['POST'])
@login_required
@admin_required
def toggle_featured(bakery_id):
    """Toggle bakery featured status."""
    bakery = Bakery.query.get_or_404(bakery_id)
    bakery.is_featured = not bakery.is_featured
    db.session.commit()
    
    status = 'featured' if bakery.is_featured else 'unfeatured'
    flash(f'Bakery is now {status}.', 'success')
    return redirect(url_for('admin.bakery_detail', bakery_id=bakery_id))


@admin_bp.route('/bakeries/<int:bakery_id>/suspend', methods=['POST'])
@login_required
@admin_required
def suspend_bakery(bakery_id):
    """Suspend/unsuspend a bakery."""
    bakery = Bakery.query.get_or_404(bakery_id)
    bakery.is_approved = not bakery.is_approved
    db.session.commit()
    
    status = 'reinstated' if bakery.is_approved else 'suspended'
    flash(f'Bakery has been {status}.', 'success')
    return redirect(url_for('admin.bakery_detail', bakery_id=bakery_id))


# --- User Management ---
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """User management."""
    page = request.args.get('page', 1, type=int)
    role = request.args.get('role', '')
    search = request.args.get('search', '')
    
    query = User.query
    
    if role:
        query = query.filter_by(role=role)
    
    if search:
        query = query.filter(
            (User.name.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html',
                         users=pagination.items,
                         pagination=pagination,
                         current_role=role,
                         search=search)


@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    """User detail view."""
    user = User.query.get_or_404(user_id)
    
    # User's orders
    orders = Order.query.filter_by(customer_id=user_id).order_by(
        Order.created_at.desc()
    ).limit(10).all()
    
    return render_template('admin/user_detail.html', user=user, orders=orders)


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Activate/deactivate user."""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot deactivate yourself.', 'danger')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User has been {status}.', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))


# --- Order Monitoring ---
@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    """All orders."""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Order.query
    
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/orders.html',
                         orders=pagination.items,
                         pagination=pagination,
                         current_status=status)


# --- Review Moderation ---
@admin_bp.route('/reviews')
@login_required
@admin_required
def reviews():
    """Review moderation."""
    page = request.args.get('page', 1, type=int)
    
    pagination = Review.query.order_by(
        Review.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/reviews.html',
                         reviews=pagination.items,
                         pagination=pagination)


@admin_bp.route('/reviews/<int:review_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_review(review_id):
    """Toggle review visibility."""
    review = Review.query.get_or_404(review_id)
    review.is_visible = not review.is_visible
    
    # Update bakery rating
    review.bakery.update_rating()
    
    db.session.commit()
    
    status = 'visible' if review.is_visible else 'hidden'
    flash(f'Review is now {status}.', 'success')
    return redirect(url_for('admin.reviews'))


@admin_bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_review(review_id):
    """Delete a review."""
    review = Review.query.get_or_404(review_id)
    bakery = review.bakery
    
    db.session.delete(review)
    db.session.commit()
    
    # Update bakery rating after deletion
    bakery.update_rating()
    
    flash('Review deleted successfully.', 'success')
    return redirect(url_for('admin.reviews'))


# --- Platform Coupons ---
@admin_bp.route('/coupons')
@login_required
@admin_required
def coupons():
    """Platform-wide coupons."""
    # Platform coupons (no bakery_id)
    platform_coupons = Coupon.query.filter_by(
        bakery_id=None
    ).order_by(Coupon.created_at.desc()).all()
    
    # All coupons
    all_coupons = Coupon.query.order_by(
        Coupon.created_at.desc()
    ).limit(50).all()
    
    return render_template('admin/coupons.html',
                         platform_coupons=platform_coupons,
                         all_coupons=all_coupons)


@admin_bp.route('/coupons/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_coupon():
    """Add platform-wide coupon."""
    if request.method == 'POST':
        valid_until = request.form.get('valid_until')
        
        coupon = Coupon(
            bakery_id=None,  # Platform-wide
            code=request.form.get('code').upper(),
            description=request.form.get('description'),
            discount_type=request.form.get('discount_type'),
            discount_value=float(request.form.get('discount_value', 0)),
            min_order_amount=float(request.form.get('min_order_amount', 0)),
            max_discount=float(request.form.get('max_discount', 0)) or None,
            usage_limit=int(request.form.get('usage_limit', 0)) or None,
            valid_until=datetime.strptime(valid_until, '%Y-%m-%d') if valid_until else None
        )
        
        db.session.add(coupon)
        db.session.commit()
        
        flash('Platform coupon created!', 'success')
        return redirect(url_for('admin.coupons'))
    
    return render_template('admin/coupon_form.html')


@admin_bp.route('/coupons/<int:coupon_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_coupon(coupon_id):
    """Toggle coupon active status."""
    coupon = Coupon.query.get_or_404(coupon_id)
    coupon.is_active = not coupon.is_active
    db.session.commit()
    
    flash('Coupon status updated!', 'success')
    return redirect(url_for('admin.coupons'))


@admin_bp.route('/coupons/<int:coupon_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_coupon(coupon_id):
    """Edit platform coupon."""
    coupon = Coupon.query.get_or_404(coupon_id)
    
    if request.method == 'POST':
        valid_until = request.form.get('valid_until')
        
        coupon.code = request.form.get('code').upper()
        coupon.description = request.form.get('description')
        coupon.discount_type = request.form.get('discount_type')
        coupon.discount_value = float(request.form.get('discount_value', 0))
        coupon.min_order_amount = float(request.form.get('min_order_amount', 0))
        coupon.max_discount = float(request.form.get('max_discount', 0)) or None
        coupon.usage_limit = int(request.form.get('usage_limit', 0)) or None
        coupon.valid_until = datetime.strptime(valid_until, '%Y-%m-%d') if valid_until else None
        
        db.session.commit()
        flash('Coupon updated!', 'success')
        return redirect(url_for('admin.coupons'))
    
    return render_template('admin/coupon_form.html', coupon=coupon)


# --- Contact Messages ---
@admin_bp.route('/messages')
@login_required
@admin_required
def messages():
    """Contact messages."""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = ContactMessage.query
    
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(
        ContactMessage.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/contact_messages.html',
                         messages=pagination.items,
                         pagination=pagination,
                         current_status=status)


@admin_bp.route('/messages/<int:message_id>/mark-read', methods=['POST'])
@login_required
@admin_required
def mark_message_read(message_id):
    """Mark message as read."""
    message = ContactMessage.query.get_or_404(message_id)
    message.status = 'read'
    db.session.commit()
    
    flash('Message marked as read.', 'success')
    return redirect(url_for('admin.messages'))


# --- Reports ---
@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    """Platform reports."""
    # Date range
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=30)
    month_start = end_date.replace(day=1)
    
    # Total counts
    total_users = User.query.count()
    total_bakeries = Bakery.query.count()
    total_orders = Order.query.count()
    
    # Total revenue
    total_revenue = db.session.query(
        func.sum(Order.total_amount)
    ).filter(Order.status == 'delivered').scalar() or 0
    
    # This month stats
    this_month_orders = Order.query.filter(
        func.date(Order.created_at) >= month_start
    ).count()
    
    this_month_revenue = db.session.query(
        func.sum(Order.total_amount)
    ).filter(
        Order.status == 'delivered',
        func.date(Order.created_at) >= month_start
    ).scalar() or 0
    
    new_users = User.query.filter(
        func.date(User.created_at) >= month_start
    ).count()
    
    new_bakeries = Bakery.query.filter(
        func.date(Bakery.created_at) >= month_start
    ).count()
    
    # Top bakeries by revenue
    top_bakeries = db.session.query(
        Bakery,
        func.sum(Order.total_amount).label('revenue')
    ).join(Order).filter(
        Order.status == 'delivered'
    ).group_by(Bakery.id).order_by(
        func.sum(Order.total_amount).desc()
    ).limit(10).all()
    
    return render_template('admin/reports.html',
                         total_users=total_users,
                         total_bakeries=total_bakeries,
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         this_month_orders=this_month_orders,
                         this_month_revenue=this_month_revenue,
                         new_users=new_users,
                         new_bakeries=new_bakeries,
                         top_bakeries=top_bakeries)

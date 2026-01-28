"""Baker dashboard routes."""

import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models import (Bakery, Category, Product, Order, OrderItem, 
                        Review, Coupon, Notification)
from app.utils.decorators import baker_required, baker_or_pending_required

baker_bp = Blueprint('baker', __name__)


def allowed_file(filename):
    """Check if file extension is allowed."""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file(file, folder):
    """Save uploaded file and return filename."""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
        file.save(filepath)
        return filename
    return None


@baker_bp.route('/pending')
@baker_or_pending_required
def pending_approval():
    """Pending approval page for bakers."""
    if current_user.bakery and current_user.bakery.is_approved:
        return redirect(url_for('baker.dashboard'))
    return render_template('baker/pending_approval.html')


@baker_bp.route('/dashboard')
@login_required
@baker_required
def dashboard():
    """Baker dashboard with overview."""
    bakery = current_user.bakery
    
    # Today's orders
    today = datetime.utcnow().date()
    today_orders = Order.query.filter(
        Order.bakery_id == bakery.id,
        func.date(Order.created_at) == today
    ).all()
    
    today_revenue = sum(o.total_amount for o in today_orders if o.status == 'delivered')
    
    # Pending orders (need action)
    pending_orders = Order.query.filter(
        Order.bakery_id == bakery.id,
        Order.status.in_(['pending', 'confirmed', 'preparing'])
    ).order_by(Order.created_at.asc()).all()
    
    # Recent orders
    recent_orders = Order.query.filter_by(
        bakery_id=bakery.id
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    # Statistics
    total_products = Product.query.filter_by(bakery_id=bakery.id).count()
    total_orders = Order.query.filter_by(bakery_id=bakery.id).count()
    
    return render_template('baker/dashboard.html',
                         bakery=bakery,
                         today_orders=len(today_orders),
                         today_revenue=today_revenue,
                         pending_orders=pending_orders,
                         recent_orders=recent_orders,
                         total_products=total_products,
                         total_orders=total_orders)


@baker_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@baker_required
def profile():
    """Baker profile / bakery settings."""
    bakery = current_user.bakery
    
    if request.method == 'POST':
        bakery.name = request.form.get('name')
        bakery.description = request.form.get('description')
        bakery.address = request.form.get('address')
        bakery.city = request.form.get('city')
        bakery.pincode = request.form.get('pincode')
        bakery.phone = request.form.get('phone')
        bakery.min_order_amount = float(request.form.get('min_order_amount', 0))
        bakery.delivery_fee = float(request.form.get('delivery_fee', 0))
        bakery.delivery_time_mins = int(request.form.get('delivery_time_mins', 30))
        
        # Handle logo upload
        if 'logo' in request.files:
            logo = request.files['logo']
            if logo.filename:
                filename = save_file(logo, 'bakeries')
                if filename:
                    bakery.logo_url = filename
        
        # Handle banner upload
        if 'banner' in request.files:
            banner = request.files['banner']
            if banner.filename:
                filename = save_file(banner, 'bakeries')
                if filename:
                    bakery.banner_url = filename
        
        db.session.commit()
        flash('Bakery profile updated successfully!', 'success')
        return redirect(url_for('baker.profile'))
    
    return render_template('baker/profile.html', bakery=bakery)


@baker_bp.route('/toggle-status', methods=['POST'])
@login_required
@baker_required
def toggle_status():
    """Toggle bakery open/closed status."""
    bakery = current_user.bakery
    bakery.is_open = not bakery.is_open
    db.session.commit()
    
    status = 'open' if bakery.is_open else 'closed'
    flash(f'Bakery is now {status}.', 'success')
    return redirect(request.referrer or url_for('baker.dashboard'))


# --- Categories ---
@baker_bp.route('/categories')
@login_required
@baker_required
def categories():
    """Manage product categories."""
    bakery_categories = Category.query.filter_by(
        bakery_id=current_user.bakery.id
    ).order_by(Category.display_order).all()
    
    return render_template('baker/categories.html', bakery=current_user.bakery, categories=bakery_categories)


@baker_bp.route('/categories/add', methods=['POST'])
@login_required
@baker_required
def add_category():
    """Add new category."""
    name = request.form.get('name')
    
    category = Category(
        bakery_id=current_user.bakery.id,
        name=name,
        display_order=Category.query.filter_by(bakery_id=current_user.bakery.id).count()
    )
    db.session.add(category)
    db.session.commit()
    
    flash('Category added!', 'success')
    return redirect(url_for('baker.categories'))


@baker_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@baker_bp.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])  # Alias
@login_required
@baker_required
def edit_category(category_id):
    """Edit category."""
    category = Category.query.filter_by(
        id=category_id,
        bakery_id=current_user.bakery.id
    ).first_or_404()
    
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        
        flash('Category updated!', 'success')
        return redirect(url_for('baker.categories'))
    
    return render_template('baker/category_form.html', 
                          bakery=current_user.bakery, 
                          category=category)


@baker_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@baker_required
def delete_category(category_id):
    """Delete category."""
    category = Category.query.filter_by(
        id=category_id,
        bakery_id=current_user.bakery.id
    ).first_or_404()
    
    # Set products to uncategorized
    Product.query.filter_by(category_id=category_id).update({'category_id': None})
    
    db.session.delete(category)
    db.session.commit()
    
    flash('Category deleted!', 'success')
    return redirect(url_for('baker.categories'))


# --- Products ---
@baker_bp.route('/products')
@login_required
@baker_required
def products():
    """Product management."""
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', type=int)
    
    query = Product.query.filter_by(bakery_id=current_user.bakery.id)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    pagination = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    categories = Category.query.filter_by(bakery_id=current_user.bakery.id).all()
    
    return render_template('baker/products.html',
                         bakery=current_user.bakery,
                         products=pagination.items,
                         pagination=pagination,
                         categories=categories,
                         current_category=category_id)


@baker_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@baker_required
def add_product():
    """Add new product."""
    if request.method == 'POST':
        discount_price = request.form.get('discount_price')
        prep_time = request.form.get('preparation_time_mins')
        
        product = Product(
            bakery_id=current_user.bakery.id,
            category_id=request.form.get('category_id', type=int) or None,
            name=request.form.get('name'),
            description=request.form.get('description'),
            ingredients=request.form.get('ingredients'),
            price=float(request.form.get('price') or 0),
            discount_price=float(discount_price) if discount_price else None,
            stock_quantity=int(request.form.get('stock_quantity') or 0),
            is_available=request.form.get('is_available') == 'on',
            is_vegetarian=request.form.get('is_vegetarian') == 'on',
            is_bestseller=request.form.get('is_bestseller') == 'on',
            preparation_time_mins=int(prep_time) if prep_time else 15
        )
        
        # Handle image upload
        if 'image' in request.files:
            image = request.files['image']
            if image.filename:
                filename = save_file(image, 'products')
                if filename:
                    product.image_url = filename
        
        db.session.add(product)
        db.session.commit()
        
        flash('Product added successfully!', 'success')
        return redirect(url_for('baker.products'))
    
    categories = Category.query.filter_by(bakery_id=current_user.bakery.id).all()
    return render_template('baker/product_form.html', bakery=current_user.bakery, product=None, categories=categories)


@baker_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@baker_required
def edit_product(product_id):
    """Edit product."""
    product = Product.query.filter_by(
        id=product_id,
        bakery_id=current_user.bakery.id
    ).first_or_404()
    
    if request.method == 'POST':
        product.category_id = request.form.get('category_id', type=int) or None
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.ingredients = request.form.get('ingredients')
        product.price = float(request.form.get('price') or 0)
        discount_price = request.form.get('discount_price')
        product.discount_price = float(discount_price) if discount_price else None
        product.stock_quantity = int(request.form.get('stock_quantity') or 0)
        product.is_available = request.form.get('is_available') == 'on'
        product.is_vegetarian = request.form.get('is_vegetarian') == 'on'
        product.is_bestseller = request.form.get('is_bestseller') == 'on'
        prep_time = request.form.get('preparation_time_mins')
        product.preparation_time_mins = int(prep_time) if prep_time else 15
        
        # Handle image upload
        if 'image' in request.files:
            image = request.files['image']
            if image.filename:
                filename = save_file(image, 'products')
                if filename:
                    product.image_url = filename
        
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('baker.products'))
    
    categories = Category.query.filter_by(bakery_id=current_user.bakery.id).all()
    return render_template('baker/product_form.html', bakery=current_user.bakery, product=product, categories=categories)


@baker_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
@baker_required
def delete_product(product_id):
    """Delete product."""
    product = Product.query.filter_by(
        id=product_id,
        bakery_id=current_user.bakery.id
    ).first_or_404()
    
    db.session.delete(product)
    db.session.commit()
    
    flash('Product deleted!', 'success')
    return redirect(url_for('baker.products'))


@baker_bp.route('/products/<int:product_id>/toggle', methods=['POST'])
@login_required
@baker_required
def toggle_product(product_id):
    """Toggle product availability."""
    product = Product.query.filter_by(
        id=product_id,
        bakery_id=current_user.bakery.id
    ).first_or_404()
    
    product.is_available = not product.is_available
    db.session.commit()
    
    status = 'available' if product.is_available else 'unavailable'
    flash(f'Product is now {status}.', 'success')
    return redirect(url_for('baker.products'))


# --- Orders ---
@baker_bp.route('/orders')
@login_required
@baker_required
def orders():
    """Order management."""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Order.query.filter_by(bakery_id=current_user.bakery.id)
    
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('baker/orders.html',
                         bakery=current_user.bakery,
                         orders=pagination.items,
                         pagination=pagination,
                         current_status=status)


@baker_bp.route('/orders/<int:order_id>')
@login_required
@baker_required
def order_detail(order_id):
    """Order detail for baker."""
    order = Order.query.filter_by(
        id=order_id,
        bakery_id=current_user.bakery.id
    ).first_or_404()
    
    return render_template('baker/order_detail.html', bakery=current_user.bakery, order=order)


@baker_bp.route('/orders/<int:order_id>/update-status', methods=['POST'])
@login_required
@baker_required
def update_order_status(order_id):
    """Update order status."""
    order = Order.query.filter_by(
        id=order_id,
        bakery_id=current_user.bakery.id
    ).first_or_404()
    
    new_status = request.form.get('status')
    notes = request.form.get('notes', '')
    
    valid_transitions = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['preparing', 'cancelled'],
        'preparing': ['ready', 'cancelled'],
        'ready': ['out_for_delivery', 'delivered'],
        'out_for_delivery': ['delivered'],
    }
    
    if order.status in valid_transitions and new_status in valid_transitions.get(order.status, []):
        order.status = new_status
        order.add_status_history(new_status, notes)
        
        if new_status == 'delivered':
            order.delivered_at = datetime.utcnow()
        
        # Notify customer
        notification = Notification.create_order_notification(
            order.customer_id,
            order.order_number,
            new_status
        )
        db.session.add(notification)
        
        db.session.commit()
        flash(f'Order status updated to {new_status}.', 'success')
    else:
        flash('Invalid status transition.', 'danger')
    
    return redirect(url_for('baker.order_detail', order_id=order_id))


# --- Reviews ---
@baker_bp.route('/reviews')
@login_required
@baker_required
def reviews():
    """View and respond to reviews."""
    page = request.args.get('page', 1, type=int)
    
    pagination = Review.query.filter_by(
        bakery_id=current_user.bakery.id
    ).order_by(Review.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('baker/reviews.html',
                         bakery=current_user.bakery,
                         reviews=pagination.items,
                         pagination=pagination)


@baker_bp.route('/reviews/<int:review_id>/reply', methods=['POST'])
@login_required
@baker_required
def reply_review(review_id):
    """Reply to a customer review."""
    review = Review.query.filter_by(
        id=review_id,
        bakery_id=current_user.bakery.id
    ).first_or_404()
    
    review.reply = request.form.get('reply')
    review.reply_at = datetime.utcnow()
    db.session.commit()
    
    flash('Reply posted!', 'success')
    return redirect(url_for('baker.reviews'))


# --- Analytics ---
@baker_bp.route('/analytics')
@login_required
@baker_required
def analytics():
    """Sales analytics."""
    bakery = current_user.bakery
    
    # Date range
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=30)
    first_of_month = end_date.replace(day=1)
    
    # This month orders
    this_month_orders = Order.query.filter(
        Order.bakery_id == bakery.id,
        Order.status == 'delivered',
        func.date(Order.created_at) >= first_of_month
    ).count()
    
    # This month revenue
    this_month_revenue = db.session.query(
        func.sum(Order.total_amount)
    ).filter(
        Order.bakery_id == bakery.id,
        Order.status == 'delivered',
        func.date(Order.created_at) >= first_of_month
    ).scalar() or 0
    
    # Top products
    top_products = db.session.query(
        Product,
        func.sum(OrderItem.quantity).label('total_sold')
    ).join(OrderItem).join(Order).filter(
        Product.bakery_id == bakery.id,
        Order.status == 'delivered'
    ).group_by(Product.id).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(10).all()
    
    # Total stats
    total_revenue = db.session.query(
        func.sum(Order.total_amount)
    ).filter(
        Order.bakery_id == bakery.id,
        Order.status == 'delivered'
    ).scalar() or 0
    
    total_orders = Order.query.filter_by(
        bakery_id=bakery.id,
        status='delivered'
    ).count()
    
    total_products = Product.query.filter_by(bakery_id=bakery.id).count()
    
    # Average order value
    avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0
    
    return render_template('baker/analytics.html',
                         bakery=bakery,
                         this_month_orders=this_month_orders,
                         this_month_revenue=this_month_revenue,
                         avg_order_value=avg_order_value,
                         top_products=top_products,
                         total_revenue=total_revenue,
                         total_orders=total_orders,
                         total_products=total_products)


# --- Coupons ---
@baker_bp.route('/coupons')
@login_required
@baker_required
def coupons():
    """Manage coupons."""
    bakery_coupons = Coupon.query.filter_by(
        bakery_id=current_user.bakery.id
    ).order_by(Coupon.created_at.desc()).all()
    
    return render_template('baker/coupons.html', bakery=current_user.bakery, coupons=bakery_coupons)


@baker_bp.route('/coupons/add', methods=['GET', 'POST'])
@login_required
@baker_required
def add_coupon():
    """Add new coupon."""
    if request.method == 'GET':
        return render_template('baker/coupon_form.html', bakery=current_user.bakery, coupon=None)
    
    valid_until = request.form.get('valid_until')
    
    coupon = Coupon(
        bakery_id=current_user.bakery.id,
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
    
    flash('Coupon created!', 'success')
    return redirect(url_for('baker.coupons'))


@baker_bp.route('/coupons/<int:coupon_id>/toggle', methods=['POST'])
@login_required
@baker_required
def toggle_coupon(coupon_id):
    """Toggle coupon active status."""
    coupon = Coupon.query.filter_by(
        id=coupon_id,
        bakery_id=current_user.bakery.id
    ).first_or_404()
    
    coupon.is_active = not coupon.is_active
    db.session.commit()
    
    flash('Coupon status updated!', 'success')
    return redirect(url_for('baker.coupons'))


@baker_bp.route('/coupons/<int:coupon_id>/edit', methods=['GET', 'POST'])
@login_required
@baker_required
def edit_coupon(coupon_id):
    """Edit existing coupon."""
    coupon = Coupon.query.filter_by(
        id=coupon_id,
        bakery_id=current_user.bakery.id
    ).first_or_404()
    
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
        return redirect(url_for('baker.coupons'))
    
    return render_template('baker/coupon_form.html', bakery=current_user.bakery, coupon=coupon)


@baker_bp.route('/coupons/<int:coupon_id>/delete', methods=['POST'])
@login_required
@baker_required
def delete_coupon(coupon_id):
    """Delete coupon."""
    coupon = Coupon.query.filter_by(
        id=coupon_id,
        bakery_id=current_user.bakery.id
    ).first_or_404()
    
    db.session.delete(coupon)
    db.session.commit()
    
    flash('Coupon deleted!', 'success')
    return redirect(url_for('baker.coupons'))

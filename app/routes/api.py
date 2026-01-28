"""JSON API endpoints for AJAX operations."""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (CartItem, Product, Bakery, 
                        Notification, Coupon, Order)

api_bp = Blueprint('api', __name__)


@api_bp.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    """Add product to cart via AJAX."""
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    product = Product.query.get(product_id)
    if not product or not product.is_available:
        return jsonify({'success': False, 'message': 'Product not available'}), 400
    
    # Check existing items from different bakery
    existing_item = CartItem.query.filter_by(user_id=current_user.id).first()
    if existing_item and existing_item.product.bakery_id != product.bakery_id:
        return jsonify({
            'success': False, 
            'message': 'Cart contains items from different bakery',
            'requires_confirmation': True
        }), 400
    
    # Check if already in cart
    cart_item = CartItem.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(cart_item)
    
    db.session.commit()
    
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    return jsonify({
        'success': True, 
        'message': f'{product.name} added to cart',
        'cart_count': cart_count
    })


@api_bp.route('/cart/update', methods=['PUT'])
@login_required
def update_cart():
    """Update cart item quantity."""
    data = request.get_json()
    item_id = data.get('item_id')
    quantity = data.get('quantity', 1)
    
    cart_item = CartItem.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first()
    
    if not cart_item:
        return jsonify({'success': False, 'message': 'Item not found'}), 404
    
    if quantity <= 0:
        db.session.delete(cart_item)
    else:
        cart_item.quantity = quantity
    
    db.session.commit()
    
    # Calculate new totals
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    cart_total = sum(item.subtotal for item in cart_items)
    
    return jsonify({
        'success': True,
        'cart_count': len(cart_items),
        'cart_total': cart_total,
        'item_subtotal': cart_item.subtotal if quantity > 0 else 0
    })


@api_bp.route('/cart/remove/<int:item_id>', methods=['DELETE'])
@login_required
def remove_from_cart(item_id):
    """Remove item from cart."""
    cart_item = CartItem.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first()
    
    if not cart_item:
        return jsonify({'success': False, 'message': 'Item not found'}), 404
    
    db.session.delete(cart_item)
    db.session.commit()
    
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    return jsonify({'success': True, 'cart_count': cart_count})


@api_bp.route('/cart/count')
@login_required
def cart_count():
    """Get cart item count."""
    count = CartItem.query.filter_by(user_id=current_user.id).count()
    return jsonify({'count': count})


@api_bp.route('/notifications')
@login_required
def get_notifications():
    """Get user notifications."""
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).limit(10).all()
    
    unread_count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    return jsonify({
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.type,
            'link': n.link,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat()
        } for n in notifications],
        'unread_count': unread_count
    })


@api_bp.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    """Mark notifications as read."""
    data = request.get_json()
    notification_ids = data.get('ids', [])
    
    if notification_ids:
        Notification.query.filter(
            Notification.id.in_(notification_ids),
            Notification.user_id == current_user.id
        ).update({'is_read': True}, synchronize_session=False)
    else:
        # Mark all as read
        Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).update({'is_read': True})
    
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/search')
def search():
    """Search bakeries and products."""
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify({'bakeries': [], 'products': []})
    
    # Search bakeries
    bakeries = Bakery.query.filter(
        Bakery.is_approved == True,
        Bakery.name.ilike(f'%{query}%')
    ).limit(5).all()
    
    # Search products
    products = Product.query.join(Bakery).filter(
        Bakery.is_approved == True,
        Product.is_available == True,
        Product.name.ilike(f'%{query}%')
    ).limit(10).all()
    
    return jsonify({
        'bakeries': [{
            'id': b.id,
            'name': b.name,
            'slug': b.slug,
            'logo_url': b.logo_url,
            'rating': b.rating
        } for b in bakeries],
        'products': [{
            'id': p.id,
            'name': p.name,
            'price': p.current_price,
            'bakery_name': p.bakery.name,
            'bakery_slug': p.bakery.slug,
            'image_url': p.image_url
        } for p in products]
    })


@api_bp.route('/coupon/validate', methods=['POST'])
@login_required
def validate_coupon():
    """Validate a coupon code."""
    data = request.get_json()
    code = data.get('code', '').upper()
    order_amount = data.get('order_amount', 0)
    bakery_id = data.get('bakery_id')
    
    coupon = Coupon.query.filter_by(code=code).first()
    
    if not coupon:
        return jsonify({'valid': False, 'message': 'Invalid coupon code'})
    
    is_valid, message = coupon.is_valid(order_amount, bakery_id)
    
    if is_valid:
        discount = coupon.calculate_discount(order_amount)
        return jsonify({
            'valid': True,
            'message': f'Coupon applied! You save ₹{discount:.2f}',
            'discount': discount
        })
    else:
        return jsonify({'valid': False, 'message': message})


@api_bp.route('/order/<order_number>/status')
@login_required
def order_status(order_number):
    """Get order status for tracking."""
    order = Order.query.filter_by(order_number=order_number).first()
    
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404
    
    # Check access
    if order.customer_id != current_user.id and not current_user.is_admin():
        if not (current_user.is_baker() and current_user.bakery and 
                current_user.bakery.id == order.bakery_id):
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    status_history = [{
        'status': h.status,
        'notes': h.notes,
        'created_at': h.created_at.isoformat()
    } for h in order.status_history.order_by('created_at').all()]
    
    return jsonify({
        'success': True,
        'order_number': order.order_number,
        'status': order.status,
        'estimated_delivery': order.estimated_delivery.isoformat() if order.estimated_delivery else None,
        'status_history': status_history
    })

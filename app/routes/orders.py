"""Order routes."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app.extensions import db
from app.models import (Order, OrderItem, OrderStatusHistory, CartItem, 
                        Address, Coupon, Notification, Product)

orders_bp = Blueprint('orders', __name__)


@orders_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Checkout page."""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart.view_cart'))
    
    # Get bakery from first item (all items should be from same bakery)
    bakery = cart_items[0].product.bakery
    
    # Calculate totals
    subtotal = sum(item.subtotal for item in cart_items)
    delivery_fee = bakery.delivery_fee
    discount = 0
    
    # Check minimum order amount
    if subtotal < bakery.min_order_amount:
        flash(f'Minimum order amount is ₹{bakery.min_order_amount}', 'warning')
        return redirect(url_for('cart.view_cart'))
    
    # Get user addresses
    addresses = Address.query.filter_by(user_id=current_user.id).all()
    default_address = current_user.get_default_address()
    
    if request.method == 'POST':
        address_id = request.form.get('address_id', type=int)
        payment_method = request.form.get('payment_method', 'cod')
        special_instructions = request.form.get('special_instructions', '')
        coupon_code = request.form.get('coupon_code', '')
        
        # Validate address
        address = Address.query.filter_by(id=address_id, user_id=current_user.id).first()
        if not address:
            flash('Please select a valid delivery address.', 'danger')
            return redirect(url_for('orders.checkout'))
        
        # Apply coupon if provided
        if coupon_code:
            coupon = Coupon.query.filter_by(code=coupon_code.upper()).first()
            if coupon:
                is_valid, message = coupon.is_valid(subtotal, bakery.id)
                if is_valid:
                    discount = coupon.calculate_discount(subtotal)
                    coupon.used_count += 1
                else:
                    flash(message, 'warning')
        
        # Calculate final total
        total = subtotal + delivery_fee - discount
        
        # Create order
        order = Order(
            order_number=Order.generate_order_number(),
            customer_id=current_user.id,
            bakery_id=bakery.id,
            delivery_address_id=address_id,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            discount=discount,
            total_amount=total,
            payment_method=payment_method,
            special_instructions=special_instructions,
            estimated_delivery=datetime.utcnow() + timedelta(minutes=bakery.delivery_time_mins)
        )
        db.session.add(order)
        db.session.flush()
        
        # Create order items
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                product_name=cart_item.product.name,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.current_price,
                subtotal=cart_item.subtotal,
                special_instructions=cart_item.special_instructions
            )
            db.session.add(order_item)
            
            # Reduce stock
            cart_item.product.reduce_stock(cart_item.quantity)
        
        # Add status history
        order.add_status_history('pending', 'Order placed')
        
        # Clear cart
        CartItem.query.filter_by(user_id=current_user.id).delete()
        
        # Create notification for customer
        notification = Notification.create_order_notification(
            current_user.id, 
            order.order_number, 
            'pending'
        )
        notification.message = f'Your order #{order.order_number} has been placed successfully!'
        db.session.add(notification)
        
        db.session.commit()
        
        flash('Order placed successfully!', 'success')
        return redirect(url_for('orders.order_confirmation', order_number=order.order_number))
    
    return render_template('customer/checkout.html',
                         cart_items=cart_items,
                         bakery=bakery,
                         subtotal=subtotal,
                         delivery_fee=delivery_fee,
                         addresses=addresses,
                         default_address=default_address)


@orders_bp.route('/confirmation/<order_number>')
@login_required
def order_confirmation(order_number):
    """Order confirmation page."""
    order = Order.query.filter_by(
        order_number=order_number,
        customer_id=current_user.id
    ).first_or_404()
    
    return render_template('customer/order_confirmation.html', order=order)


@orders_bp.route('/')
@login_required
def order_history():
    """Order history."""
    page = request.args.get('page', 1, type=int)
    
    orders_query = Order.query.filter_by(
        customer_id=current_user.id
    ).order_by(Order.created_at.desc())
    
    pagination = orders_query.paginate(page=page, per_page=10, error_out=False)
    
    return render_template('customer/orders.html',
                         orders=pagination.items,
                         pagination=pagination)


@orders_bp.route('/<order_number>')
@login_required
def order_detail(order_number):
    """Order detail page."""
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    
    # Check access
    if order.customer_id != current_user.id and not current_user.is_admin():
        if not (current_user.is_baker() and current_user.bakery and 
                current_user.bakery.id == order.bakery_id):
            flash('Access denied.', 'danger')
            return redirect(url_for('main.index'))
    
    # Get status history
    status_history = order.status_history.order_by(
        OrderStatusHistory.created_at.desc()
    ).all()
    
    return render_template('customer/order_detail.html',
                         order=order,
                         status_history=status_history)


@orders_bp.route('/<order_number>/tracking')
@login_required
def order_tracking(order_number):
    """Order tracking page."""
    order = Order.query.filter_by(
        order_number=order_number,
        customer_id=current_user.id
    ).first_or_404()
    
    status_history = order.status_history.order_by(
        OrderStatusHistory.created_at.asc()
    ).all()
    
    return render_template('customer/order_tracking.html',
                         order=order,
                         status_history=status_history)


@orders_bp.route('/<order_number>/cancel', methods=['POST'])
@login_required
def cancel_order(order_number):
    """Cancel an order."""
    order = Order.query.filter_by(
        order_number=order_number,
        customer_id=current_user.id
    ).first_or_404()
    
    if not order.can_cancel():
        flash('This order cannot be cancelled.', 'danger')
        return redirect(url_for('orders.order_detail', order_number=order_number))
    
    reason = request.form.get('reason', 'Customer requested cancellation')
    order.status = 'cancelled'
    order.cancellation_reason = reason
    order.add_status_history('cancelled', reason)
    
    # Restore stock
    for item in order.items:
        item.product.stock_quantity += item.quantity
    
    db.session.commit()
    
    flash('Order cancelled successfully.', 'success')
    return redirect(url_for('orders.order_detail', order_number=order_number))


@orders_bp.route('/<order_number>/reorder', methods=['POST'])
@login_required
def reorder(order_number):
    """Reorder from a previous order."""
    order = Order.query.filter_by(
        order_number=order_number,
        customer_id=current_user.id
    ).first_or_404()
    
    # Clear current cart
    CartItem.query.filter_by(user_id=current_user.id).delete()
    
    # Add items from previous order
    for item in order.items:
        if item.product.is_available:
            cart_item = CartItem(
                user_id=current_user.id,
                product_id=item.product_id,
                quantity=item.quantity
            )
            db.session.add(cart_item)
    
    db.session.commit()
    
    flash('Items added to cart. Please review before checkout.', 'success')
    return redirect(url_for('cart.view_cart'))

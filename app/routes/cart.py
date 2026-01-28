"""Cart routes."""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import CartItem, Product, Bakery

cart_bp = Blueprint('cart', __name__)


@cart_bp.route('/')
@login_required
def view_cart():
    """View shopping cart."""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    # Group items by bakery
    bakeries = {}
    for item in cart_items:
        bakery_id = item.product.bakery_id
        if bakery_id not in bakeries:
            bakeries[bakery_id] = {
                'bakery': item.product.bakery,
                'cart_items': [],
                'subtotal': 0
            }
        bakeries[bakery_id]['cart_items'].append(item)
        bakeries[bakery_id]['subtotal'] += item.subtotal
    
    # Calculate totals
    cart_total = sum(b['subtotal'] for b in bakeries.values())
    
    return render_template('customer/cart.html',
                         bakeries=bakeries,
                         cart_total=cart_total)


@cart_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_to_cart():
    """Add product to cart."""
    # If accessed via GET, redirect to cart
    if request.method == 'GET':
        return redirect(url_for('cart.view_cart'))
    
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', 1, type=int)
    special_instructions = request.form.get('special_instructions', '')
    
    product = Product.query.get_or_404(product_id)
    
    # Check if product is available
    if not product.is_available or not product.bakery.is_approved:
        flash('This product is not available.', 'danger')
        return redirect(request.referrer or url_for('main.index'))
    
    # Check for existing cart item from different bakery
    existing_items = CartItem.query.filter_by(user_id=current_user.id).first()
    if existing_items and existing_items.product.bakery_id != product.bakery_id:
        # Clear cart and add new item (or ask user)
        if not request.form.get('replace_cart'):
            flash('Your cart contains items from a different bakery. Adding this will replace your cart.', 'warning')
            return render_template('customer/cart_replace_confirm.html', 
                                 product=product, 
                                 quantity=quantity)
        else:
            CartItem.query.filter_by(user_id=current_user.id).delete()
    
    # Check if already in cart
    cart_item = CartItem.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    
    if cart_item:
        cart_item.quantity += quantity
        cart_item.special_instructions = special_instructions or cart_item.special_instructions
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity,
            special_instructions=special_instructions
        )
        db.session.add(cart_item)
    
    db.session.commit()
    flash(f'{product.name} added to cart!', 'success')
    
    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({'success': True, 'cart_count': cart_count})
    
    return redirect(request.referrer or url_for('main.bakery_detail', slug=product.bakery.slug))


@cart_bp.route('/update', methods=['POST'])
@login_required
def update_cart():
    """Update cart item quantity."""
    item_id = request.form.get('item_id', type=int)
    quantity = request.form.get('quantity', type=int)
    
    cart_item = CartItem.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first_or_404()
    
    if quantity <= 0:
        db.session.delete(cart_item)
        message = 'Item removed from cart.'
    else:
        cart_item.quantity = quantity
        message = 'Cart updated.'
    
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({'success': True, 'cart_count': cart_count, 'message': message})
    
    flash(message, 'success')
    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    """Remove item from cart."""
    cart_item = CartItem.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first_or_404()
    
    db.session.delete(cart_item)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({'success': True, 'cart_count': cart_count})
    
    flash('Item removed from cart.', 'success')
    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/clear', methods=['POST'])
@login_required
def clear_cart():
    """Clear all items from cart."""
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    
    flash('Cart cleared.', 'success')
    return redirect(url_for('cart.view_cart'))

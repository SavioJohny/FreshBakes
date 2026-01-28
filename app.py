# FreshBakes - Local Development Version
# This is a simplified version for local testing without AWS services
# Uses in-memory dictionaries for data storage

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration for File Uploads
UPLOAD_FOLDER = 'app/static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directories exist
for sub_dir in ['bakeries', 'products', 'profiles']:
    os.makedirs(os.path.join(UPLOAD_FOLDER, sub_dir), exist_ok=True)

# In-memory database (dictionaries)
users = {}  # email -> {password_hash, name, phone, role, ...}
addresses = {}  # address_id -> {user_email, full_address, city, ...}
bakeries = {}  # bakery_id -> {owner_email, name, slug, ...}
categories = {}  # category_id -> {bakery_id, name, ...}
products = {}  # product_id -> {bakery_id, name, price, ...}
cart_items = {}  # user_email -> {product_id -> quantity, ...}
orders = {}  # order_number -> {customer_email, bakery_id, items, ...}
order_items = {}  # order_number -> [{product_id, quantity, price}, ...]
reviews = {}  # review_id -> {user_email, bakery_id, rating, ...}

# Helper function to generate slug
def generate_slug(name):
    """Generate a URL-friendly slug from name."""
    slug = name.lower().replace(' ', '-')
    slug = ''.join(c for c in slug if c.isalnum() or c == '-')
    return slug

# Helper function to check if user is logged in
def is_logged_in():
    return 'user_email' in session

def get_current_user():
    if not is_logged_in():
        return None
    email = session['user_email']
    return users.get(email)

def login_required(f):
    """Decorator to require login."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def baker_required(f):
    """Decorator to require baker role."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user.get('role') != 'baker':
            flash('Access denied.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user.get('role') != 'admin':
            flash('Access denied.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Context processor for cart count
@app.context_processor
def inject_globals():
    cart_count = 0
    if is_logged_in():
        user_cart = cart_items.get(session['user_email'], {})
        cart_count = sum(user_cart.values())
    return dict(cart_count=cart_count, current_user=get_current_user())

# ==================== PUBLIC ROUTES ====================

@app.route('/')
def index():
    """Homepage with featured bakeries."""
    featured = [b for b in bakeries.values() if b.get('is_approved') and b.get('is_featured')][:6]
    all_bakeries = [b for b in bakeries.values() if b.get('is_approved')][:8]
    popular = [p for p in products.values() if p.get('is_bestseller') and p.get('is_available')][:8]
    
    return render_template('main/index.html',
                          featured_bakeries=featured,
                          bakeries=all_bakeries,
                          popular_products=popular)

@app.route('/bakeries')
def bakeries_list():
    """List all bakeries."""
    search = request.args.get('search', '')
    city = request.args.get('city', '')
    
    result = [b for b in bakeries.values() if b.get('is_approved')]
    
    if search:
        result = [b for b in result if search.lower() in b['name'].lower()]
    if city:
        result = [b for b in result if city.lower() in b.get('city', '').lower()]
    
    cities = list(set(b.get('city', '') for b in bakeries.values() if b.get('is_approved')))
    
    return render_template('main/bakeries.html',
                          bakeries=result,
                          cities=cities,
                          search=search,
                          current_city=city)

@app.route('/bakery/<slug>')
def bakery_detail(slug):
    """Individual bakery page."""
    bakery = next((b for b in bakeries.values() if b.get('slug') == slug and b.get('is_approved')), None)
    if not bakery:
        return "Bakery not found", 404
    
    bakery_categories = [c for c in categories.values() if c.get('bakery_id') == bakery['bakery_id']]
    bakery_products = [p for p in products.values() if p.get('bakery_id') == bakery['bakery_id'] and p.get('is_available')]
    bakery_reviews = [r for r in reviews.values() if r.get('bakery_id') == bakery['bakery_id']]
    
    return render_template('main/bakery_detail.html',
                          bakery=bakery,
                          categories=bakery_categories,
                          products=bakery_products,
                          reviews=bakery_reviews)

@app.route('/product/<product_id>')
def product_detail(product_id):
    """Product detail page."""
    product = products.get(product_id)
    if not product:
        return "Product not found", 404
    
    bakery = bakeries.get(product.get('bakery_id'))
    related = [p for p in products.values() 
               if p.get('bakery_id') == product.get('bakery_id') 
               and p.get('product_id') != product_id][:4]
    
    return render_template('main/product_detail.html',
                          product=product,
                          bakery=bakery,
                          related_products=related)

@app.route('/search')
def search():
    """Search results page."""
    query = request.args.get('q', '')
    
    found_bakeries = [b for b in bakeries.values() 
                      if b.get('is_approved') and query.lower() in b['name'].lower()][:6]
    found_products = [p for p in products.values() 
                      if p.get('is_available') and query.lower() in p['name'].lower()][:12]
    
    return render_template('main/search_results.html',
                          query=query,
                          bakeries=found_bakeries,
                          products=found_products)

@app.route('/about')
def about():
    return render_template('main/about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash('Thank you for your message!', 'success')
        return redirect(url_for('contact'))
    return render_template('main/contact.html')

@app.route('/faq')
def faq():
    return render_template('main/faq.html')

@app.route('/terms')
def terms():
    return render_template('main/terms.html')

@app.route('/privacy')
def privacy():
    return render_template('main/privacy.html')

@app.route('/become-a-baker')
def become_baker():
    return render_template('main/become_baker.html')

# ==================== AUTH ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if is_logged_in():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        password = request.form.get('password', '')
        
        user = users.get(email)
        if user and check_password_hash(user['password_hash'], password):
            if not user.get('is_active', True):
                flash('Your account has been deactivated.', 'danger')
                return render_template('auth/login.html')
            
            session['user_email'] = email
            flash(f"Welcome back, {user['name']}!", 'success')
            
            if user.get('role') == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.get('role') == 'baker':
                return redirect(url_for('baker_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Customer registration."""
    if is_logged_in():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        password = request.form.get('password', '')
        name = request.form.get('name', '')
        phone = request.form.get('phone', '')
        
        if email in users:
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html')
        
        users[email] = {
            'email': email,
            'password_hash': generate_password_hash(password),
            'name': name,
            'phone': phone,
            'role': 'customer',
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html')

@app.route('/register/baker', methods=['GET', 'POST'])
def register_baker():
    """Baker registration."""
    if is_logged_in():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        password = request.form.get('password', '')
        name = request.form.get('name', '')
        phone = request.form.get('phone', '')
        bakery_name = request.form.get('bakery_name', '')
        bakery_address = request.form.get('bakery_address', '')
        city = request.form.get('city', '')
        pincode = request.form.get('pincode', '')
        
        if email in users:
            flash('Email already registered.', 'danger')
            return render_template('auth/register_baker.html')
        
        # Create user
        users[email] = {
            'email': email,
            'password_hash': generate_password_hash(password),
            'name': name,
            'phone': phone,
            'role': 'baker',
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Create bakery
        bakery_id = str(uuid.uuid4())
        bakeries[bakery_id] = {
            'bakery_id': bakery_id,
            'owner_email': email,
            'name': bakery_name,
            'slug': generate_slug(bakery_name),
            'address': bakery_address,
            'city': city,
            'pincode': pincode,
            'phone': phone,
            'is_approved': False,
            'is_open': True,
            'is_featured': False,
            'rating': 0.0,
            'created_at': datetime.utcnow().isoformat()
        }
        
        flash('Registration submitted! Your bakery is pending admin approval.', 'info')
        return redirect(url_for('login'))
    
    return render_template('auth/register_baker.html')

@app.route('/logout')
def logout():
    """User logout."""
    session.pop('user_email', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ==================== CART ROUTES ====================

@app.route('/cart')
@login_required
def view_cart():
    """View shopping cart."""
    user_email = session['user_email']
    user_cart = cart_items.get(user_email, {})
    
    cart_data = []
    total = 0
    for product_id, quantity in user_cart.items():
        product = products.get(product_id)
        if product:
            subtotal = product.get('price', 0) * quantity
            cart_data.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
            total += subtotal
    
    return render_template('customer/cart.html',
                          cart_items=cart_data,
                          cart_total=total)

@app.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    """Add product to cart."""
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    
    product = products.get(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(request.referrer or url_for('index'))
    
    user_email = session['user_email']
    if user_email not in cart_items:
        cart_items[user_email] = {}
    
    if product_id in cart_items[user_email]:
        cart_items[user_email][product_id] += quantity
    else:
        cart_items[user_email][product_id] = quantity
    
    flash(f"{product['name']} added to cart!", 'success')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'cart_count': sum(cart_items[user_email].values())})
    
    return redirect(request.referrer or url_for('view_cart'))

@app.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    """Update cart item quantity."""
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 0))
    
    user_email = session['user_email']
    if user_email in cart_items and product_id in cart_items[user_email]:
        if quantity <= 0:
            del cart_items[user_email][product_id]
            flash('Item removed from cart.', 'success')
        else:
            cart_items[user_email][product_id] = quantity
            flash('Cart updated.', 'success')
    
    return redirect(url_for('view_cart'))

@app.route('/cart/remove/<product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    """Remove item from cart."""
    user_email = session['user_email']
    if user_email in cart_items and product_id in cart_items[user_email]:
        del cart_items[user_email][product_id]
        flash('Item removed from cart.', 'success')
    
    return redirect(url_for('view_cart'))

@app.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    """Clear all items from cart."""
    user_email = session['user_email']
    cart_items[user_email] = {}
    flash('Cart cleared.', 'success')
    return redirect(url_for('view_cart'))

# ==================== ORDER ROUTES ====================

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Checkout page."""
    user_email = session['user_email']
    user_cart = cart_items.get(user_email, {})
    
    if not user_cart:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('view_cart'))
    
    if request.method == 'POST':
        # Create order
        order_number = f"LC{datetime.utcnow().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().hex)[:6].upper()}"
        
        items = []
        total = 0
        bakery_id = None
        for product_id, quantity in user_cart.items():
            product = products.get(product_id)
            if product:
                subtotal = product['price'] * quantity
                items.append({
                    'product_id': product_id,
                    'product_name': product['name'],
                    'quantity': quantity,
                    'unit_price': product['price'],
                    'subtotal': subtotal
                })
                total += subtotal
                bakery_id = product.get('bakery_id')
        
        orders[order_number] = {
            'order_number': order_number,
            'customer_email': user_email,
            'bakery_id': bakery_id,
            'items': items,
            'total_amount': total,
            'status': 'pending',
            'payment_method': request.form.get('payment_method', 'cod'),
            'delivery_address': request.form.get('address', ''),
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Clear cart
        cart_items[user_email] = {}
        
        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_confirmation', order_number=order_number))
    
    # Get user addresses
    user_addresses = [a for a in addresses.values() if a.get('user_email') == user_email]
    
    cart_data = []
    total = 0
    for product_id, quantity in user_cart.items():
        product = products.get(product_id)
        if product:
            subtotal = product['price'] * quantity
            cart_data.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
            total += subtotal
    
    return render_template('customer/checkout.html',
                          cart_items=cart_data,
                          cart_total=total,
                          addresses=user_addresses)

@app.route('/order/<order_number>')
@login_required
def order_confirmation(order_number):
    """Order confirmation page."""
    order = orders.get(order_number)
    if not order or order['customer_email'] != session['user_email']:
        return "Order not found", 404
    
    return render_template('customer/order_confirmation.html', order=order)

@app.route('/orders')
@login_required
def order_history():
    """Order history."""
    user_email = session['user_email']
    user_orders = [o for o in orders.values() if o['customer_email'] == user_email]
    user_orders.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('customer/order_history.html', orders=user_orders)

@app.route('/orders/<order_number>')
@login_required
def order_detail(order_number):
    """Order detail page."""
    order = orders.get(order_number)
    if not order or order['customer_email'] != session['user_email']:
        return "Order not found", 404
    
    bakery = bakeries.get(order.get('bakery_id'))
    
    return render_template('customer/order_detail.html', order=order, bakery=bakery)

# ==================== BAKER ROUTES ====================

@app.route('/baker/dashboard')
@login_required
@baker_required
def baker_dashboard():
    """Baker dashboard."""
    user_email = session['user_email']
    bakery = next((b for b in bakeries.values() if b['owner_email'] == user_email), None)
    
    if not bakery:
        flash('No bakery found for your account.', 'danger')
        return redirect(url_for('index'))
    
    bakery_orders = [o for o in orders.values() if o.get('bakery_id') == bakery['bakery_id']]
    bakery_products = [p for p in products.values() if p.get('bakery_id') == bakery['bakery_id']]
    
    return render_template('baker/dashboard.html',
                          bakery=bakery,
                          orders=bakery_orders,
                          products=bakery_products)

@app.route('/baker/products')
@login_required
@baker_required
def baker_products():
    """Baker products list."""
    user_email = session['user_email']
    bakery = next((b for b in bakeries.values() if b['owner_email'] == user_email), None)
    
    if not bakery:
        return redirect(url_for('baker_dashboard'))
    
    bakery_products = [p for p in products.values() if p.get('bakery_id') == bakery['bakery_id']]
    bakery_categories = [c for c in categories.values() if c.get('bakery_id') == bakery['bakery_id']]
    
    return render_template('baker/products.html',
                          bakery=bakery,
                          products=bakery_products,
                          categories=bakery_categories)

@app.route('/baker/products/add', methods=['GET', 'POST'])
@login_required
@baker_required
def baker_add_product():
    """Add new product."""
    user_email = session['user_email']
    bakery = next((b for b in bakeries.values() if b['owner_email'] == user_email), None)
    
    if not bakery:
        return redirect(url_for('baker_dashboard'))
    
    if request.method == 'POST':
        product_id = str(uuid.uuid4())
        
        # Handle image upload
        image_filename = 'default-product.png'
        if 'image' in request.files:
            image = request.files['image']
            if image.filename:
                image_filename = secure_filename(f"{product_id}_{image.filename}")
                image.save(os.path.join(UPLOAD_FOLDER, 'products', image_filename))
        
        products[product_id] = {
            'product_id': product_id,
            'bakery_id': bakery['bakery_id'],
            'category_id': request.form.get('category_id'),
            'name': request.form.get('name'),
            'description': request.form.get('description', ''),
            'price': float(request.form.get('price', 0)),
            'discount_price': float(request.form.get('discount_price', 0)) or None,
            'image_url': image_filename,
            'stock_quantity': int(request.form.get('stock_quantity', 0)),
            'is_available': True,
            'is_vegetarian': request.form.get('is_vegetarian') == 'on',
            'is_bestseller': False,
            'created_at': datetime.utcnow().isoformat()
        }
        
        flash('Product added successfully!', 'success')
        return redirect(url_for('baker_products'))
    
    bakery_categories = [c for c in categories.values() if c.get('bakery_id') == bakery['bakery_id']]
    
    return render_template('baker/add_product.html',
                          bakery=bakery,
                          categories=bakery_categories)

@app.route('/baker/orders')
@login_required
@baker_required
def baker_orders():
    """Baker orders list."""
    user_email = session['user_email']
    bakery = next((b for b in bakeries.values() if b['owner_email'] == user_email), None)
    
    if not bakery:
        return redirect(url_for('baker_dashboard'))
    
    bakery_orders = [o for o in orders.values() if o.get('bakery_id') == bakery['bakery_id']]
    bakery_orders.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('baker/orders.html',
                          bakery=bakery,
                          orders=bakery_orders)

@app.route('/baker/orders/<order_number>/update', methods=['POST'])
@login_required
@baker_required
def baker_update_order(order_number):
    """Update order status."""
    order = orders.get(order_number)
    if order:
        order['status'] = request.form.get('status', order['status'])
        flash('Order status updated.', 'success')
    
    return redirect(url_for('baker_orders'))

# ==================== ADMIN ROUTES ====================

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard."""
    return render_template('admin/dashboard.html',
                          users=users,
                          bakeries=bakeries,
                          orders=orders,
                          products=products)

@app.route('/admin/bakeries')
@login_required
@admin_required
def admin_bakeries():
    """Admin bakeries management."""
    return render_template('admin/bakeries.html', bakeries=bakeries)

@app.route('/admin/bakeries/<bakery_id>/approve', methods=['POST'])
@login_required
@admin_required
def admin_approve_bakery(bakery_id):
    """Approve bakery."""
    if bakery_id in bakeries:
        bakeries[bakery_id]['is_approved'] = True
        flash('Bakery approved.', 'success')
    
    return redirect(url_for('admin_bakeries'))

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Admin users management."""
    return render_template('admin/users.html', users=users)

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    """Admin orders management."""
    return render_template('admin/orders.html', orders=orders)

# ==================== CUSTOMER PROFILE ROUTES ====================

@app.route('/profile')
@login_required
def profile():
    """User profile page."""
    user = get_current_user()
    user_addresses = [a for a in addresses.values() if a.get('user_email') == session['user_email']]
    
    return render_template('customer/profile.html',
                          user=user,
                          addresses=user_addresses)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile."""
    user_email = session['user_email']
    user = users.get(user_email)
    
    if request.method == 'POST':
        user['name'] = request.form.get('name', user['name'])
        user['phone'] = request.form.get('phone', user.get('phone', ''))
        flash('Profile updated.', 'success')
        return redirect(url_for('profile'))
    
    return render_template('customer/edit_profile.html', user=user)

@app.route('/addresses/add', methods=['GET', 'POST'])
@login_required
def add_address():
    """Add new address."""
    if request.method == 'POST':
        address_id = str(uuid.uuid4())
        addresses[address_id] = {
            'address_id': address_id,
            'user_email': session['user_email'],
            'label': request.form.get('label', 'Home'),
            'full_address': request.form.get('full_address'),
            'city': request.form.get('city'),
            'pincode': request.form.get('pincode'),
            'is_default': len([a for a in addresses.values() if a.get('user_email') == session['user_email']]) == 0
        }
        flash('Address added.', 'success')
        return redirect(url_for('profile'))
    
    return render_template('customer/add_address.html')

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    # Create a default admin user for testing
    users['admin@freshbakes.com'] = {
        'email': 'admin@freshbakes.com',
        'password_hash': generate_password_hash('admin123'),
        'name': 'Admin User',
        'phone': '1234567890',
        'role': 'admin',
        'is_active': True,
        'created_at': datetime.utcnow().isoformat()
    }
    
    app.run(debug=True, host='0.0.0.0', port=5000)

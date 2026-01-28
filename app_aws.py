# FreshBakes - AWS Deployment Version
# Uses DynamoDB for data storage and SNS for notifications
# Deploy this file on EC2 with appropriate IAM role

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import uuid
import boto3
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from decimal import Decimal

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.secret_key = os.environ.get('SECRET_KEY', 'production-secret-key-change-this')

# ==================== AWS CONFIGURATION ====================

# AWS Region - Update this to your region
REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=REGION)
sns = boto3.client('sns', region_name=REGION)

# DynamoDB Tables (Create these in AWS Console first)
users_table = dynamodb.Table('FreshBakes_Users')
addresses_table = dynamodb.Table('FreshBakes_Addresses')
bakeries_table = dynamodb.Table('FreshBakes_Bakeries')
categories_table = dynamodb.Table('FreshBakes_Categories')
products_table = dynamodb.Table('FreshBakes_Products')
cart_items_table = dynamodb.Table('FreshBakes_CartItems')
orders_table = dynamodb.Table('FreshBakes_Orders')
order_items_table = dynamodb.Table('FreshBakes_OrderItems')
reviews_table = dynamodb.Table('FreshBakes_Reviews')

# SNS Topic ARN - Replace with your actual SNS Topic ARN
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:307946664606:FreshBakes')

# Configuration for File Uploads
UPLOAD_FOLDER = 'app/static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directories exist
for sub_dir in ['bakeries', 'products', 'profiles']:
    os.makedirs(os.path.join(UPLOAD_FOLDER, sub_dir), exist_ok=True)

# ==================== HELPER FUNCTIONS ====================

def send_notification(subject, message):
    """Send SNS notification."""
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
    except ClientError as e:
        print(f"Error sending notification: {e}")

@app.template_filter('format_decimal')
def format_decimal_filter(value, decimals=2):
    """Format Decimal/float for display in templates."""
    try:
        # Helper to convert Decimal to float for formatting, if needed
        def decimal_to_float(d):
            if isinstance(d, Decimal):
                return float(d)
            return d
        return f"{decimal_to_float(value):.{decimals}f}"
    except:
        return "0.00"

@app.template_filter('format_date')
def format_date_filter(value, format='%b %d, %Y'):
    """Format date string or datetime object."""
    if not value:
        return ''
    if isinstance(value, str):
        try:
            # Handle ISO format
            if 'T' in value:
                value = datetime.fromisoformat(value)
            else:
                # Try simple date format
                value = datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return value
    return value.strftime(format)

def generate_slug(name):
    """Generate a URL-friendly slug from name."""
    slug = name.lower().replace(' ', '-')
    slug = ''.join(c for c in slug if c.isalnum() or c == '-')
    return slug

def is_logged_in():
    return 'user_email' in session

def get_current_user():
    if not is_logged_in():
        return None
    email = session['user_email']
    try:
        response = users_table.get_item(Key={'email': email})
        return response.get('Item')
    except ClientError:
        return None

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
    current_user = None
    if is_logged_in():
        current_user = get_current_user()
        try:
            response = cart_items_table.query(
                KeyConditionExpression=Key('user_email').eq(session['user_email'])
            )
            cart_count = sum(item.get('quantity', 0) for item in response.get('Items', []))
        except ClientError:
            pass
    return dict(cart_count=cart_count, current_user=current_user)

# ==================== PUBLIC ROUTES ====================

@app.route('/')
def index():
    """Homepage with featured bakeries."""
    try:
        # Get all approved bakeries
        response = bakeries_table.scan(
            FilterExpression=Attr('is_approved').eq(True)
        )
        all_bakeries = response.get('Items', [])
        
        featured = [b for b in all_bakeries if b.get('is_featured')][:6]
        
        # Get bestseller products
        prod_response = products_table.scan(
            FilterExpression=Attr('is_bestseller').eq(True) & Attr('is_available').eq(True)
        )
        popular = prod_response.get('Items', [])[:8]
    except ClientError as e:
        print(f"Error: {e}")
        all_bakeries = []
        featured = []
        popular = []
    
    return render_template('main/index.html',
                          featured_bakeries=featured,
                          bakeries=all_bakeries[:8],
                          popular_products=popular)

@app.route('/bakeries')
def bakeries_list():
    """List all bakeries."""
    search = request.args.get('search', '')
    city = request.args.get('city', '')
    
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('is_approved').eq(True)
        )
        result = response.get('Items', [])
        
        if search:
            result = [b for b in result if search.lower() in b.get('name', '').lower()]
        if city:
            result = [b for b in result if city.lower() in b.get('city', '').lower()]
        
        cities = list(set(b.get('city', '') for b in response.get('Items', [])))
    except ClientError:
        result = []
        cities = []
    
    return render_template('main/bakeries.html',
                          bakeries=result,
                          cities=cities,
                          search=search,
                          current_city=city)

@app.route('/bakery/<slug>')
def bakery_detail(slug):
    """Individual bakery page."""
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('slug').eq(slug) & Attr('is_approved').eq(True)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            return "Bakery not found", 404
        bakery = bakeries_list[0]
        
        # Get categories
        cat_response = categories_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id'])
        )
        bakery_categories = cat_response.get('Items', [])
        
        # Get products
        prod_response = products_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id']) & Attr('is_available').eq(True)
        )
        bakery_products = prod_response.get('Items', [])
        
        # Get reviews
        rev_response = reviews_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id'])
        )
        bakery_reviews = rev_response.get('Items', [])
        
    except ClientError as e:
        print(f"Error: {e}")
        return "Error loading bakery", 500
    
    return render_template('main/bakery_detail.html',
                          bakery=bakery,
                          categories=bakery_categories,
                          products=bakery_products,
                          reviews=bakery_reviews)

@app.route('/product/<product_id>')
def product_detail(product_id):
    """Product detail page."""
    try:
        response = products_table.get_item(Key={'product_id': product_id})
        product = response.get('Item')
        if not product:
            return "Product not found", 404
        
        bakery_response = bakeries_table.get_item(Key={'bakery_id': product.get('bakery_id')})
        bakery = bakery_response.get('Item')
        
        # Get related products
        related_response = products_table.scan(
            FilterExpression=Attr('bakery_id').eq(product.get('bakery_id')) & Attr('product_id').ne(product_id)
        )
        related = related_response.get('Items', [])[:4]
    except ClientError as e:
        print(f"Error: {e}")
        return "Error loading product", 500
    
    return render_template('main/product_detail.html',
                          product=product,
                          bakery=bakery,
                          related_products=related)

@app.route('/search')
def search():
    """Search results page."""
    query = request.args.get('q', '')
    
    try:
        bakery_response = bakeries_table.scan(FilterExpression=Attr('is_approved').eq(True))
        all_bakeries = bakery_response.get('Items', [])
        found_bakeries = [b for b in all_bakeries if query.lower() in b.get('name', '').lower()][:6]
        
        prod_response = products_table.scan(FilterExpression=Attr('is_available').eq(True))
        all_products = prod_response.get('Items', [])
        found_products = [p for p in all_products if query.lower() in p.get('name', '').lower()][:12]
    except ClientError:
        found_bakeries = []
        found_products = []
    
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
        send_notification("Contact Form Submission", 
                         f"From: {request.form.get('name')} ({request.form.get('email')})\n"
                         f"Subject: {request.form.get('subject')}\n"
                         f"Message: {request.form.get('message')}")
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
        
        try:
            response = users_table.get_item(Key={'email': email})
            user = response.get('Item')
            
            if user and check_password_hash(user['password_hash'], password):
                if not user.get('is_active', True):
                    flash('Your account has been deactivated.', 'danger')
                    return render_template('auth/login.html')
                
                session['user_email'] = email
                send_notification("User Login", f"User {email} has logged in.")
                flash(f"Welcome back, {user['name']}!", 'success')
                
                if user.get('role') == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user.get('role') == 'baker':
                    return redirect(url_for('baker_dashboard'))
                else:
                    return redirect(url_for('index'))
            else:
                flash('Invalid email or password.', 'danger')
        except ClientError as e:
            print(f"Login error: {e}")
            flash('An error occurred. Please try again.', 'danger')
    
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
        
        try:
            # Check if user exists
            response = users_table.get_item(Key={'email': email})
            if 'Item' in response:
                flash('Email already registered.', 'danger')
                return render_template('auth/register.html')
            
            # Create user
            users_table.put_item(Item={
                'email': email,
                'password_hash': generate_password_hash(password),
                'name': name,
                'phone': phone,
                'role': 'customer',
                'is_active': True,
                'created_at': datetime.utcnow().isoformat()
            })
            
            send_notification("New User Signup", f"User {name} ({email}) has signed up.")
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except ClientError as e:
            print(f"Registration error: {e}")
            flash('An error occurred. Please try again.', 'danger')
    
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
        
        try:
            # Check if user exists
            response = users_table.get_item(Key={'email': email})
            if 'Item' in response:
                flash('Email already registered.', 'danger')
                return render_template('auth/register_baker.html')
            
            # Create user
            users_table.put_item(Item={
                'email': email,
                'password_hash': generate_password_hash(password),
                'name': name,
                'phone': phone,
                'role': 'baker',
                'is_active': True,
                'created_at': datetime.utcnow().isoformat()
            })
            
            # Create bakery
            bakery_id = str(uuid.uuid4())
            bakeries_table.put_item(Item={
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
                'rating': 0,
                'created_at': datetime.utcnow().isoformat()
            })
            
            send_notification("New Baker Registration", 
                            f"Baker {name} ({email}) registered bakery: {bakery_name}")
            flash('Registration submitted! Your bakery is pending admin approval.', 'info')
            return redirect(url_for('login'))
        except ClientError as e:
            print(f"Baker registration error: {e}")
            flash('An error occurred. Please try again.', 'danger')
    
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
    
    try:
        response = cart_items_table.query(
            KeyConditionExpression=Key('user_email').eq(user_email)
        )
        cart_data = []
        total = 0
        
        for item in response.get('Items', []):
            prod_response = products_table.get_item(Key={'product_id': item['product_id']})
            product = prod_response.get('Item')
            if product:
                quantity = int(item.get('quantity', 0))
                price = float(product.get('price', 0))
                subtotal = price * quantity
                cart_data.append({
                    'product': product,
                    'quantity': quantity,
                    'subtotal': subtotal
                })
                total += subtotal
    except ClientError as e:
        print(f"Cart error: {e}")
        cart_data = []
        total = 0
    
    return render_template('customer/cart.html',
                          cart_items=cart_data,
                          cart_total=total)

@app.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    """Add product to cart."""
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    
    try:
        prod_response = products_table.get_item(Key={'product_id': product_id})
        product = prod_response.get('Item')
        if not product:
            flash('Product not found.', 'danger')
            return redirect(request.referrer or url_for('index'))
        
        user_email = session['user_email']
        
        # Check existing cart item
        cart_response = cart_items_table.get_item(
            Key={'user_email': user_email, 'product_id': product_id}
        )
        
        if 'Item' in cart_response:
            # Update quantity
            new_quantity = int(cart_response['Item'].get('quantity', 0)) + quantity
            cart_items_table.update_item(
                Key={'user_email': user_email, 'product_id': product_id},
                UpdateExpression='SET quantity = :q',
                ExpressionAttributeValues={':q': new_quantity}
            )
        else:
            # Add new item
            cart_items_table.put_item(Item={
                'user_email': user_email,
                'product_id': product_id,
                'quantity': quantity,
                'created_at': datetime.utcnow().isoformat()
            })
        
        flash(f"{product['name']} added to cart!", 'success')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
            
    except ClientError as e:
        print(f"Add to cart error: {e}")
        flash('Error adding to cart.', 'danger')
    
    return redirect(request.referrer or url_for('view_cart'))

@app.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    """Update cart item quantity."""
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 0))
    user_email = session['user_email']
    
    try:
        if quantity <= 0:
            cart_items_table.delete_item(
                Key={'user_email': user_email, 'product_id': product_id}
            )
            flash('Item removed from cart.', 'success')
        else:
            cart_items_table.update_item(
                Key={'user_email': user_email, 'product_id': product_id},
                UpdateExpression='SET quantity = :q',
                ExpressionAttributeValues={':q': quantity}
            )
            flash('Cart updated.', 'success')
    except ClientError as e:
        print(f"Update cart error: {e}")
    
    return redirect(url_for('view_cart'))

@app.route('/cart/remove/<product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    """Remove item from cart."""
    user_email = session['user_email']
    
    try:
        cart_items_table.delete_item(
            Key={'user_email': user_email, 'product_id': product_id}
        )
        flash('Item removed from cart.', 'success')
    except ClientError as e:
        print(f"Remove from cart error: {e}")
    
    return redirect(url_for('view_cart'))

@app.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    """Clear all items from cart."""
    user_email = session['user_email']
    
    try:
        response = cart_items_table.query(
            KeyConditionExpression=Key('user_email').eq(user_email)
        )
        for item in response.get('Items', []):
            cart_items_table.delete_item(
                Key={'user_email': user_email, 'product_id': item['product_id']}
            )
        flash('Cart cleared.', 'success')
    except ClientError as e:
        print(f"Clear cart error: {e}")
    
    return redirect(url_for('view_cart'))

# ==================== ORDER ROUTES ====================

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Checkout page."""
    user_email = session['user_email']
    
    try:
        cart_response = cart_items_table.query(
            KeyConditionExpression=Key('user_email').eq(user_email)
        )
        cart_items_list = cart_response.get('Items', [])
        
        if not cart_items_list:
            flash('Your cart is empty.', 'warning')
            return redirect(url_for('view_cart'))
        
        if request.method == 'POST':
            # Create order
            order_number = f"LC{datetime.utcnow().strftime('%Y%m%d%H%M')}{str(uuid.uuid4().hex)[:6].upper()}"
            
            items = []
            total = 0
            bakery_id = None
            for cart_item in cart_items_list:
                prod_response = products_table.get_item(Key={'product_id': cart_item['product_id']})
                product = prod_response.get('Item')
                if product:
                    quantity = int(cart_item['quantity'])
                    price = float(product['price'])
                    subtotal = price * quantity
                    items.append({
                        'product_id': cart_item['product_id'],
                        'product_name': product['name'],
                        'quantity': quantity,
                        'unit_price': str(price),
                        'subtotal': str(subtotal)
                    })
                    total += subtotal
                    bakery_id = product.get('bakery_id')
            
            # Save order
            orders_table.put_item(Item={
                'order_number': order_number,
                'customer_email': user_email,
                'bakery_id': bakery_id,
                'items': items,
                'total_amount': str(total),
                'status': 'pending',
                'payment_method': request.form.get('payment_method', 'cod'),
                'delivery_address': request.form.get('address', ''),
                'created_at': datetime.utcnow().isoformat()
            })
            
            # Clear cart
            for cart_item in cart_items_list:
                cart_items_table.delete_item(
                    Key={'user_email': user_email, 'product_id': cart_item['product_id']}
                )
            
            send_notification("New Order Placed", 
                            f"Order {order_number} placed by {user_email}. Total: ${total:.2f}")
            
            flash('Order placed successfully!', 'success')
            return redirect(url_for('order_confirmation', order_number=order_number))
        
        # Get user addresses
        addr_response = addresses_table.scan(
            FilterExpression=Attr('user_email').eq(user_email)
        )
        user_addresses = addr_response.get('Items', [])
        
        cart_data = []
        total = 0
        for cart_item in cart_items_list:
            prod_response = products_table.get_item(Key={'product_id': cart_item['product_id']})
            product = prod_response.get('Item')
            if product:
                quantity = int(cart_item['quantity'])
                price = float(product['price'])
                subtotal = price * quantity
                cart_data.append({
                    'product': product,
                    'quantity': quantity,
                    'subtotal': subtotal
                })
                total += subtotal
        
    except ClientError as e:
        print(f"Checkout error: {e}")
        flash('An error occurred.', 'danger')
        return redirect(url_for('view_cart'))
    
    return render_template('customer/checkout.html',
                          cart_items=cart_data,
                          cart_total=total,
                          addresses=user_addresses)

@app.route('/order/<order_number>')
@login_required
def order_confirmation(order_number):
    """Order confirmation page."""
    try:
        response = orders_table.get_item(Key={'order_number': order_number})
        order = response.get('Item')
        if not order or order['customer_email'] != session['user_email']:
            return "Order not found", 404
    except ClientError:
        return "Error loading order", 500
    
    return render_template('customer/order_confirmation.html', order=order)

@app.route('/orders')
@login_required
def order_history():
    """Order history."""
    user_email = session['user_email']
    
    try:
        response = orders_table.scan(
            FilterExpression=Attr('customer_email').eq(user_email)
        )
        user_orders = sorted(response.get('Items', []), 
                           key=lambda x: x.get('created_at', ''), 
                           reverse=True)
    except ClientError:
        user_orders = []
    
    return render_template('customer/orders.html', orders=user_orders)

@app.route('/orders/<order_number>')
@login_required
def order_detail(order_number):
    """Order detail page."""
    try:
        response = orders_table.get_item(Key={'order_number': order_number})
        order = response.get('Item')
        if not order or order['customer_email'] != session['user_email']:
            return "Order not found", 404
        
        bakery = None
        if order.get('bakery_id'):
            bakery_response = bakeries_table.get_item(Key={'bakery_id': order['bakery_id']})
            bakery = bakery_response.get('Item')
    except ClientError:
        return "Error loading order", 500
    
    return render_template('customer/order_detail.html', order=order, bakery=bakery)

# ==================== BAKER ROUTES ====================

@app.route('/baker/dashboard')
@login_required
@baker_required
def baker_dashboard():
    """Baker dashboard."""
    user_email = session['user_email']
    
    try:
        # Get bakery
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            flash('No bakery found for your account.', 'danger')
            return redirect(url_for('index'))
        bakery = bakeries_list[0]
        
        # Get orders
        orders_response = orders_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id'])
        )
        bakery_orders = orders_response.get('Items', [])
        
        # Get products
        products_response = products_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id'])
        )
        bakery_products = products_response.get('Items', [])
        
        # Calculate dashboard stats
        today = datetime.utcnow().strftime('%Y-%m-%d')
        today_orders_list = [o for o in bakery_orders if o.get('created_at', '').startswith(today)]
        today_orders = len(today_orders_list)
        today_revenue = sum(float(o.get('total_amount', 0)) for o in today_orders_list)
        total_products = len(bakery_products)
        total_orders = len(bakery_orders)
        
        # Get pending orders
        pending_orders = [o for o in bakery_orders if o.get('status') == 'pending']
        
        # Get recent orders (sorted by created_at, limit to 10)
        recent_orders = sorted(bakery_orders, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
        
    except ClientError as e:
        print(f"Baker dashboard error: {e}")
        return "Error loading dashboard", 500
    
    return render_template('baker/dashboard.html',
                          bakery=bakery,
                          orders=bakery_orders,
                          products=bakery_products,
                          today_orders=today_orders,
                          today_revenue=today_revenue,
                          total_products=total_products,
                          total_orders=total_orders,
                          pending_orders=pending_orders,
                          recent_orders=recent_orders)

@app.route('/baker/products')
@login_required
@baker_required
def baker_products():
    """Baker products list."""
    user_email = session['user_email']
    
    try:
        # Get bakery
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            return redirect(url_for('baker_dashboard'))
        bakery = bakeries_list[0]
        
        # Get products
        products_response = products_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id'])
        )
        bakery_products = products_response.get('Items', [])
        
        # Get categories
        cat_response = categories_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id'])
        )
        bakery_categories = cat_response.get('Items', [])
        
    except ClientError:
        bakery_products = []
        bakery_categories = []
        bakery = {}
    
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
    
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            return redirect(url_for('baker_dashboard'))
        bakery = bakeries_list[0]
        
        if request.method == 'POST':
            product_id = str(uuid.uuid4())
            
            # Handle image upload
            image_filename = 'default-product.png'
            if 'image' in request.files:
                image = request.files['image']
                if image.filename:
                    image_filename = secure_filename(f"{product_id}_{image.filename}")
                    image.save(os.path.join(UPLOAD_FOLDER, 'products', image_filename))
            
            products_table.put_item(Item={
                'product_id': product_id,
                'bakery_id': bakery['bakery_id'],
                'category_id': request.form.get('category_id', ''),
                'name': request.form.get('name'),
                'description': request.form.get('description', ''),
                'price': str(float(request.form.get('price', 0))),
                'discount_price': request.form.get('discount_price', ''),
                'image_url': image_filename,
                'stock_quantity': int(request.form.get('stock_quantity', 0)),
                'is_available': True,
                'is_vegetarian': request.form.get('is_vegetarian') == 'on',
                'is_bestseller': False,
                'created_at': datetime.utcnow().isoformat()
            })
            
            send_notification("New Product Added", 
                            f"Product '{request.form.get('name')}' added to {bakery['name']}")
            
            flash('Product added successfully!', 'success')
            return redirect(url_for('baker_products'))
        
        # Get categories
        cat_response = categories_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id'])
        )
        bakery_categories = cat_response.get('Items', [])
        
    except ClientError as e:
        print(f"Add product error: {e}")
        bakery = {}
        bakery_categories = []
    
    return render_template('baker/product_form.html',
                          bakery=bakery,
                          categories=bakery_categories)

@app.route('/baker/products/<product_id>/edit', methods=['GET', 'POST'])
@login_required
@baker_required
def baker_edit_product(product_id):
    """Edit a product."""
    user_email = session['user_email']
    
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            return redirect(url_for('baker_products'))
        bakery = bakeries_list[0]
        
        # Get the product
        prod_response = products_table.get_item(Key={'product_id': product_id})
        product = prod_response.get('Item')
        
        if not product or product.get('bakery_id') != bakery['bakery_id']:
            flash('Product not found.', 'danger')
            return redirect(url_for('baker_products'))
        
        if request.method == 'POST':
            # Handle image upload
            image_filename = product.get('image_url', '')
            if 'image' in request.files:
                image = request.files['image']
                if image and image.filename:
                    image_filename = f"{product_id}_{image.filename}"
                    os.makedirs(os.path.join(UPLOAD_FOLDER, 'products'), exist_ok=True)
                    image.save(os.path.join(UPLOAD_FOLDER, 'products', image_filename))
            
            # Update product
            update_expr = 'SET #n = :n, description = :desc, price = :p, discount_price = :dp, category_id = :cat, stock_quantity = :sq, is_available = :av, is_vegetarian = :veg, is_bestseller = :bs, image_url = :img'
            expr_names = {'#n': 'name'}
            expr_values = {
                ':n': request.form.get('name'),
                ':desc': request.form.get('description', ''),
                ':p': str(float(request.form.get('price', 0))),
                ':dp': request.form.get('discount_price', ''),
                ':cat': request.form.get('category_id', ''),
                ':sq': int(request.form.get('stock_quantity', 0)),
                ':av': request.form.get('is_available') == 'on',
                ':veg': request.form.get('is_vegetarian') == 'on',
                ':bs': request.form.get('is_bestseller') == 'on',
                ':img': image_filename
            }
            
            products_table.update_item(
                Key={'product_id': product_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values
            )
            
            flash('Product updated successfully!', 'success')
            return redirect(url_for('baker_products'))
        
        # GET request - show form
        cat_response = categories_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id'])
        )
        bakery_categories = cat_response.get('Items', [])
        
    except ClientError as e:
        print(f"Edit product error: {e}")
        flash('Error editing product.', 'danger')
        return redirect(url_for('baker_products'))
    
    return render_template('baker/product_form.html',
                          bakery=bakery,
                          product=product,
                          categories=bakery_categories)

@app.route('/baker/orders')
@login_required
@baker_required
def baker_orders():
    """Baker orders list."""
    user_email = session['user_email']
    
    try:
        # Get bakery
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            return redirect(url_for('baker_dashboard'))
        bakery = bakeries_list[0]
        
        # Get orders
        orders_response = orders_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id'])
        )
        bakery_orders = sorted(orders_response.get('Items', []),
                              key=lambda x: x.get('created_at', ''),
                              reverse=True)
    except ClientError:
        bakery = {}
        bakery_orders = []
    
    return render_template('baker/orders.html',
                          bakery=bakery,
                          orders=bakery_orders)

@app.route('/baker/orders/<order_number>/update', methods=['POST'])
@login_required
@baker_required
def baker_update_order(order_number):
    """Update order status."""
    new_status = request.form.get('status')
    
    try:
        orders_table.update_item(
            Key={'order_number': order_number},
            UpdateExpression='SET #s = :s',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': new_status}
        )
        
        send_notification("Order Status Update", 
                         f"Order {order_number} status changed to: {new_status}")
        
        flash('Order status updated.', 'success')
    except ClientError as e:
        print(f"Update order error: {e}")
    
    return redirect(url_for('baker_orders'))

@app.route('/baker/toggle-status', methods=['POST'])
@login_required
@baker_required
def baker_toggle_status():
    """Toggle bakery open/closed status."""
    user_email = session['user_email']
    
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if bakeries_list:
            bakery = bakeries_list[0]
            new_status = not bakery.get('is_open', True)
            
            bakeries_table.update_item(
                Key={'bakery_id': bakery['bakery_id']},
                UpdateExpression='SET is_open = :s',
                ExpressionAttributeValues={':s': new_status}
            )
            
            status_text = 'open' if new_status else 'closed'
            flash(f"Your bakery is now {status_text}.", 'success')
    except ClientError as e:
        print(f"Toggle status error: {e}")
        flash('Error updating status.', 'danger')
    
    return redirect(url_for('baker_dashboard'))

@app.route('/baker/products/<product_id>/delete', methods=['POST'])
@login_required
@baker_required
def baker_delete_product(product_id):
    """Delete a product."""
    user_email = session['user_email']
    
    try:
        # Verify product belongs to baker's bakery
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            flash('Bakery not found.', 'danger')
            return redirect(url_for('baker_products'))
        
        bakery = bakeries_list[0]
        
        # Check product belongs to this bakery
        prod_response = products_table.get_item(Key={'product_id': product_id})
        product = prod_response.get('Item')
        
        if product and product.get('bakery_id') == bakery['bakery_id']:
            products_table.delete_item(Key={'product_id': product_id})
            flash('Product deleted successfully.', 'success')
        else:
            flash('Product not found.', 'danger')
    except ClientError as e:
        print(f"Delete product error: {e}")
        flash('Error deleting product.', 'danger')
    
    return redirect(url_for('baker_products'))

@app.route('/baker/categories')
@login_required
@baker_required
def baker_categories():
    """Baker categories management."""
    user_email = session['user_email']
    
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            return redirect(url_for('baker_dashboard'))
        bakery = bakeries_list[0]
        
        cat_response = categories_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id'])
        )
        bakery_categories = cat_response.get('Items', [])
    except ClientError:
        bakery = {}
        bakery_categories = []
    
    return render_template('baker/categories.html',
                          bakery=bakery,
                          categories=bakery_categories)

@app.route('/baker/categories/add', methods=['POST'])
@login_required
@baker_required
def baker_add_category():
    """Add a new category."""
    user_email = session['user_email']
    
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            flash('Bakery not found.', 'danger')
            return redirect(url_for('baker_categories'))
        bakery = bakeries_list[0]
        
        category_id = str(uuid.uuid4())
        categories_table.put_item(Item={
            'category_id': category_id,
            'bakery_id': bakery['bakery_id'],
            'name': request.form.get('name', 'New Category'),
            'display_order': 0,
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        })
        
        flash('Category added successfully!', 'success')
    except ClientError as e:
        print(f"Add category error: {e}")
        flash('Error adding category.', 'danger')
    
    return redirect(url_for('baker_categories'))

@app.route('/baker/category/<category_id>/edit', methods=['POST'])
@login_required
@baker_required
def baker_edit_category(category_id):
    """Edit a category."""
    user_email = session['user_email']
    
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            flash('Bakery not found.', 'danger')
            return redirect(url_for('baker_categories'))
        bakery = bakeries_list[0]
        
        # Verify category belongs to this bakery
        cat_response = categories_table.get_item(Key={'category_id': category_id})
        category = cat_response.get('Item')
        
        if category and category.get('bakery_id') == bakery['bakery_id']:
            new_name = request.form.get('name', category.get('name'))
            is_active = request.form.get('is_active') == 'on'
            
            categories_table.update_item(
                Key={'category_id': category_id},
                UpdateExpression='SET #n = :n, is_active = :a',
                ExpressionAttributeNames={'#n': 'name'},
                ExpressionAttributeValues={':n': new_name, ':a': is_active}
            )
            flash('Category updated.', 'success')
        else:
            flash('Category not found.', 'danger')
    except ClientError as e:
        print(f"Edit category error: {e}")
        flash('Error updating category.', 'danger')
    
    return redirect(url_for('baker_categories'))

@app.route('/baker/categories/<category_id>/delete', methods=['POST'])
@login_required
@baker_required
def baker_delete_category(category_id):
    """Delete a category."""
    user_email = session['user_email']
    
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            flash('Bakery not found.', 'danger')
            return redirect(url_for('baker_categories'))
        bakery = bakeries_list[0]
        
        # Verify category belongs to this bakery
        cat_response = categories_table.get_item(Key={'category_id': category_id})
        category = cat_response.get('Item')
        
        if category and category.get('bakery_id') == bakery['bakery_id']:
            categories_table.delete_item(Key={'category_id': category_id})
            flash('Category deleted.', 'success')
        else:
            flash('Category not found.', 'danger')
    except ClientError as e:
        print(f"Delete category error: {e}")
        flash('Error deleting category.', 'danger')
    
    return redirect(url_for('baker_categories'))

@app.route('/baker/reviews')
@login_required
@baker_required
def baker_reviews():
    """Baker reviews management."""
    user_email = session['user_email']
    
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            return redirect(url_for('baker_dashboard'))
        bakery = bakeries_list[0]
        
        rev_response = reviews_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id'])
        )
        bakery_reviews = rev_response.get('Items', [])
    except ClientError:
        bakery = {}
        bakery_reviews = []
    
    return render_template('baker/reviews.html',
                          bakery=bakery,
                          reviews=bakery_reviews)

@app.route('/baker/analytics')
@login_required
@baker_required
def baker_analytics():
    """Baker analytics page."""
    user_email = session['user_email']
    
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            return redirect(url_for('baker_dashboard'))
        bakery = bakeries_list[0]
        
        # Ensure bakery has required fields
        if 'rating' not in bakery:
            bakery['rating'] = 0.0
        if 'total_reviews' not in bakery:
            bakery['total_reviews'] = 0
        
        # Get orders for analytics
        orders_response = orders_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id'])
        )
        bakery_orders = orders_response.get('Items', [])
        
        # Get products count
        products_response = products_table.scan(
            FilterExpression=Attr('bakery_id').eq(bakery['bakery_id'])
        )
        bakery_products = products_response.get('Items', [])
        total_products = len(bakery_products)
        
        # Calculate analytics
        total_revenue = sum(float(o.get('total_amount', 0)) for o in bakery_orders)
        total_orders = len(bakery_orders)
        
        # This month stats
        this_month = datetime.utcnow().strftime('%Y-%m')
        this_month_orders_list = [o for o in bakery_orders if o.get('created_at', '').startswith(this_month)]
        this_month_orders = len(this_month_orders_list)
        this_month_revenue = sum(float(o.get('total_amount', 0)) for o in this_month_orders_list)
        
        # Average order value
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Top products - simplified (just return empty for now)
        top_products = []
        
    except ClientError:
        bakery = {'rating': 0.0, 'total_reviews': 0}
        bakery_orders = []
        total_revenue = 0
        total_orders = 0
        this_month_orders = 0
        this_month_revenue = 0
        avg_order_value = 0
        top_products = []
        total_products = 0
    
    return render_template('baker/analytics.html',
                          bakery=bakery,
                          orders=bakery_orders,
                          total_revenue=total_revenue,
                          total_orders=total_orders,
                          this_month_orders=this_month_orders,
                          this_month_revenue=this_month_revenue,
                          avg_order_value=avg_order_value,
                          top_products=top_products,
                          total_products=total_products)

@app.route('/baker/coupons')
@login_required
@baker_required
def baker_coupons():
    """Baker coupons management."""
    user_email = session['user_email']
    
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            return redirect(url_for('baker_dashboard'))
        bakery = bakeries_list[0]
    except ClientError:
        bakery = {}
    
    # Coupons table not implemented yet - return empty list
    return render_template('baker/coupons.html',
                          bakery=bakery,
                          coupons=[])

@app.route('/baker/coupons/add', methods=['POST'])
@login_required
@baker_required
def baker_add_coupon():
    """Add a new coupon."""
    user_email = session['user_email']
    
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            flash('Bakery not found.', 'danger')
            return redirect(url_for('baker_coupons'))
        bakery = bakeries_list[0]
        
        coupon_id = str(uuid.uuid4())
        valid_until = request.form.get('valid_until')
        usage_limit = request.form.get('usage_limit')
        
        coupon_data = {
            'coupon_id': coupon_id,
            'bakery_id': bakery['bakery_id'],
            'code': request.form.get('code', '').upper(),
            'discount_type': request.form.get('discount_type', 'percentage'),
            'discount_value': Decimal(str(request.form.get('discount_value', 10))),
            'min_order_amount': Decimal(str(request.form.get('min_order_amount', 0))),
            'usage_limit': int(usage_limit) if usage_limit else None,
            'used_count': 0,
            'valid_until': valid_until if valid_until else None,
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Note: Would need to create coupons_table in DynamoDB
        # For now, just show success message
        flash(f'Coupon {coupon_data["code"]} created successfully!', 'success')
    except ClientError as e:
        print(f"Add coupon error: {e}")
        flash('Error creating coupon.', 'danger')
    
    return redirect(url_for('baker_coupons'))

@app.route('/baker/settings', methods=['GET', 'POST'])
@login_required
@baker_required
def baker_settings():
    """Baker settings/profile page."""
    user_email = session['user_email']
    user = get_current_user()
    
    try:
        response = bakeries_table.scan(
            FilterExpression=Attr('owner_email').eq(user_email)
        )
        bakeries_list = response.get('Items', [])
        if not bakeries_list:
            return redirect(url_for('baker_dashboard'))
        bakery = bakeries_list[0]
        
        if request.method == 'POST':
            # Update bakery settings
            # Convert all numeric values to appropriate types for DynamoDB
            delivery_time = request.form.get('delivery_time_mins', '30')
            min_order = request.form.get('min_order_amount', '0')
            delivery_fee = request.form.get('delivery_fee', '0')
            
            # Ensure proper type conversion
            try:
                delivery_time_int = int(delivery_time) if delivery_time else 30
            except (ValueError, TypeError):
                delivery_time_int = 30
            
            try:
                min_order_decimal = Decimal(str(min_order)) if min_order else Decimal('0')
            except (ValueError, TypeError):
                min_order_decimal = Decimal('0')
            
            try:
                delivery_fee_decimal = Decimal(str(delivery_fee)) if delivery_fee else Decimal('0')
            except (ValueError, TypeError):
                delivery_fee_decimal = Decimal('0')
            
            update_expr = 'SET #n = :n, description = :desc, phone = :phone, email = :email, address = :addr, city = :city, pincode = :pin, delivery_time_mins = :dt, min_order_amount = :mo, delivery_fee = :df'
            expr_names = {'#n': 'name'}
            expr_values = {
                ':n': request.form.get('name', bakery.get('name', '')),
                ':desc': request.form.get('description', ''),
                ':phone': request.form.get('phone', ''),
                ':email': request.form.get('email', ''),
                ':addr': request.form.get('address', ''),
                ':city': request.form.get('city', ''),
                ':pin': request.form.get('pincode', ''),
                ':dt': delivery_time_int,
                ':mo': min_order_decimal,
                ':df': delivery_fee_decimal
            }
            
            bakeries_table.update_item(
                Key={'bakery_id': bakery['bakery_id']},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values
            )
            
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('baker_settings'))
            
    except ClientError as e:
        print(f"Baker settings error: {e}")
        bakery = {}
    
    return render_template('baker/profile.html',
                          bakery=bakery,
                          user=user)

# ==================== ADMIN ROUTES ====================

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard."""
    try:
        users_response = users_table.scan()
        bakeries_response = bakeries_table.scan()
        orders_response = orders_table.scan()
        products_response = products_table.scan()
        
        all_users = users_response.get('Items', [])
        all_bakeries = bakeries_response.get('Items', [])
        all_orders = orders_response.get('Items', [])
        all_products = products_response.get('Items', [])
        
        # Calculate statistics for dashboard
        total_users = len(all_users)
        total_bakeries = len(all_bakeries)
        total_orders = len(all_orders)
        total_products = len(all_products)
        
        # Count pending bakeries (not approved)
        pending_bakeries_list = [b for b in all_bakeries if not b.get('is_approved', False)]
        pending_bakeries = len(pending_bakeries_list)
        pending_approvals = pending_bakeries_list[:5]  # First 5 for display
        
        # Count approved bakeries
        approved_bakeries = len([b for b in all_bakeries if b.get('is_approved', False)])
        
        # Count active users
        active_users = len([u for u in all_users if u.get('is_active', True)])
        
        # Count customers and bakers
        total_customers = len([u for u in all_users if u.get('role') == 'customer'])
        total_bakers = len([u for u in all_users if u.get('role') == 'baker'])
        
        # Calculate total revenue
        total_revenue = sum(float(o.get('total_amount', 0)) for o in all_orders)
        
        # Today's statistics
        today = datetime.utcnow().strftime('%Y-%m-%d')
        today_orders_list = [o for o in all_orders if o.get('created_at', '').startswith(today)]
        today_orders = len(today_orders_list)
        today_revenue = sum(float(o.get('total_amount', 0)) for o in today_orders_list)
        
        # Get recent orders
        recent_orders = sorted(all_orders, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
        
        # Messages count (placeholder - not implemented yet)
        new_messages = 0
        
    except ClientError as e:
        print(f"Admin dashboard error: {e}")
        all_users = []
        all_bakeries = []
        all_orders = []
        all_products = []
        total_users = 0
        total_bakeries = 0
        total_orders = 0
        total_products = 0
        pending_bakeries = 0
        pending_approvals = []
        approved_bakeries = 0
        active_users = 0
        total_customers = 0
        total_bakers = 0
        total_revenue = 0
        today_orders = 0
        today_revenue = 0
        recent_orders = []
        new_messages = 0
    
    return render_template('admin/dashboard.html',
                          users=all_users,
                          bakeries=all_bakeries,
                          orders=all_orders,
                          products=all_products,
                          total_users=total_users,
                          total_bakeries=total_bakeries,
                          total_orders=total_orders,
                          total_products=total_products,
                          pending_bakeries=pending_bakeries,
                          pending_approvals=pending_approvals,
                          approved_bakeries=approved_bakeries,
                          active_users=active_users,
                          total_customers=total_customers,
                          total_bakers=total_bakers,
                          total_revenue=total_revenue,
                          today_orders=today_orders,
                          today_revenue=today_revenue,
                          recent_orders=recent_orders,
                          new_messages=new_messages)

@app.route('/admin/bakeries')
@login_required
@admin_required
def admin_bakeries():
    """Admin bakeries management."""
    try:
        response = bakeries_table.scan()
        all_bakeries = response.get('Items', [])
    except ClientError:
        all_bakeries = []
    
    return render_template('admin/bakeries.html', bakeries=all_bakeries)

@app.route('/admin/bakeries/<bakery_id>/approve', methods=['POST'])
@login_required
@admin_required
def admin_approve_bakery(bakery_id):
    """Approve bakery."""
    try:
        bakeries_table.update_item(
            Key={'bakery_id': bakery_id},
            UpdateExpression='SET is_approved = :a',
            ExpressionAttributeValues={':a': True}
        )
        
        # Get bakery details for notification
        response = bakeries_table.get_item(Key={'bakery_id': bakery_id})
        bakery = response.get('Item', {})
        
        send_notification("Bakery Approved", 
                         f"Bakery '{bakery.get('name', 'Unknown')}' has been approved!")
        
        flash('Bakery approved.', 'success')
    except ClientError as e:
        print(f"Approve bakery error: {e}")
    
    return redirect(url_for('admin_bakeries'))

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Admin users management."""
    try:
        response = users_table.scan()
        all_users = response.get('Items', [])
    except ClientError:
        all_users = []
    
    return render_template('admin/users.html', users=all_users)

@app.route('/admin/users/<user_email>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_user(user_email):
    """Toggle user active status."""
    try:
        response = users_table.get_item(Key={'email': user_email})
        user = response.get('Item')
        
        if user:
            new_status = not user.get('is_active', True)
            users_table.update_item(
                Key={'email': user_email},
                UpdateExpression='SET is_active = :a',
                ExpressionAttributeValues={':a': new_status}
            )
            
            status_text = 'activated' if new_status else 'deactivated'
            flash(f"User {user.get('name', user_email)} has been {status_text}.", 'success')
    except ClientError as e:
        print(f"Toggle user error: {e}")
        flash('Error updating user status.', 'danger')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    """Admin orders management."""
    try:
        response = orders_table.scan()
        all_orders = response.get('Items', [])
    except ClientError:
        all_orders = []
    
    return render_template('admin/orders.html', orders=all_orders)

# ==================== CUSTOMER PROFILE ROUTES ====================

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page."""
    user_email = session['user_email']
    user = get_current_user()
    
    if request.method == 'POST':
        try:
            users_table.update_item(
                Key={'email': user_email},
                UpdateExpression='SET #n = :n, phone = :p',
                ExpressionAttributeNames={'#n': 'name'},
                ExpressionAttributeValues={
                    ':n': request.form.get('name', user.get('name', '')),
                    ':p': request.form.get('phone', user.get('phone', ''))
                }
            )
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
        except ClientError as e:
            print(f"Edit profile error: {e}")
            flash('Error updating profile.', 'danger')
    
    try:
        response = addresses_table.scan(
            FilterExpression=Attr('user_email').eq(user_email)
        )
        user_addresses = response.get('Items', [])
    except ClientError:
        user_addresses = []
    
    return render_template('customer/profile.html',
                          user=user,
                          addresses=user_addresses)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile."""
    user_email = session['user_email']
    user = get_current_user()
    
    if request.method == 'POST':
        try:
            users_table.update_item(
                Key={'email': user_email},
                UpdateExpression='SET #n = :n, phone = :p',
                ExpressionAttributeNames={'#n': 'name'},
                ExpressionAttributeValues={
                    ':n': request.form.get('name', user.get('name', '')),
                    ':p': request.form.get('phone', user.get('phone', ''))
                }
            )
            flash('Profile updated.', 'success')
            return redirect(url_for('profile'))
        except ClientError as e:
            print(f"Edit profile error: {e}")
    
    return render_template('customer/edit_profile.html', user=user)

@app.route('/addresses/add', methods=['GET', 'POST'])
@login_required
def add_address():
    """Add new address."""
    if request.method == 'POST':
        try:
            address_id = str(uuid.uuid4())
            addresses_table.put_item(Item={
                'address_id': address_id,
                'user_email': session['user_email'],
                'label': request.form.get('label', 'Home'),
                'full_address': request.form.get('full_address'),
                'city': request.form.get('city'),
                'pincode': request.form.get('pincode'),
                'is_default': False,
                'created_at': datetime.utcnow().isoformat()
            })
            flash('Address added.', 'success')
            return redirect(url_for('profile'))
        except ClientError as e:
            print(f"Add address error: {e}")
    
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
    print("=" * 60)
    print("FreshBakes - AWS Deployment Version")
    print("=" * 60)
    print(f"Region: {REGION}")
    print(f"SNS Topic: {SNS_TOPIC_ARN}")
    print("")
    print("Required DynamoDB Tables:")
    print("  - FreshBakes_Users (PK: email)")
    print("  - FreshBakes_Addresses (PK: address_id)")
    print("  - FreshBakes_Bakeries (PK: bakery_id)")
    print("  - FreshBakes_Categories (PK: category_id)")
    print("  - FreshBakes_Products (PK: product_id)")
    print("  - FreshBakes_CartItems (PK: user_email, SK: product_id)")
    print("  - FreshBakes_Orders (PK: order_number)")
    print("  - FreshBakes_OrderItems (PK: order_number, SK: product_id)")
    print("  - FreshBakes_Reviews (PK: review_id)")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)



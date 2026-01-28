"""Seed script to populate database with sample data."""

from app import create_app, db
from app.models import User, Bakery, Category, Product, Coupon


def seed_database():
    """Seed the database with sample data."""
    app = create_app()
    
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Check if already seeded
        if User.query.filter_by(email='admin@localcrust.com').first():
            print('Database already seeded!')
            return
        
        print('Seeding database...')
        
        # Create Admin
        admin = User(
            email='admin@localcrust.com',
            name='Admin User',
            phone='9999999999',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create Sample Bakers and Bakeries
        bakers_data = [
            {
                'user': {
                    'email': 'artisan@example.com',
                    'name': 'Priya Sharma',
                    'phone': '9876543210',
                    'password': 'baker123'
                },
                'bakery': {
                    'name': 'Artisan Bakes',
                    'description': 'Handcrafted artisan breads and pastries made with love. Our sourdough has been winning hearts for over 10 years.',
                    'address': '45, MG Road, Indiranagar',
                    'city': 'Bangalore',
                    'pincode': '560038',
                    'phone': '9876543210',
                    'delivery_time_mins': 35,
                    'min_order_amount': 200,
                    'delivery_fee': 30,
                    'rating': 4.8,
                    'total_reviews': 245,
                    'is_featured': True
                },
                'categories': ['Breads', 'Pastries', 'Cakes'],
                'products': [
                    {'name': 'Sourdough Loaf', 'price': 180, 'category': 'Breads', 'description': 'Classic tangy sourdough with a crispy crust', 'is_vegetarian': True, 'is_bestseller': True},
                    {'name': 'Multigrain Bread', 'price': 120, 'category': 'Breads', 'description': 'Healthy multigrain bread with seeds', 'is_vegetarian': True},
                    {'name': 'Croissant', 'price': 85, 'category': 'Pastries', 'description': 'Buttery, flaky French croissant', 'is_vegetarian': True, 'is_bestseller': True},
                    {'name': 'Chocolate Eclair', 'price': 95, 'category': 'Pastries', 'description': 'Filled with vanilla cream, topped with chocolate', 'is_vegetarian': True},
                    {'name': 'Red Velvet Cake', 'price': 650, 'category': 'Cakes', 'description': 'Classic red velvet with cream cheese frosting', 'is_vegetarian': True},
                    {'name': 'Black Forest Cake', 'price': 550, 'category': 'Cakes', 'description': 'Chocolate layers with cherry and cream', 'is_vegetarian': True},
                ]
            },
            {
                'user': {
                    'email': 'sweetdelights@example.com',
                    'name': 'Rahul Patel',
                    'phone': '9123456780',
                    'password': 'baker123'
                },
                'bakery': {
                    'name': 'Sweet Delights',
                    'description': 'Specializing in celebration cakes and custom desserts. Every cake tells a story!',
                    'address': '12, Park Street, Koramangala',
                    'city': 'Bangalore',
                    'pincode': '560095',
                    'phone': '9123456780',
                    'delivery_time_mins': 45,
                    'min_order_amount': 300,
                    'delivery_fee': 40,
                    'rating': 4.6,
                    'total_reviews': 189,
                    'is_featured': True
                },
                'categories': ['Cakes', 'Cupcakes', 'Cookies'],
                'products': [
                    {'name': 'Chocolate Truffle Cake', 'price': 750, 'category': 'Cakes', 'description': 'Rich chocolate cake with truffle frosting', 'is_vegetarian': True, 'is_bestseller': True},
                    {'name': 'Butterscotch Cake', 'price': 600, 'category': 'Cakes', 'description': 'Butterscotch sponge with caramel crunch', 'is_vegetarian': True},
                    {'name': 'Rainbow Cupcakes (6pc)', 'price': 320, 'category': 'Cupcakes', 'description': 'Colorful vanilla cupcakes with buttercream', 'is_vegetarian': True},
                    {'name': 'Chocolate Cupcakes (6pc)', 'price': 350, 'category': 'Cupcakes', 'description': 'Rich chocolate cupcakes with ganache', 'is_vegetarian': True, 'is_bestseller': True},
                    {'name': 'Butter Cookies Box', 'price': 280, 'category': 'Cookies', 'description': 'Assorted butter cookies, 250g box', 'is_vegetarian': True},
                    {'name': 'Chocolate Chip Cookies', 'price': 220, 'category': 'Cookies', 'description': 'Classic chocolate chip, 200g pack', 'is_vegetarian': True},
                ]
            },
            {
                'user': {
                    'email': 'homestyle@example.com',
                    'name': 'Meera Reddy',
                    'phone': '9234567890',
                    'password': 'baker123'
                },
                'bakery': {
                    'name': 'Homestyle Bakery',
                    'description': 'Traditional recipes passed down through generations. Taste the love in every bite!',
                    'address': '78, Gandhi Nagar, HSR Layout',
                    'city': 'Bangalore',
                    'pincode': '560102',
                    'phone': '9234567890',
                    'delivery_time_mins': 40,
                    'min_order_amount': 150,
                    'delivery_fee': 25,
                    'rating': 4.5,
                    'total_reviews': 156
                },
                'categories': ['Traditional', 'Snacks', 'Sweets'],
                'products': [
                    {'name': 'Banana Bread', 'price': 160, 'category': 'Traditional', 'description': 'Moist banana bread with walnuts', 'is_vegetarian': True, 'is_bestseller': True},
                    {'name': 'Plum Cake', 'price': 250, 'category': 'Traditional', 'description': 'Rich fruit cake with rum essence', 'is_vegetarian': True},
                    {'name': 'Veg Puff (4pc)', 'price': 80, 'category': 'Snacks', 'description': 'Flaky puff pastry with spiced veggies', 'is_vegetarian': True},
                    {'name': 'Cheese Toast', 'price': 60, 'category': 'Snacks', 'description': 'Crispy toast with melted cheese', 'is_vegetarian': True},
                    {'name': 'Gulab Jamun (6pc)', 'price': 120, 'category': 'Sweets', 'description': 'Soft milk dumplings in sugar syrup', 'is_vegetarian': True},
                    {'name': 'Rasmalai (4pc)', 'price': 180, 'category': 'Sweets', 'description': 'Creamy cottage cheese in saffron milk', 'is_vegetarian': True},
                ]
            },
        ]
        
        for baker_data in bakers_data:
            # Create baker user
            baker = User(
                email=baker_data['user']['email'],
                name=baker_data['user']['name'],
                phone=baker_data['user']['phone'],
                role='baker'
            )
            baker.set_password(baker_data['user']['password'])
            db.session.add(baker)
            db.session.flush()
            
            # Create bakery
            bakery_info = baker_data['bakery']
            bakery = Bakery(
                owner_id=baker.id,
                name=bakery_info['name'],
                description=bakery_info['description'],
                address=bakery_info['address'],
                city=bakery_info['city'],
                pincode=bakery_info['pincode'],
                phone=bakery_info['phone'],
                email=baker_data['user']['email'],
                delivery_time_mins=bakery_info['delivery_time_mins'],
                min_order_amount=bakery_info['min_order_amount'],
                delivery_fee=bakery_info['delivery_fee'],
                rating=bakery_info['rating'],
                total_reviews=bakery_info['total_reviews'],
                is_approved=True,
                is_open=True,
                is_featured=bakery_info.get('is_featured', False),
                logo_url='default-bakery.png'
            )
            bakery.generate_slug()
            db.session.add(bakery)
            db.session.flush()
            
            # Create categories
            category_map = {}
            for i, cat_name in enumerate(baker_data['categories']):
                category = Category(
                    bakery_id=bakery.id,
                    name=cat_name,
                    display_order=i
                )
                db.session.add(category)
                db.session.flush()
                category_map[cat_name] = category.id
            
            # Create products
            for product_data in baker_data['products']:
                product = Product(
                    bakery_id=bakery.id,
                    category_id=category_map.get(product_data['category']),
                    name=product_data['name'],
                    description=product_data['description'],
                    price=product_data['price'],
                    is_vegetarian=product_data.get('is_vegetarian', False),
                    is_bestseller=product_data.get('is_bestseller', False),
                    stock_quantity=50,
                    is_available=True,
                    image_url='default-product.png'
                )
                db.session.add(product)
        
        # Create sample customers
        customers = [
            {'email': 'john@example.com', 'name': 'John Doe', 'phone': '9876543211', 'password': 'user123'},
            {'email': 'jane@example.com', 'name': 'Jane Smith', 'phone': '9876543212', 'password': 'user123'},
        ]
        
        for cust in customers:
            customer = User(
                email=cust['email'],
                name=cust['name'],
                phone=cust['phone'],
                role='customer'
            )
            customer.set_password(cust['password'])
            db.session.add(customer)
        
        # Create platform coupon
        coupon = Coupon(
            code='WELCOME10',
            description='10% off your first order',
            discount_type='percentage',
            discount_value=10,
            max_discount=100,
            min_order_amount=200,
            is_active=True
        )
        db.session.add(coupon)
        
        db.session.commit()
        print('Database seeded successfully!')
        print('\nTest Accounts:')
        print('  Admin: admin@localcrust.com / admin123')
        print('  Baker: artisan@example.com / baker123')
        print('  Customer: john@example.com / user123')
        print('\nCoupon Code: WELCOME10 (10% off, max ₹100)')


if __name__ == '__main__':
    seed_database()

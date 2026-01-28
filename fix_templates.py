"""Fix all template url_for references for AWS deployment."""
import os
import re

# Mapping from blueprint-style to direct route names
REPLACEMENTS = {
    # Main routes
    "url_for('main.index')": "url_for('index')",
    "url_for('main.bakeries')": "url_for('bakeries_list')",
    "url_for('main.bakery_detail'": "url_for('bakery_detail'",
    "url_for('main.product_detail'": "url_for('product_detail'",
    "url_for('main.search')": "url_for('search')",
    "url_for('main.about')": "url_for('about')",
    "url_for('main.contact')": "url_for('contact')",
    "url_for('main.faq')": "url_for('faq')",
    "url_for('main.terms')": "url_for('terms')",
    "url_for('main.privacy')": "url_for('privacy')",
    "url_for('main.become_baker')": "url_for('become_baker')",
    
    # Auth routes
    "url_for('auth.login')": "url_for('login')",
    "url_for('auth.register')": "url_for('register')",
    "url_for('auth.register_baker')": "url_for('register_baker')",
    "url_for('auth.logout')": "url_for('logout')",
    
    # Cart routes
    "url_for('cart.view_cart')": "url_for('view_cart')",
    "url_for('cart.add_to_cart')": "url_for('add_to_cart')",
    "url_for('cart.update_cart')": "url_for('update_cart')",
    "url_for('cart.remove_from_cart'": "url_for('remove_from_cart'",
    "url_for('cart.clear_cart')": "url_for('clear_cart')",
    "url_for('cart.checkout')": "url_for('checkout')",
    
    # Order routes
    "url_for('orders.checkout')": "url_for('checkout')",
    "url_for('orders.order_confirmation'": "url_for('order_confirmation'",
    "url_for('orders.order_history')": "url_for('order_history')",
    "url_for('orders.order_detail'": "url_for('order_detail'",
    "url_for('orders.track_order'": "url_for('order_detail'",
    
    # Customer routes
    "url_for('customer.dashboard')": "url_for('index')",
    "url_for('customer.profile')": "url_for('profile')",
    "url_for('customer.edit_profile')": "url_for('edit_profile')",
    "url_for('customer.my_reviews')": "url_for('order_history')",
    "url_for('customer.notifications')": "url_for('order_history')",
    "url_for('customer.addresses')": "url_for('profile')",
    "url_for('customer.add_address')": "url_for('add_address')",
    
    # Baker routes
    "url_for('baker.dashboard')": "url_for('baker_dashboard')",
    "url_for('baker.products')": "url_for('baker_products')",
    "url_for('baker.add_product')": "url_for('baker_add_product')",
    "url_for('baker.edit_product'": "url_for('baker_products'",
    "url_for('baker.orders')": "url_for('baker_orders')",
    "url_for('baker.order_detail'": "url_for('baker_orders'",
    "url_for('baker.update_order'": "url_for('baker_update_order'",
    "url_for('baker.categories')": "url_for('baker_products')",
    "url_for('baker.add_category')": "url_for('baker_products')",
    "url_for('baker.profile')": "url_for('baker_dashboard')",
    "url_for('baker.analytics')": "url_for('baker_dashboard')",
    "url_for('baker.reviews')": "url_for('baker_dashboard')",
    "url_for('baker.coupons')": "url_for('baker_dashboard')",
    
    # Admin routes
    "url_for('admin.dashboard')": "url_for('admin_dashboard')",
    "url_for('admin.bakeries')": "url_for('admin_bakeries')",
    "url_for('admin.bakery_detail'": "url_for('admin_bakeries'",
    "url_for('admin.approve_bakery'": "url_for('admin_approve_bakery'",
    "url_for('admin.users')": "url_for('admin_users')",
    "url_for('admin.orders')": "url_for('admin_orders')",
    "url_for('admin.reviews')": "url_for('admin_dashboard')",
    "url_for('admin.coupons')": "url_for('admin_dashboard')",
    "url_for('admin.pending_approvals')": "url_for('admin_bakeries')",
    
    # Fix current_user.is_authenticated to check if current_user exists
    "current_user.is_authenticated": "current_user",
    "current_user.is_admin()": "current_user.role == 'admin'",
    "current_user.is_baker()": "current_user.role == 'baker'",
}

def fix_file(filepath):
    """Fix url_for references in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        for old, new in REPLACEMENTS.items():
            content = content.replace(old, new)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    templates_dir = os.path.join(os.path.dirname(__file__), 'app', 'templates')
    fixed_count = 0
    
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                if fix_file(filepath):
                    print(f"Fixed: {filepath}")
                    fixed_count += 1
    
    print(f"\nDone! Fixed {fixed_count} files.")

if __name__ == '__main__':
    main()

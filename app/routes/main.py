"""Main public routes."""

from flask import Blueprint, render_template, request, current_app
from app.models import Bakery, Product, Category
from sqlalchemy import or_

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Homepage with featured bakeries."""
    # Featured bakeries
    featured_bakeries = Bakery.query.filter_by(
        is_approved=True, 
        is_featured=True
    ).limit(6).all()
    
    # All approved bakeries
    bakeries = Bakery.query.filter_by(is_approved=True).order_by(
        Bakery.rating.desc()
    ).limit(8).all()
    
    # Popular products
    popular_products = Product.query.join(Bakery).filter(
        Bakery.is_approved == True,
        Product.is_available == True,
        Product.is_bestseller == True
    ).limit(8).all()
    
    return render_template('main/index.html',
                         featured_bakeries=featured_bakeries,
                         bakeries=bakeries,
                         popular_products=popular_products)


@main_bp.route('/bakeries')
def bakeries():
    """List all bakeries with search and filter."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    city = request.args.get('city', '')
    sort = request.args.get('sort', 'rating')
    
    # Base query
    query = Bakery.query.filter_by(is_approved=True)
    
    # Search
    if search:
        query = query.filter(
            or_(
                Bakery.name.ilike(f'%{search}%'),
                Bakery.description.ilike(f'%{search}%')
            )
        )
    
    # Filter by city
    if city:
        query = query.filter(Bakery.city.ilike(f'%{city}%'))
    
    # Sort
    if sort == 'rating':
        query = query.order_by(Bakery.rating.desc())
    elif sort == 'delivery_time':
        query = query.order_by(Bakery.delivery_time_mins.asc())
    elif sort == 'name':
        query = query.order_by(Bakery.name.asc())
    
    # Pagination
    pagination = query.paginate(
        page=page,
        per_page=current_app.config.get('ITEMS_PER_PAGE', 12),
        error_out=False
    )
    
    # Get unique cities for filter
    cities = Bakery.query.filter_by(is_approved=True).with_entities(
        Bakery.city
    ).distinct().all()
    cities = [c[0] for c in cities]
    
    return render_template('main/bakeries.html',
                         bakeries=pagination.items,
                         pagination=pagination,
                         cities=cities,
                         search=search,
                         current_city=city,
                         current_sort=sort)


@main_bp.route('/bakery/<slug>')
def bakery_detail(slug):
    """Individual bakery page with products."""
    bakery = Bakery.query.filter_by(slug=slug, is_approved=True).first_or_404()
    
    # Get categories with products
    categories = Category.query.filter_by(
        bakery_id=bakery.id,
        is_active=True
    ).order_by(Category.display_order).all()
    
    # Products without category
    uncategorized_products = Product.query.filter_by(
        bakery_id=bakery.id,
        category_id=None,
        is_available=True
    ).all()
    
    # Get reviews
    reviews = bakery.reviews.filter_by(is_visible=True).order_by(
        db.desc('created_at')
    ).limit(10).all() if hasattr(bakery, 'reviews') else []
    
    return render_template('main/bakery_detail.html',
                         bakery=bakery,
                         categories=categories,
                         uncategorized_products=uncategorized_products,
                         reviews=reviews)


@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    """Product detail page."""
    product = Product.query.get_or_404(product_id)
    
    # Ensure bakery is approved
    if not product.bakery.is_approved:
        abort(404)
    
    # Related products from same bakery
    related_products = Product.query.filter(
        Product.bakery_id == product.bakery_id,
        Product.id != product.id,
        Product.is_available == True
    ).limit(4).all()
    
    return render_template('main/product_detail.html',
                         product=product,
                         related_products=related_products)


@main_bp.route('/search')
def search():
    """Search results page."""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    if not query:
        return render_template('main/search_results.html',
                             query='',
                             bakeries=[],
                             products=[])
    
    # Search bakeries
    bakeries = Bakery.query.filter(
        Bakery.is_approved == True,
        or_(
            Bakery.name.ilike(f'%{query}%'),
            Bakery.description.ilike(f'%{query}%'),
            Bakery.city.ilike(f'%{query}%')
        )
    ).limit(6).all()
    
    # Search products
    products = Product.query.join(Bakery).filter(
        Bakery.is_approved == True,
        Product.is_available == True,
        or_(
            Product.name.ilike(f'%{query}%'),
            Product.description.ilike(f'%{query}%')
        )
    ).limit(12).all()
    
    return render_template('main/search_results.html',
                         query=query,
                         bakeries=bakeries,
                         products=products)


@main_bp.route('/about')
def about():
    """About us page."""
    return render_template('main/about.html')


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact us page."""
    from app.models import ContactMessage
    from app.extensions import db
    
    if request.method == 'POST':
        message = ContactMessage(
            name=request.form.get('name'),
            email=request.form.get('email'),
            subject=request.form.get('subject'),
            message=request.form.get('message')
        )
        db.session.add(message)
        db.session.commit()
        
        from flask import flash
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('main.contact'))
    
    return render_template('main/contact.html')


@main_bp.route('/faq')
def faq():
    """FAQ page."""
    return render_template('main/faq.html')


@main_bp.route('/terms')
def terms():
    """Terms of service."""
    return render_template('main/terms.html')


@main_bp.route('/privacy')
def privacy():
    """Privacy policy."""
    return render_template('main/privacy.html')


@main_bp.route('/become-a-baker')
def become_baker():
    """Baker signup landing page."""
    return render_template('main/become_baker.html')


# Import for redirect and abort
from flask import redirect, url_for, abort
from app.extensions import db

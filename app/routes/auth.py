"""Authentication routes."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User, Bakery
from app.forms.auth import LoginForm, CustomerRegistrationForm, BakerRegistrationForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return render_template('auth/login.html', form=form)
            
            login_user(user, remember=form.remember.data)
            flash(f'Welcome back, {user.name}!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            # Redirect based on role
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            elif user.is_baker():
                return redirect(url_for('baker.dashboard'))
            else:
                return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Customer registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = CustomerRegistrationForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data.lower(),
            name=form.name.data,
            phone=form.phone.data,
            role='customer'
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/register/baker', methods=['GET', 'POST'])
def register_baker():
    """Baker registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = BakerRegistrationForm()
    if form.validate_on_submit():
        # Create user
        user = User(
            email=form.email.data.lower(),
            name=form.name.data,
            phone=form.phone.data,
            role='baker'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Create bakery (pending approval)
        bakery = Bakery(
            owner_id=user.id,
            name=form.bakery_name.data,
            description=form.bakery_description.data,
            address=form.bakery_address.data,
            city=form.city.data,
            pincode=form.pincode.data,
            phone=form.bakery_phone.data or form.phone.data,
            email=form.email.data.lower(),
            is_approved=False
        )
        bakery.generate_slug()
        db.session.add(bakery)
        db.session.commit()
        
        flash('Registration submitted! Your bakery is pending admin approval.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register_baker.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password - request reset."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        user = User.query.filter_by(email=email).first()
        
        # Always show success message for security
        flash('If an account exists with that email, you will receive a password reset link.', 'info')
        
        if user:
            # TODO: Generate token and send email
            pass
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # TODO: Validate token and reset password
    return render_template('auth/reset_password.html', token=token)

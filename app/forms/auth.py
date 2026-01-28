"""Authentication forms."""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from app.models import User


class LoginForm(FlaskForm):
    """Login form."""
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required')
    ])
    remember = BooleanField('Remember Me')


class CustomerRegistrationForm(FlaskForm):
    """Customer registration form."""
    name = StringField('Full Name', validators=[
        DataRequired(message='Name is required'),
        Length(min=2, max=100, message='Name must be between 2 and 100 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message='Phone number is required'),
        Length(min=10, max=15, message='Please enter a valid phone number')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    
    def validate_email(self, field):
        """Check if email already exists."""
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('This email is already registered.')


class BakerRegistrationForm(FlaskForm):
    """Baker registration form."""
    # Personal info
    name = StringField('Your Full Name', validators=[
        DataRequired(message='Name is required'),
        Length(min=2, max=100)
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message='Phone number is required'),
        Length(min=10, max=15)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    
    # Bakery info
    bakery_name = StringField('Bakery Name', validators=[
        DataRequired(message='Bakery name is required'),
        Length(min=2, max=150)
    ])
    bakery_description = TextAreaField('Bakery Description', validators=[
        Optional(),
        Length(max=1000)
    ])
    bakery_address = StringField('Bakery Address', validators=[
        DataRequired(message='Address is required'),
        Length(max=500)
    ])
    city = StringField('City', validators=[
        DataRequired(message='City is required'),
        Length(max=100)
    ])
    pincode = StringField('Pincode', validators=[
        DataRequired(message='Pincode is required'),
        Length(min=5, max=10)
    ])
    bakery_phone = StringField('Bakery Phone (optional)', validators=[
        Optional(),
        Length(min=10, max=15)
    ])
    
    def validate_email(self, field):
        """Check if email already exists."""
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('This email is already registered.')

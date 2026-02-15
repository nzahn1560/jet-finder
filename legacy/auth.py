"""
Authentication system for Jet Finder
Cookie-based sessions with secure password hashing
"""
from flask import Blueprint, request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import SessionLocal, User, Session, ListingStatus
import os
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Cookie settings
COOKIE_NAME = 'jet_session'
# Secure cookies in production (Railway uses HTTPS)
# Check multiple env vars for production detection
COOKIE_SECURE = (
    os.environ.get('FLASK_ENV') == 'production' or
    os.environ.get('NODE_ENV') == 'production' or
    os.environ.get('RAILWAY_ENVIRONMENT') == 'production' or
    os.environ.get('RAILWAY_ENVIRONMENT_NAME') == 'production'
)
COOKIE_SAMESITE = 'Lax'
COOKIE_HTTPONLY = True
COOKIE_PATH = '/'
COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days

def set_session_cookie(response, token):
    """Set session cookie on response"""
    response.set_cookie(
        COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        secure=COOKIE_SECURE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH
    )
    return response

def clear_session_cookie(response):
    """Clear session cookie"""
    response.set_cookie(
        COOKIE_NAME,
        value='',
        max_age=0,
        secure=COOKIE_SECURE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH
    )
    return response

def get_current_user():
    """Get current user from cookie session"""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    
    db = SessionLocal()
    try:
        # Find valid session
        session = db.query(Session).filter(
            Session.token == token
        ).first()
        
        if not session or not session.is_valid():
            return None
        
        # Load user
        user = db.query(User).filter(User.id == session.user_id).first()
        return user
    finally:
        db.close()

def require_auth(f):
    """Decorator: require authenticated user"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Attach user to request context
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator: require admin user"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        if not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        # Attach user to request context
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function

# Get limiter instance from app
from flask import current_app

# Get limiter from app (will be set by app_production.py)
from flask import current_app
limiter = None

def set_limiter(limiter_instance):
    """Set limiter instance from app"""
    global limiter
    limiter = limiter_instance

# Auth routes
@auth_bp.route('/signup', methods=['POST'])
def signup():
    """Create new user account"""
    # Apply rate limiting if limiter is available
    if limiter:
        limiter.limit("10 per minute")(lambda: None)()
    
    data = request.get_json()
    
    # Check honeypot (add 'website' hidden field to signup form)
    from security import check_honeypot
    if check_honeypot(data):
        # Bot detected via honeypot
        return jsonify({'error': 'Invalid request'}), 400
    
    # Validate input
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    
    db = SessionLocal()
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create user
        password_hash = generate_password_hash(password)
        new_user = User(
            email=email,
            password_hash=password_hash,
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            company=data.get('company'),
            phone=data.get('phone')
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create session
        session = Session.create_for_user(new_user.id)
        db.add(session)
        db.commit()
        
        # Return response with cookie
        response = make_response(jsonify({
            'message': 'Account created successfully',
            'user': new_user.to_dict()
        }), 201)
        
        set_session_cookie(response, session.token)
        return response
        
    except Exception as e:
        db.rollback()
        print(f"Signup error: {e}")
        return jsonify({'error': 'An error occurred during signup'}), 500
    finally:
        db.close()

@auth_bp.route('/login', methods=['POST'])
def login():
    """Log in existing user"""
    data = request.get_json()
    
    # Check honeypot
    from security import check_honeypot
    if check_honeypot(data):
        # Bot detected via honeypot
        return jsonify({'error': 'Invalid request'}), 400
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    db = SessionLocal()
    try:
        # Find user
        user = db.query(User).filter(User.email == email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Create new session
        session = Session.create_for_user(user.id)
        db.add(session)
        db.commit()
        
        # Return response with cookie
        response = make_response(jsonify({
            'message': 'Login successful',
            'user': user.to_dict()
        }), 200)
        
        set_session_cookie(response, session.token)
        return response
        
    except Exception as e:
        db.rollback()
        print(f"Login error: {e}")
        return jsonify({'error': 'An error occurred during login'}), 500
    finally:
        db.close()

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Log out current user"""
    token = request.cookies.get(COOKIE_NAME)
    
    if token:
        db = SessionLocal()
        try:
            # Delete session
            db.query(Session).filter(Session.token == token).delete()
            db.commit()
        except Exception as e:
            print(f"Logout error: {e}")
        finally:
            db.close()
    
    # Clear cookie
    response = make_response(jsonify({'message': 'Logged out successfully'}), 200)
    clear_session_cookie(response)
    return response

@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_me():
    """Get current user info"""
    user = request.current_user
    return jsonify({
        'user': user.to_dict()
    }), 200

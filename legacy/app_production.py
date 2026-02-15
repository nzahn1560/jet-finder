"""
Jet Finder - Production App for Railway
Single origin: serves frontend + API
"""
from flask import Flask, render_template, send_from_directory, request
from flask_cors import CORS
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Initialize security & rate limiting
from security import init_rate_limiter, add_security_headers, RATE_LIMITS
limiter = init_rate_limiter(app)

# CORS - allow credentials for cookie auth
# On Railway with single origin (frontend + API same domain), CORS may not be needed
# But configure it properly for cross-origin scenarios
app_base_url = os.environ.get('APP_BASE_URL', '')
if app_base_url and app_base_url != '*':
    # Explicit origin(s) - best practice for production
    CORS(app, 
         supports_credentials=True,
         origins=[app_base_url])
else:
    # Development: allow all origins (NOT recommended for production)
    # In production, APP_BASE_URL should be set to your Railway domain
    CORS(app, 
         supports_credentials=True,
         origins='*')  # Only for development

# Initialize database - MUST succeed or app won't start
from models import init_db, engine
try:
    logger.info("🔧 Initializing database...")
    logger.info(f"🔧 DATABASE_URL: {os.environ.get('DATABASE_URL', 'NOT SET')[:50]}..." if os.environ.get('DATABASE_URL') else "🔧 DATABASE_URL: NOT SET")
    init_db()
    logger.info("✅ Database initialized successfully - all tables ready")
except Exception as e:
    logger.error("=" * 60)
    logger.error("❌ CRITICAL: Database initialization FAILED")
    logger.error(f"❌ Error: {e}")
    logger.error(f"❌ Error type: {type(e).__name__}")
    import traceback
    logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
    logger.error("=" * 60)
    # Re-raise to prevent app from starting without database
    # This ensures Railway shows the error and deployment fails
    raise

# Register blueprints
from auth import auth_bp
from listings_api import listings_bp
from billing_api import billing_bp

app.register_blueprint(auth_bp)
app.register_blueprint(listings_bp)
app.register_blueprint(billing_bp)

logger.info("✅ API blueprints registered")

# Security headers for all responses
@app.after_request
def apply_security_headers(response):
    """Add security headers to all responses"""
    return add_security_headers(response)

# Frontend routes
@app.route('/')
@limiter.limit("100 per minute")  # Lenient for public pages
def index():
    """Home page - public listing feed"""
    return render_template('public/index.html')

@app.route('/listing/<int:listing_id>')
def listing_detail(listing_id):
    """Listing detail page"""
    return render_template('public/listing_detail.html', listing_id=listing_id)

@app.route('/signup')
@limiter.limit("20 per minute")  # Moderate limit for signup page
def signup_page():
    """Signup page"""
    return render_template('auth/signup.html')

@app.route('/login')
@limiter.limit("20 per minute")  # Moderate limit for login page
def login_page():
    """Login page"""
    return render_template('auth/login.html')

@app.route('/dashboard')
def dashboard():
    """User dashboard (requires auth)"""
    from auth import get_current_user
    from flask import redirect, url_for
    
    # Check if user is logged in
    user = get_current_user()
    if not user:
        return redirect(url_for('login_page'))
    
    # Pass user to template
    return render_template('dashboard/index.html', user=user)

@app.route('/admin')
def admin_panel():
    """Admin panel (requires admin auth)"""
    return render_template('admin/index.html')

# Static files
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# Robots.txt
@app.route('/robots.txt')
def robots():
    """Serve robots.txt for crawler control"""
    return send_from_directory('.', 'robots.txt', mimetype='text/plain')

# Health check for Railway
@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5015))
    app.run(host='0.0.0.0', port=port, debug=False)

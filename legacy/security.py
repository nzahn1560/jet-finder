"""
Security middleware and bot protection for Jet Finder
Implements rate limiting, bot detection, and security headers
"""
from flask import request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import re
import os

# Known bot user agents (partial matches)
BOT_USER_AGENTS = [
    'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
    'python-requests', 'go-http-client', 'java/', 'scrapy',
    'axios', 'node-fetch', 'httpx', 'aiohttp'
]

# Known hosting providers and proxies (often used by bots)
SUSPICIOUS_ASNS = [
    'amazon', 'digitalocean', 'ovh', 'hetzner', 'linode',
    'vultr', 'scaleway', 'contabo'
]

def init_rate_limiter(app):
    """
    Initialize Flask-Limiter with Redis or in-memory storage
    
    For production with Redis (Railway):
    - Add Redis service in Railway
    - Set REDIS_URL environment variable
    
    For development without Redis:
    - Uses in-memory storage (not suitable for production with multiple workers)
    """
    redis_url = os.environ.get('REDIS_URL')
    
    if redis_url:
        # Production: Use Redis for distributed rate limiting
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            storage_uri=redis_url,
            default_limits=["1000 per hour", "100 per minute"],
            strategy="fixed-window",
            headers_enabled=True,
        )
        app.logger.info("✅ Rate limiter initialized with Redis")
    else:
        # Development: Use in-memory storage
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["1000 per hour", "100 per minute"],
            strategy="fixed-window",
            headers_enabled=True,
        )
        app.logger.warning("⚠️  Rate limiter using in-memory storage (not suitable for production)")
    
    return limiter

def is_bot_user_agent(user_agent):
    """Check if user agent matches known bot patterns"""
    if not user_agent:
        return True  # No user agent = suspicious
    
    user_agent_lower = user_agent.lower()
    
    # Check against known bot patterns
    for bot_pattern in BOT_USER_AGENTS:
        if bot_pattern in user_agent_lower:
            return True
    
    return False

def is_suspicious_ip(ip):
    """
    Check if IP is from a known hosting provider or proxy
    This is a basic check - in production, use a service like IPQualityScore
    """
    # This is a placeholder - would need actual ASN/hosting provider database
    # For now, just a basic check
    return False

def check_cloudflare_headers():
    """
    Check if request came through Cloudflare
    Cloudflare adds specific headers that can help identify legitimate traffic
    """
    cf_ray = request.headers.get('CF-Ray')
    cf_connecting_ip = request.headers.get('CF-Connecting-IP')
    
    return bool(cf_ray and cf_connecting_ip)

def get_client_ip():
    """
    Get real client IP, accounting for proxies and Cloudflare
    """
    # If behind Cloudflare
    cf_connecting_ip = request.headers.get('CF-Connecting-IP')
    if cf_connecting_ip:
        return cf_connecting_ip
    
    # If behind other proxies
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    
    # Direct connection
    return request.remote_addr

def block_bots(allow_search_engines=True):
    """
    Decorator to block obvious bots
    
    Usage:
        @app.route('/api/sensitive')
        @block_bots()
        def sensitive_endpoint():
            return jsonify({'data': 'sensitive'})
    
    Args:
        allow_search_engines: If True, allows Googlebot, Bingbot, etc.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_agent = request.headers.get('User-Agent', '')
            
            # Allow legitimate search engines
            if allow_search_engines:
                if any(engine in user_agent.lower() for engine in ['googlebot', 'bingbot', 'slurp', 'duckduckbot']):
                    return f(*args, **kwargs)
            
            # Block known bots
            if is_bot_user_agent(user_agent):
                return jsonify({
                    'error': 'Access denied',
                    'message': 'Automated access detected'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def add_security_headers(response):
    """
    Add security headers to all responses
    Call this in Flask's after_request handler
    """
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy (adjust as needed)
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
    )
    
    # Permissions policy (formerly Feature-Policy)
    response.headers['Permissions-Policy'] = (
        "geolocation=(), "
        "microphone=(), "
        "camera=(), "
        "payment=()"
    )
    
    return response

def check_honeypot(form_data):
    """
    Check for honeypot field (hidden field that bots fill out)
    
    Usage in forms: Add a hidden field named 'website' or 'url'
    Humans won't fill it, bots often will
    
    Returns:
        True if bot detected (honeypot filled)
        False if likely human (honeypot empty)
    """
    honeypot_fields = ['website', 'url', 'homepage']
    
    for field in honeypot_fields:
        if field in form_data and form_data[field]:
            return True
    
    return False

def analyze_behavior(ip_key):
    """
    Analyze user behavior patterns
    This is a placeholder - would need Redis or database to track behavior
    
    Things to track:
    - Request frequency
    - Time between requests
    - Sequential page access patterns
    - Mouse movements (client-side)
    """
    # TODO: Implement behavior analysis with Redis
    pass

# Rate limit presets for common use cases
RATE_LIMITS = {
    'strict': '10 per minute',       # Login, signup
    'moderate': '30 per minute',     # API endpoints
    'lenient': '100 per minute',     # Public pages
    'very_strict': '3 per minute',   # Password reset, sensitive actions
}

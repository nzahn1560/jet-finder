# API Module for JetFinder
from flask import Blueprint

def create_api_blueprints(app):
    """Register all API blueprints"""
    # These modules don't exist in the current codebase - commenting out to fix linter errors
    # from .service_providers import service_provider_bp
    # from .analytics import analytics_bp
    # from .payments import payments_bp
    # from .auth import auth_bp
    
    # app.register_blueprint(service_provider_bp, url_prefix='/api/service-providers')
    # app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    # app.register_blueprint(payments_bp, url_prefix='/api/payments')
    # app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    # Note: API endpoints are currently defined directly in app.py
    pass 
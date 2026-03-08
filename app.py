from __future__ import annotations

from flask import Flask, render_template, request, jsonify, url_for, redirect, flash, session, current_app
import os
import json
from pathlib import Path
from typing import Any, cast

import pandas as pd
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from marketplace import marketplace, load_listings, recommend_aircraft, get_current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import stripe
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional integrations (see integrations/ folder)
try:
    from integrations import enhanced_data_manager, avinode_client
except ImportError:
    enhanced_data_manager = None
    avinode_client = None

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Global scoring dataset (set per-request to ensure normalization uses the current filtered set)
SCORING_DATASET = None

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_...')  # Replace with your actual test key
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_test_...')  # Replace with your actual test key

# Individual subscription price IDs
CHARTER_SEARCH_PRICE_ID = os.environ.get('STRIPE_CHARTER_SEARCH_PRICE_ID', 'price_charter_50')  # $50/month
EMPTY_LEG_PRICE_ID = os.environ.get('STRIPE_EMPTY_LEG_PRICE_ID', 'price_empty_leg_10')  # $10/month
PARTS_PRICE_ID = os.environ.get('STRIPE_PARTS_PRICE_ID', 'price_parts_10')  # $10/month

# Legacy Pro subscription removed - no longer offered

# Per-use pricing
ADVANCED_ACQUISITION_PRICE = 5.00  # $5 per search
SERVICE_PROVIDER_PRICE = 5.00  # $5 per search

# Add built-in functions to Jinja2 environment
app.jinja_env.globals.update(max=max, min=min, len=len, range=range)
app.jinja_env.globals.update(stripe_publishable_key=STRIPE_PUBLISHABLE_KEY)

# Register blueprints
app.register_blueprint(marketplace)

# Database: PostgreSQL (Railway) or SQLite (local) via db module
import db as db_module

def init_db():
    """Create users, user_listings, user_subscriptions, per_use_purchases tables (Postgres or SQLite)."""
    db_module.init_db()

# Initialize database on startup
init_db()

# User management: delegate to db module
def get_user_by_id(user_id):
    return db_module.get_user_by_id(user_id)

def get_user_by_email(email):
    return db_module.get_user_by_email(email)

def create_user(email, password, first_name, last_name, company=None, phone=None):
    password_hash = generate_password_hash(password)
    return db_module.create_user(email, password_hash, first_name, last_name, company, phone)

def get_user_subscriptions(user_id):
    return db_module.get_user_subscriptions(user_id)

def get_user_subscription(user_id, subscription_type=None):
    return db_module.get_user_subscription(user_id, subscription_type)

def update_user_subscription(user_id, subscription_type, stripe_customer_id=None,
                           stripe_subscription_id=None, subscription_status=None,
                           activated_at=None, expires_at=None):
    db_module.update_user_subscription(user_id, subscription_type,
        stripe_customer_id=stripe_customer_id, stripe_subscription_id=stripe_subscription_id,
        subscription_status=subscription_status, activated_at=activated_at, expires_at=expires_at)

def has_active_subscription(user_id, subscription_type):
    subscription = get_user_subscription(user_id, subscription_type)
    if not subscription:
        return False
    if subscription.get('subscription_status') != 'active':
        return False
    if subscription.get('expires_at'):
        try:
            expires_at = datetime.fromisoformat(str(subscription['expires_at']).replace('Z', '+00:00'))
        except Exception:
            return False
        if expires_at.tzinfo:
            from datetime import timezone
            if expires_at < datetime.now(timezone.utc):
                return False
        else:
            if expires_at < datetime.now():
                return False
    return True

def record_per_use_purchase(user_id, service_type, amount, stripe_payment_intent_id=None):
    return db_module.record_per_use_purchase(user_id, service_type, amount, stripe_payment_intent_id)

def use_per_use_purchase(user_id, service_type):
    return db_module.use_per_use_purchase(user_id, service_type)

# Authentication decorators
def login_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def subscription_required(subscription_type, price_per_month=None):
    """Decorator factory to require specific subscription type"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login', next=request.url))
            
            user = get_user_by_id(session['user_id'])
            if not user:
                flash('User not found. Please log in again.', 'error')
                return redirect(url_for('login'))
            
            # Check if user has active subscription for this type
            if not has_active_subscription(user['id'], subscription_type):
                price_text = f"${price_per_month}/month" if price_per_month else "subscription required"
                flash(f'This feature requires a {subscription_type.replace("_", " ").title()} subscription ({price_text}).', 'info')
                return redirect(url_for('pricing'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def per_use_required(service_type, price_per_use):
    """Decorator factory to require per-use purchase"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login', next=request.url))
            
            user = get_user_by_id(session['user_id'])
            if not user:
                flash('User not found. Please log in again.', 'error')
                return redirect(url_for('login'))
            
            # Check if user has unused purchase for this service
            if not use_per_use_purchase(user['id'], service_type):
                flash(f'This feature requires a ${price_per_use} per-use purchase.', 'info')
                return redirect(url_for('pricing'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Specific decorators for each subscription type
@app.route('/charter-search')
def charter_search():
    """Charter search page - now accessible to all users"""
    return render_template('marketplace/charter_search.html')

@app.route('/empty-legs')
def empty_legs():
    """Empty leg flights page - now accessible to all users"""
    return render_template('marketplace/empty_legs.html')

@app.route('/parts-marketplace')
def parts_marketplace():
    """Parts marketplace page - now accessible to all users"""
    return render_template('marketplace/parts.html')

@app.route('/service-providers')
def service_providers():
    """Service providers directory - now accessible to all users"""
    return render_template('service_providers.html')

# Pro subscription removed - legacy decorator removed

# Specific subscription decorators
def charter_search_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Check if user has charter search subscription
        has_subscription = has_active_subscription(session['user_id'], 'charter_search')
        if not has_subscription:
            flash('Charter Search requires an active subscription. Please subscribe to access this feature.', 'warning')
            return redirect(url_for('pricing'))
        
        return f(*args, **kwargs)
    return decorated_function

def empty_leg_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Check if user has empty leg subscription
        has_subscription = has_active_subscription(session['user_id'], 'empty_leg')
        if not has_subscription:
            flash('Empty Leg access requires an active subscription. Please subscribe to access this feature.', 'warning')
            return redirect(url_for('pricing'))
        
        return f(*args, **kwargs)
    return decorated_function

def parts_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Check if user has parts subscription
        has_subscription = has_active_subscription(session['user_id'], 'parts')
        if not has_subscription:
            flash('Parts access requires an active subscription. Please subscribe to access this feature.', 'warning')
            return redirect(url_for('pricing'))
        
        return f(*args, **kwargs)
    return decorated_function

def service_provider_search_required(f):
    """Require $5 per-use payment for service provider search (uses DB layer for Railway)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required', 'redirect': '/login'}), 401
        if db_module.has_unused_service_provider_credit(session['user_id']):
            return f(*args, **kwargs)
        return jsonify({
            'error': 'Service provider search requires $5 payment',
            'service_type': 'service_provider_search',
            'price': 5.00,
            'redirect': '/pricing'
        }), 402
    return decorated_function

def safe_int_convert_form(value):
    """Safely convert form value to int, handling None and empty strings"""
    if not value or not value.strip():
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

# Service Provider Management (DB layer for Railway Postgres)
def create_service_provider(user_id, provider_data):
    """Create a new service provider listing."""
    return db_module.create_service_provider(user_id, provider_data)


def search_service_providers(service_type=None, location=None, radius=50, keywords=None,
                           verified_only=False, sort_by='rating', limit=20):
    """Search service providers with filters."""
    return db_module.search_service_providers(
        service_type=service_type, location=location, radius=radius, keywords=keywords,
        verified_only=verified_only, sort_by=sort_by, limit=limit,
    )


def get_service_provider_details(provider_id):
    """Get detailed information about a service provider."""
    return db_module.get_service_provider_details(provider_id)


def contact_service_provider(provider_id, customer_data):
    """Record a contact request to a service provider."""
    return db_module.contact_service_provider(provider_id, customer_data)

def get_service_categories():
    """Get available service categories"""
    return [
        'Aircraft Maintenance',
        'Avionics Installation',
        'Interior Refurbishment', 
        'Paint & Exterior',
        'Engine Services',
        'Flight Training',
        'Aircraft Management',
        'Insurance Services',
        'Legal Services',
        'Financing',
        'Aircraft Sales',
        'Parts & Components',
        'Ground Support',
        'Hangar Services',
        'Fuel Services',
        'Catering',
        'Transportation',
        'Consulting'
    ]

def load_aircraft_data() -> list[dict[str, Any]]:
    """Load aircraft from PostgreSQL/SQLite (seeded from CSV on first run). Falls back to file if DB empty."""
    try:
        aircraft = db_module.get_all_aircraft_profiles()
        if aircraft:
            logger.info("Loaded %d aircraft from database", len(aircraft))
            return aircraft
        db_module.seed_aircraft_and_airports()
        aircraft = db_module.get_all_aircraft_profiles()
        if aircraft:
            logger.info("Loaded %d aircraft from DB (seeded from CSV)", len(aircraft))
            return aircraft
    except Exception as e:
        logger.warning("DB aircraft load failed, falling back to file: %s", e, exc_info=True)
    # Fallback: load from file via data_loader (used by seed)
    try:
        from data_loader import load_aircraft_from_csv
        _base = Path(__file__).resolve().parent
        for p in [_base / 'static' / 'data' / 'aircraft_data.csv', _base / 'Aircraft Data - Aircraft Data (1).csv']:
            if p.is_file():
                out = load_aircraft_from_csv(str(p))
                if out:
                    logger.info("Loaded %d aircraft from file (fallback)", len(out))
                    return out
    except Exception as e:
        logger.warning("File aircraft load failed: %s", e)
    logger.warning("No aircraft data available (DB failed and no CSV found)")
    return []


# Load aircraft data at startup (from DB, seeded from CSV on first run)
AIRCRAFT_DATA: list[dict[str, Any]] = load_aircraft_data()

# Unified data function that merges spreadsheet and marketplace data
def get_unified_aircraft_data() -> list[dict[str, Any]]:
    """
    Get aircraft data from CSV spreadsheet only (as requested by user).
    Returns a list of aircraft with consistent data structure for filtering and scoring.
    """
    try:
        # Return only spreadsheet data (316 aircraft) - user requested to exclude marketplace listings
        return list(AIRCRAFT_DATA)
        
        # DISABLED: Marketplace integration (was adding extra 328 listings)
        # from marketplace import load_listings
        # marketplace_listings = load_listings()
        # ... marketplace processing code removed ...
        
    except Exception as e:
        print(f"Error getting aircraft data: {e}")
        return AIRCRAFT_DATA.copy() if AIRCRAFT_DATA else []



@app.route('/')
@app.route('/jet-finder')
def home():
    """Home route - Jet Finder with comprehensive scoring and pagination"""
    # Get query parameters for filtering
    budget = request.args.get('budget', type=int)
    range_requirement = request.args.get('range_requirement', type=int)
    passengers = request.args.get('passengers', type=int)
    sort_by = request.args.get('sort', 'score_desc')  # Default to score-based sorting
    search_query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    # Financial analysis filters
    max_annual_cost = request.args.get('max_annual_cost', type=float)
    max_hourly_cost = request.args.get('max_hourly_cost', type=float)
    
    # Advanced analysis filters
    min_speed = request.args.get('min_speed', type=int)
    min_altitude = request.args.get('min_altitude', type=int)
    max_runway = request.args.get('max_runway', type=int)
    min_cabin_volume = request.args.get('min_cabin_volume', type=int)
    fuel_price = request.args.get('fuel_price', type=float)
    ownership_years = request.args.get('ownership_years', type=int)
    
    # Get user priority selections from dropdowns
    priority_1st = request.args.get('priority_1st', 'best_speed_dollar')
    priority_2nd = request.args.get('priority_2nd', 'best_range_dollar')
    priority_3rd = request.args.get('priority_3rd', 'best_performance_dollar')
    priority_4th = request.args.get('priority_4th', 'best_efficiency_dollar')
    priority_5th = request.args.get('priority_5th', 'best_all_around_dollar')
    
    # Collect all selected priorities (skip empty selections)
    selected_priorities = []
    if priority_1st:
        selected_priorities.append(priority_1st)
    if priority_2nd:
        selected_priorities.append(priority_2nd)
    if priority_3rd:
        selected_priorities.append(priority_3rd)
    if priority_4th:
        selected_priorities.append(priority_4th)
    if priority_5th:
        selected_priorities.append(priority_5th)
    
    # Calculate equal weight for each selected priority
    equal_weight = 1.0 / len(selected_priorities) if selected_priorities else 0
    
    # Build user priorities dictionary from selections with equal weights
    user_priorities = {}
    for priority in selected_priorities:
        if priority in user_priorities:
            # If duplicate selection, add the weights together
            user_priorities[priority] += equal_weight
        else:
            user_priorities[priority] = equal_weight
    
    # Also check for legacy priority parameters for backwards compatibility
    legacy_priorities = {
        'price': float(request.args.get('priority_price', 0)),
        'range': float(request.args.get('priority_range', 0)),
        'speed': float(request.args.get('priority_speed', 0)),
        'passengers': float(request.args.get('priority_passengers', 0)),
        'total_hourly_cost': float(request.args.get('priority_operating_cost', 0)),
        'runway_length': float(request.args.get('priority_runway', 0))
    }
    
    # Merge legacy priorities into user_priorities
    for key, value in legacy_priorities.items():
        if value > 0:
            user_priorities[key] = user_priorities.get(key, 0) + value
    
    # Start with unified data (CSV + marketplace)
    filtered_aircraft = get_unified_aircraft_data()

    
    # Apply search filter (manufacturer/model/name)
    if search_query:
        filtered_aircraft = [
            aircraft for aircraft in filtered_aircraft
            if search_query.lower() in aircraft.get('aircraft_name', '').lower() or
               search_query.lower() in aircraft.get('manufacturer', '').lower() or
               search_query.lower() in aircraft.get('model', '').lower()
        ]
    
    # Apply basic filters
    if budget:
        # Exclude unknown price (0) when budget filter is set
        filtered_aircraft = [
            a for a in filtered_aircraft
            if a.get('price', 0) > 0 and a.get('price', 0) <= budget
        ]
    
    if range_requirement:
        filtered_aircraft = [a for a in filtered_aircraft if a.get('range', 0) >= range_requirement]
    
    if passengers:
        filtered_aircraft = [a for a in filtered_aircraft if a.get('passengers', 0) >= passengers]
    
    # Apply financial analysis filters
    if max_annual_cost:
        filtered_aircraft = [a for a in filtered_aircraft if a.get('adjusted_annual_budget', 0) <= max_annual_cost]
    
    if max_hourly_cost:
        filtered_aircraft = [a for a in filtered_aircraft if a.get('total_hourly_cost', 0) <= max_hourly_cost]
    
    # Apply advanced analysis filters
    min_speed = request.args.get('min_speed', type=int)
    min_altitude = request.args.get('min_altitude', type=int)
    max_runway = request.args.get('max_runway', type=int)
    min_cabin_volume = request.args.get('min_cabin_volume', type=int)
    lowest_year = request.args.get('lowest_year', type=int)
    
    if min_speed:
        filtered_aircraft = [a for a in filtered_aircraft if a.get('speed', 0) >= min_speed]
    
    if min_altitude:
        filtered_aircraft = [a for a in filtered_aircraft if a.get('max_altitude', 0) >= min_altitude]
    
    if max_runway:
        filtered_aircraft = [a for a in filtered_aircraft if a.get('runway_length', 0) <= max_runway]
    
    if min_cabin_volume:
        filtered_aircraft = [a for a in filtered_aircraft if a.get('cabin_volume', 0) >= min_cabin_volume]

    if lowest_year:
        filtered_aircraft = [a for a in filtered_aircraft if a.get('year', 0) >= lowest_year]
    
    # Build user inputs for scoring
    user_inputs = {
        'budget': budget or 0,
        'range_requirement': range_requirement or 0,
        'passengers': passengers or 0,
        'max_annual_cost': max_annual_cost or 0,
        'max_hourly_cost': max_hourly_cost or 0,
        'min_speed': request.args.get('min_speed', type=int) or 0,
        'min_altitude': request.args.get('min_altitude', type=int) or 0,
        'max_runway': request.args.get('max_runway', type=int) or 0,
        'min_cabin_volume': request.args.get('min_cabin_volume', type=int) or 0,
    }

    # Use the filtered set for normalization during this request
    global SCORING_DATASET
    SCORING_DATASET = filtered_aircraft

    # Apply final scoring using strict 50/50 methodology
    for aircraft in filtered_aircraft:
        score_result = calculate_final_recommendation_score(aircraft, user_priorities, user_inputs)
        aircraft['display_score'] = score_result['final_score']
        aircraft['score_breakdown'] = {
            'final_score': score_result['final_score'],
            'spreadsheet_score': score_result['spreadsheet_score'],
            'priority_score': score_result['priority_score'],
            'value_rating': 'Excellent' if score_result['final_score'] <= 20 else \
                            'Very Good' if score_result['final_score'] <= 40 else \
                            'Good' if score_result['final_score'] <= 60 else \
                            'Fair' if score_result['final_score'] <= 80 else 'Poor'
        }

    # Annotate upgrade/value intelligence to help decide on deals
    annotate_deal_intelligence(filtered_aircraft, SCORING_DATASET)
    
    # Reset scoring dataset after scoring
    SCORING_DATASET = None

    # Apply sorting (LOWEST SCORE FIRST)
    if sort_by == 'score_desc':
        filtered_aircraft.sort(key=lambda x: x.get('display_score', 0))  # Ascending: lowest is best
    elif sort_by == 'score_asc':
        filtered_aircraft.sort(key=lambda x: x.get('display_score', 0), reverse=True)
    elif sort_by == 'price_asc':
        filtered_aircraft.sort(key=lambda x: x.get('price', 0))
    elif sort_by == 'price_desc':
        filtered_aircraft.sort(key=lambda x: x.get('price', 0), reverse=True)
    elif sort_by == 'name':
        filtered_aircraft.sort(key=lambda x: x.get('aircraft_name', ''))
    elif sort_by == 'passengers':
        filtered_aircraft.sort(key=lambda x: x.get('passengers', 0), reverse=True)
    elif sort_by == 'range':
        filtered_aircraft.sort(key=lambda x: x.get('range', 0), reverse=True)
    
    # Implement proper pagination with configurable aircraft per page
    total = len(filtered_aircraft)
    per_page = request.args.get('per_page', 12, type=int)
    pages = (total + per_page - 1) // per_page  # Ceiling division
    
    # Calculate start and end indices for current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    aircraft_page = filtered_aircraft[start_idx:end_idx]
    
    # Create pagination object
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': pages,
        'has_prev': page > 1,
        'has_next': page < pages,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if page < pages else None
    }
    
    # Build priority selections for template
    priority_selections = {
        'priority_1st': priority_1st,
        'priority_2nd': priority_2nd,
        'priority_3rd': priority_3rd,
        'priority_4th': priority_4th,
        'priority_5th': priority_5th
    }
    
    return render_template('index.html', 
                         filtered_aircraft=aircraft_page,
                         pagination=pagination,
                         total_aircraft=total,
                         search_query=search_query,
                         user_priorities=user_priorities,
                         priority_selections=priority_selections,
                         current_criteria={
                             'budget': budget,
                             'range_requirement': range_requirement,
                             'passengers': passengers,
                             'max_annual_cost': max_annual_cost,
                             'max_hourly_cost': max_hourly_cost,
                             'sort_by': sort_by
                         })

# Unify aircraft listings under Jet Finder
@app.route('/aircraft-listings')
def aircraft_listings():
    return redirect(url_for('home'))


@app.route('/compare')
def compare_aircraft():
    """Dedicated comparison page for selected aircraft IDs from CSV data.
    Usage: /compare?ids=1,2,3
    """
    ids_param = request.args.get('ids', '').strip()
    if not ids_param:
        flash('No aircraft selected for comparison.', 'info')
        return redirect(url_for('home'))
    try:
        raw_ids = [i for i in ids_param.replace(' ', '').split(',') if i]
        ids = []
        for rid in raw_ids:
            # marketplace listings may be 'listing_...' – skip for this compare
            if rid.isdigit():
                ids.append(int(rid))
        selected = [ac for ac in AIRCRAFT_DATA if ac.get('id') in ids]
    except Exception:
        selected = []
    if not selected:
        flash('Could not find selected aircraft to compare.', 'warning')
        return redirect(url_for('home'))

    # Metrics to render in comparison table
    metrics = [
        ('price', 'Price', 'USD'),
        ('year', 'Year', ''),
        ('passengers', 'Passengers', ''),
        ('range', 'Range (nm)', ''),
        ('speed', 'Speed (kts)', ''),
        ('max_altitude', 'Ceiling (ft)', ''),
        ('runway_length', 'Runway (ft)', ''),
        ('cabin_volume', 'Cabin Volume (ft³)', ''),
        ('baggage_volume', 'Baggage Volume (ft³)', ''),
        ('total_hourly_cost', 'Hourly Cost (USD)', ''),
        ('best_all_around_dollar', 'All-Around $', ''),
    ]
    return render_template('compare.html', aircraft=selected, metrics=metrics)

@app.route('/aircraft-detail/<int:aircraft_id>')
def aircraft_details(aircraft_id):
    """Aircraft detail page"""
    # Find aircraft in our data
    aircraft = None
    for a in AIRCRAFT_DATA:
        if a.get('id') == aircraft_id:
            aircraft = a
            break
    
    if not aircraft:
        flash('Aircraft not found', 'error')
        return redirect(url_for('aircraft_listings'))
    
    return render_template('aircraft_detail.html', aircraft=aircraft)

@app.route('/marketplace-search')
def marketplace_search():
    """Marketplace search page"""
    return render_template('marketplace/listings.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard (login required)."""
    user = get_current_user_info()
    return render_template('dashboard.html', user=user, subscription=user.get('subscription') if user else None)

@app.route('/airplane-stock-market')
def airplane_stock_market():
    """Main Airplane Stock Market page with enhanced scoring and price charts"""
    return render_template('airplane_stock_market.html')

@app.route('/api/stock-market-overview')
def api_stock_market_overview():
    """Get Robinhood-style aircraft market data with all 316 aircraft as tradeable assets"""
    try:
        import random
        from datetime import datetime, timedelta
        
        # Use real aircraft data from CSV - all 316 aircraft
        aircraft_models = []
        
        for aircraft in AIRCRAFT_DATA:
            # Get price data - if no price, assign reasonable value based on category
            current_price = aircraft.get('price', 0)
            if current_price <= 0:
                # Assign reasonable default prices based on aircraft type
                manufacturer = aircraft.get('manufacturer', '').lower()
                model = aircraft.get('model', '').lower()
                passengers = aircraft.get('passengers', 0)
                
                if 'piston' in model or passengers <= 4:
                    current_price = 150000  # Small piston aircraft
                elif 'turboprop' in model or passengers <= 8:
                    current_price = 2500000  # Turboprop
                elif passengers <= 12:
                    current_price = 8000000  # Light jet
                else:
                    current_price = 25000000  # Heavy jet
                
            manufacturer = aircraft.get('manufacturer', 'Unknown')
            model = aircraft.get('model', 'Unknown')
            
            # Generate realistic price movements (±5% variation)
            price_variation = random.uniform(-0.05, 0.05)
            price_change = int(current_price * price_variation)
            price_change_percent = round(price_variation * 100, 2)
            
            # Determine aircraft category
            category = categorize_aircraft(aircraft)
            
            # Generate market data for different time periods
            def generate_market_data(base_price, volatility_factor):
                return {
                    'high': int(base_price * (1 + random.uniform(0.02, 0.08) * volatility_factor)),
                    'low': int(base_price * (1 - random.uniform(0.02, 0.08) * volatility_factor)),
                    'volume': random.randint(1, 15),
                    'listings': random.randint(3, 25)
                }
            
            aircraft_model = {
                'id': aircraft.get('id', len(aircraft_models) + 1),
                'manufacturer': manufacturer,
                'model': model,
                'category': category,
                'current_price': current_price,
                'price_change': price_change,
                'price_change_percent': price_change_percent,
                'year': aircraft.get('year', 2020),
                'range': aircraft.get('range', 0),
                'speed': aircraft.get('speed', 0),
                'passengers': aircraft.get('passengers', 0),
                'market_data': {
                    '1d': generate_market_data(current_price, 0.3),
                    '1w': generate_market_data(current_price, 0.5),
                    '1m': generate_market_data(current_price, 0.8),
                    '3m': generate_market_data(current_price, 1.2),
                    '6m': generate_market_data(current_price, 1.5),
                    '1y': generate_market_data(current_price, 2.0),
                    'max': generate_market_data(current_price, 3.0)
                },
                'chart_data': {
                    '1d': [current_price + random.randint(-50000, 50000) for _ in range(24)],
                    '1w': [current_price + random.randint(-200000, 200000) for _ in range(7)],
                    '1m': [current_price + random.randint(-500000, 500000) for _ in range(30)],
                    '3m': [current_price + random.randint(-800000, 800000) for _ in range(90)],
                    '6m': [current_price + random.randint(-1200000, 1200000) for _ in range(180)],
                    '1y': [current_price + random.randint(-1500000, 1500000) for _ in range(365)],
                    'max': [current_price + random.randint(-2000000, 2000000) for _ in range(1000)]
                }
            }
            aircraft_models.append(aircraft_model)
        
        # Sort by price change percentage for "biggest movers" by default
        aircraft_models.sort(key=lambda x: abs(x['price_change_percent']), reverse=True)
        
        # Calculate market summary statistics
        total_models = len(aircraft_models)
        gainers = len([x for x in aircraft_models if x['price_change'] > 0])
        decliners = len([x for x in aircraft_models if x['price_change'] < 0])
        unchanged = total_models - gainers - decliners
        
        avg_price = sum(x['current_price'] for x in aircraft_models) / total_models if total_models > 0 else 0
        total_volume = sum(x['market_data']['1d']['volume'] for x in aircraft_models)
        
        return jsonify({
            'aircraft_models': aircraft_models,
            'market_summary': {
                'total_models': total_models,
                'gainers': gainers,
                'decliners': decliners,
                'unchanged': unchanged,
                'avg_price': avg_price,
                'total_volume': total_volume,
                'last_updated': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        print(f"Error in stock market API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock-market-test')
def api_stock_market_test():
    """Test endpoint to verify data loading"""
    try:
        return jsonify({
            'status': 'success',
            'total_aircraft_in_csv': len(AIRCRAFT_DATA),
            'total_aircraft_loaded': len(AIRCRAFT_DATA),
            'sample_aircraft_names': [aircraft.get('aircraft_name', 'Unknown') for aircraft in AIRCRAFT_DATA[:5]],
            'api_endpoint_available': True
        })
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500


# Lightweight aircraft details API for comparison/details modals
@app.route('/api/aircraft-detail/<int:aircraft_id>')
def api_aircraft_detail(aircraft_id: int):
    """Return a single aircraft from AIRCRAFT_DATA by numeric id as JSON."""
    try:
        for aircraft in AIRCRAFT_DATA:
            if aircraft.get('id') == aircraft_id:
                return jsonify({'success': True, 'aircraft': aircraft})
        return jsonify({'success': False, 'error': 'Aircraft not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/aircraft-data')
def api_aircraft_data():
    """Get all aircraft data for JavaScript frontend"""
    try:
        aircraft_data = get_unified_aircraft_data()
        return jsonify(aircraft_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Fallback airport list when JSON file is missing (e.g. on some hosts)
_AIRPORTS_FALLBACK = [
    {'iata': 'LAX', 'icao': 'KLAX', 'name': 'Los Angeles International', 'city': 'Los Angeles', 'country': 'United States', 'lat': 33.9425, 'lon': -118.4081},
    {'iata': 'JFK', 'icao': 'KJFK', 'name': 'John F Kennedy International', 'city': 'New York', 'country': 'United States', 'lat': 40.6398, 'lon': -73.7789},
    {'iata': 'ORD', 'icao': 'KORD', 'name': 'Chicago O\'Hare International', 'city': 'Chicago', 'country': 'United States', 'lat': 41.9786, 'lon': -87.9047},
    {'iata': 'DFW', 'icao': 'KDFW', 'name': 'Dallas Fort Worth International', 'city': 'Dallas', 'country': 'United States', 'lat': 32.8968, 'lon': -97.0380},
    {'iata': 'ATL', 'icao': 'KATL', 'name': 'Hartsfield-Jackson Atlanta International', 'city': 'Atlanta', 'country': 'United States', 'lat': 33.6367, 'lon': -84.4281},
]

def _load_airports_data():
    """Load airports from PostgreSQL/SQLite (seeded from JSON on first run). Falls back to file if DB empty."""
    try:
        airports = db_module.get_all_airports()
        if airports:
            return airports
        db_module.seed_aircraft_and_airports()
        airports = db_module.get_all_airports()
        if airports:
            return airports
    except Exception as e:
        logger.warning("DB airports load failed, falling back to file: %s", e, exc_info=True)
    # Fallback: load from file
    _base = Path(__file__).resolve().parent
    for _path in [_base / 'static' / 'data' / 'airports.json', _base / 'airports.json']:
        if _path.is_file():
            try:
                with open(_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not load %s: %s", _path, e)
    logger.warning("Airport data file not found; using fallback list")
    return _AIRPORTS_FALLBACK

@app.route('/api/debug')
def api_debug():
    """Debug route to verify app.py is running"""
    return jsonify({
        'app': 'app.py',
        'routes': ['/api/airports', '/api/user-listings'],
        'airports_route_exists': True
    }), 200

@app.route('/api/health')
def api_health():
    """Health check: db_ok, table counts, aircraft/airports loaded (Railway debugging)."""
    try:
        db_status = db_module.get_database_status()
        airports_data = _load_airports_data()
        airports_count = len(airports_data) if isinstance(airports_data, list) else 0
        aircraft_count = len(AIRCRAFT_DATA) if AIRCRAFT_DATA else 0
        return jsonify({
            'status': 'ok' if db_status['db_ok'] else 'db_error',
            'timestamp': int(datetime.now().timestamp() * 1000),
            'db_ok': db_status['db_ok'],
            'database_type': db_status['database_type'],
            'connection_error': db_status.get('connection_error'),
            'table_counts': db_status.get('table_counts', {}),
            'aircraft_count': aircraft_count,
            'airports_count': airports_count,
            'data_loaded': {
                'airports': airports_count,
                'aircraft': aircraft_count,
            },
        }), 200
    except Exception as e:
        logger.exception("Error in /api/health")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/diagnostic')
def api_diagnostic():
    """Railway debugging: DB status, table counts, connection errors, file fallbacks (no secrets)."""
    _base = Path(__file__).resolve().parent
    aircraft_candidates = [
        _base / 'static' / 'data' / 'aircraft_data.csv',
        _base / 'Aircraft Data - Aircraft Data (1).csv',
        _base / 'static' / 'data' / 'Aircraft Data - Aircraft Data (1).csv',
    ]
    airports_candidates = [
        _base / 'static' / 'data' / 'airports.json',
        _base / 'airports.json',
    ]
    aircraft_found = next((str(p) for p in aircraft_candidates if p.is_file()), None)
    airports_found = next((str(p) for p in airports_candidates if p.is_file()), None)
    db_url = os.environ.get('DATABASE_URL', '')
    db_status = db_module.get_database_status()
    ap_data = _load_airports_data()
    airports_count = len(ap_data) if isinstance(ap_data, list) else 0
    return jsonify({
        'app_root': str(_base),
        'has_database_url': bool(db_url),
        'database_type': db_status['database_type'],
        'db_ok': db_status['db_ok'],
        'connection_error': db_status.get('connection_error'),
        'table_counts': db_status.get('table_counts', {}),
        'aircraft_paths_tried': [str(p) for p in aircraft_candidates],
        'aircraft_file_found': aircraft_found,
        'airports_paths_tried': [str(p) for p in airports_candidates],
        'airports_file_found': airports_found,
        'aircraft_count': len(AIRCRAFT_DATA) if AIRCRAFT_DATA else 0,
        'airports_count': airports_count,
    }), 200

@app.route('/api/airports')
def api_airports():
    """Airport search API endpoint"""
    try:
        query = request.args.get('q', '').strip().upper()
        
        if not query or len(query) < 2:
            return jsonify([])
        
        airports = _load_airports_data()
        
        # Search airports by IATA code, ICAO code, name, or city
        matching_airports = []
        for airport in airports:
            # Check IATA code (primary search)
            if airport.get('iata', '').upper().startswith(query):
                matching_airports.append({
                    'iata': airport.get('iata', ''),
                    'icao': airport.get('icao', ''),
                    'name': airport.get('name', ''),
                    'city': airport.get('city', ''),
                    'country': airport.get('country', ''),
                    'lat': airport.get('lat', 0),
                    'lon': airport.get('lon', 0),
                    'match_type': 'iata'
                })
            # Check ICAO code
            elif airport.get('icao', '').upper().startswith(query):
                matching_airports.append({
                    'iata': airport.get('iata', ''),
                    'icao': airport.get('icao', ''),
                    'name': airport.get('name', ''),
                    'city': airport.get('city', ''),
                    'country': airport.get('country', ''),
                    'lat': airport.get('lat', 0),
                    'lon': airport.get('lon', 0),
                    'match_type': 'icao'
                })
            # Check name and city (partial matches)
            elif (query in airport.get('name', '').upper() or 
                  query in airport.get('city', '').upper()):
                matching_airports.append({
                    'iata': airport.get('iata', ''),
                    'icao': airport.get('icao', ''),
                    'name': airport.get('name', ''),
                    'city': airport.get('city', ''),
                    'country': airport.get('country', ''),
                    'lat': airport.get('lat', 0),
                    'lon': airport.get('lon', 0),
                    'match_type': 'name_city'
                })
        
        # Sort by match type priority (IATA first, then ICAO, then name/city)
        # and limit results to prevent overwhelming the UI
        matching_airports.sort(key=lambda x: (
            0 if x['match_type'] == 'iata' else 
            1 if x['match_type'] == 'icao' else 2,
            x['name']
        ))
        
        # Return up to 20 results
        return jsonify(matching_airports[:20])
        
    except Exception as e:
        print(f"Error in airports API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/available-columns')
def api_available_columns():
    """Get available CSV columns for dynamic filtering"""
    try:
        # Return the available columns from the aircraft data
        if not AIRCRAFT_DATA:
            return jsonify([])
        
        # Get all keys from the first aircraft record
        sample_aircraft = AIRCRAFT_DATA[0]
        columns = list(sample_aircraft.keys())
        
        # Filter out technical fields and return user-friendly column names
        user_friendly_columns = []
        for col in columns:
            if col not in ['id', 'image', 'description']:
                # Convert snake_case to Title Case
                friendly_name = col.replace('_', ' ').title()
                user_friendly_columns.append({
                    'key': col,
                    'name': friendly_name,
                    'type': 'numeric' if isinstance(sample_aircraft.get(col), (int, float)) else 'text'
                })
        
        return jsonify(user_friendly_columns)
        
    except Exception as e:
        print(f"Error in available columns API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/priority-metrics')
def api_priority_metrics():
    """Get priority metrics for aircraft analysis"""
    try:
        # Return standard priority metrics used in aircraft evaluation
        metrics = [
            {
                'key': 'price',
                'name': 'Purchase Price',
                'description': 'Aircraft acquisition cost',
                'weight': 25,
                'type': 'numeric',
                'unit': 'USD',
                'lower_is_better': True
            },
            {
                'key': 'range',
                'name': 'Range',
                'description': 'Maximum flight range',
                'weight': 20,
                'type': 'numeric',
                'unit': 'NM',
                'lower_is_better': False
            },
            {
                'key': 'speed',
                'name': 'Cruise Speed',
                'description': 'Normal cruise speed',
                'weight': 15,
                'type': 'numeric',
                'unit': 'KTS',
                'lower_is_better': False
            },
            {
                'key': 'passengers',
                'name': 'Passenger Capacity',
                'description': 'Maximum number of passengers',
                'weight': 15,
                'type': 'numeric',
                'unit': 'seats',
                'lower_is_better': False
            },
            {
                'key': 'total_hourly_cost',
                'name': 'Hourly Operating Cost',
                'description': 'Total cost per flight hour',
                'weight': 15,
                'type': 'numeric',
                'unit': 'USD/hr',
                'lower_is_better': True
            },
            {
                'key': 'runway_length',
                'name': 'Runway Length Required',
                'description': 'Minimum runway length needed',
                'weight': 10,
                'type': 'numeric',
                'unit': 'ft',
                'lower_is_better': True
            }
        ]
        
        return jsonify(metrics)
        
    except Exception as e:
        print(f"Error in priority metrics API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calculate-priority-ranking', methods=['POST'])
def api_calculate_priority_ranking():
    """Calculate priority ranking based on user weightings using the new scoring system"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        priorities = data.get('priorities', {})
        user_inputs = data.get('user_inputs', {})
        
        # Validate priorities have weights
        if not priorities:
            return jsonify({'error': 'No priorities specified'}), 400
        
        # Calculate final recommendation scores for all aircraft
        # First, filter aircraft based on hard requirements
        filtered_aircraft = []
        
        for aircraft in AIRCRAFT_DATA:
            # Check if aircraft meets all hard requirements
            meets_requirements = True
            
            # Budget filter - exclude aircraft over budget
            budget = user_inputs.get('budget', 0)
            if budget and aircraft.get('price', 0) > budget:
                meets_requirements = False
                continue
            
            # Range filter - exclude aircraft with insufficient range
            required_range = user_inputs.get('range_requirement', 0)
            if required_range and aircraft.get('range', 0) < required_range:
                meets_requirements = False
                continue
            
            # Passenger filter - exclude aircraft with insufficient capacity
            required_passengers = user_inputs.get('passengers', 0)
            if required_passengers and aircraft.get('passengers', 0) < required_passengers:
                meets_requirements = False
                continue
            
            # Year filter - exclude aircraft older than specified
            lowest_year = user_inputs.get('lowest_year', 0)
            if lowest_year and aircraft.get('year', 0) < lowest_year:
                meets_requirements = False
                continue
            
            # Speed filter - exclude aircraft below minimum speed
            min_speed = user_inputs.get('min_speed', 0)
            if min_speed and aircraft.get('speed', 0) < min_speed:
                meets_requirements = False
                continue
            
            # Altitude filter - exclude aircraft below minimum altitude
            min_altitude = user_inputs.get('min_altitude', 0)
            if min_altitude and aircraft.get('max_altitude', 0) < min_altitude:
                meets_requirements = False
                continue
            
            # Runway filter - exclude aircraft requiring longer runways
            max_runway = user_inputs.get('max_runway', 0)
            if max_runway and aircraft.get('runway_length', 0) > max_runway:
                meets_requirements = False
                continue
            
            # Cabin volume filter - exclude aircraft with insufficient cabin space
            min_cabin_volume = user_inputs.get('min_cabin_volume', 0)
            if min_cabin_volume and aircraft.get('cabin_volume', 0) < min_cabin_volume:
                meets_requirements = False
                continue
            
            # Annual cost filter - exclude aircraft over annual cost limit
            max_annual_cost = user_inputs.get('max_annual_cost', 0)
            if max_annual_cost and aircraft.get('total_hourly_cost', 0) * user_inputs.get('yearly_trips', 100) > max_annual_cost:
                meets_requirements = False
                continue
            
            # Hourly cost filter - exclude aircraft over hourly cost limit
            max_hourly_cost = user_inputs.get('max_hourly_cost', 0)
            if max_hourly_cost and aircraft.get('total_hourly_cost', 0) > max_hourly_cost:
                meets_requirements = False
                continue
            
            # If aircraft meets all requirements, add to filtered list
            if meets_requirements:
                filtered_aircraft.append(aircraft)
        
        # Calculate scores for filtered aircraft only
        ranked_aircraft = []
        
        for aircraft in filtered_aircraft:
            # Calculate final recommendation score using the new system
            score_result = calculate_final_recommendation_score(aircraft, priorities, user_inputs)
            
            ranked_aircraft.append({
                'aircraft': aircraft,
                'final_score': score_result['final_score'],
                'spreadsheet_score': score_result['spreadsheet_score'],
                'priority_score': score_result['priority_score'],
                'combined_score': score_result['combined_score'],
                'all_around_score': score_result['all_around_score'],
                'scoring_breakdown': score_result['breakdown']
            })
        
        # Sort by final score (highest first)
        ranked_aircraft.sort(key=lambda x: x['final_score'], reverse=True)
        
        return jsonify({
            'rankings': ranked_aircraft,  # Return all filtered aircraft
            'total_filtered': len(filtered_aircraft),
            'total_available': len(AIRCRAFT_DATA),
            'filters_applied': user_inputs,
            'scoring_methodology': {
                'step_1': 'Calculate spreadsheet score (average of 5 per-dollar metrics)',
                'step_2': 'Calculate priority score (weighted user preferences)',
                'step_3': 'Average spreadsheet and priority scores',
                'step_4': 'Average result with all-around/$ score',
                'step_5': 'Final recommendation percentage',
                'description': 'Comprehensive scoring combining objective performance metrics with user priorities'
            }
        })
        
    except Exception as e:
        print(f"Error in priority ranking API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calculate-aircraft', methods=['POST'])
def api_calculate_aircraft():
    """Calculate aircraft recommendations based on user inputs and mission requirements"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_inputs = data.get('user_inputs', {})
        mission_profile = data.get('mission_profile', {})
        
        # Get unified data (CSV + marketplace listings)
        all_aircraft = get_unified_aircraft_data()
        
        # First, apply strict hard filtering - aircraft that don't meet criteria are EXCLUDED
        filtered_aircraft = []
        filters_applied = {}
        
        for aircraft in all_aircraft:
            # STRICT HARD FILTERING - Aircraft not meeting ANY criteria are excluded
            meets_requirements = True
            exclusion_reasons = []
            
            # Budget filter - HARD EXCLUDE aircraft over budget
            budget = user_inputs.get('budget', 0)
            if budget and budget > 0:
                filters_applied['budget'] = budget
                aircraft_price = aircraft.get('price', 0)
                if aircraft_price > budget:
                    meets_requirements = False
                    exclusion_reasons.append(f"Price ${aircraft_price:,} exceeds budget ${budget:,}")
                    continue
            
            # Range filter - exclude aircraft with insufficient range
            required_range = user_inputs.get('range_requirement', 0)
            if required_range and aircraft.get('range', 0) < required_range:
                meets_requirements = False
                continue
            
            # Passenger filter - exclude aircraft with insufficient capacity
            required_passengers = user_inputs.get('passengers', 0)
            if required_passengers and aircraft.get('passengers', 0) < required_passengers:
                meets_requirements = False
                continue
            
            # Year filter - exclude aircraft older than specified
            lowest_year = user_inputs.get('lowest_year', 0)
            if lowest_year and aircraft.get('year', 0) < lowest_year:
                meets_requirements = False
                continue
            
            # Speed filter - exclude aircraft below minimum speed
            min_speed = user_inputs.get('min_speed', 0)
            if min_speed and aircraft.get('speed', 0) < min_speed:
                meets_requirements = False
                continue
            
            # Altitude filter - exclude aircraft below minimum altitude
            min_altitude = user_inputs.get('min_altitude', 0)
            if min_altitude and aircraft.get('max_altitude', 0) < min_altitude:
                meets_requirements = False
                continue
            
            # Runway filter - exclude aircraft requiring longer runways
            max_runway = user_inputs.get('max_runway', 0)
            if max_runway and aircraft.get('runway_length', 0) > max_runway:
                meets_requirements = False
                continue
            
            # Cabin volume filter - exclude aircraft with insufficient cabin space
            min_cabin_volume = user_inputs.get('min_cabin_volume', 0)
            if min_cabin_volume and aircraft.get('cabin_volume', 0) < min_cabin_volume:
                meets_requirements = False
                continue
            
            # Annual cost filter - exclude aircraft over annual cost limit
            max_annual_cost = user_inputs.get('max_annual_cost', 0)
            if max_annual_cost and aircraft.get('total_hourly_cost', 0) * user_inputs.get('yearly_trips', 100) > max_annual_cost:
                meets_requirements = False
                continue
            
            # Hourly cost filter - exclude aircraft over hourly cost limit
            max_hourly_cost = user_inputs.get('max_hourly_cost', 0)
            if max_hourly_cost and aircraft.get('total_hourly_cost', 0) > max_hourly_cost:
                meets_requirements = False
                continue
            
            # If aircraft meets all requirements, add to filtered list
            if meets_requirements:
                filtered_aircraft.append(aircraft)
        
        # Calculate comprehensive scores for filtered aircraft only using the 50/50 system
        recommendations = []
        
        # Convert mission_profile to priorities format for scoring
        priorities = {}
        if mission_profile:
            for key, value in mission_profile.items():
                if value and value != '':
                    priorities[value] = 1.0  # Equal weight for selected priorities
        
        for aircraft in filtered_aircraft:
            # Use the bulletproof 50/50 scoring system
            score_result = calculate_final_recommendation_score(aircraft, priorities, user_inputs)
            
            recommendations.append({
                'aircraft': aircraft,
                'total_score': score_result['final_score'],
                'final_score': score_result['final_score'],
                'scoring_details': {
                    'final_score': score_result['final_score'],
                    'spreadsheet_score': score_result['spreadsheet_score'],
                    'priority_score': score_result['priority_score'],
                    'breakdown': score_result['breakdown']
                },
                'display_score': score_result['final_score'],  # For compatibility
                'recommendation_reason': f"Score: {100 - score_result['final_score']:.1f}% (Spreadsheet: {100 - score_result['spreadsheet_score']:.1f}%, Priority: {100 - score_result['priority_score']:.1f}%)"
            })
        
        # Sort by final score (lower is better, so ascending)
        recommendations.sort(key=lambda x: x['final_score'])
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'total_filtered': len(filtered_aircraft),
            'total_available': len(all_aircraft),
            'filters_applied': filters_applied,
            'scoring_methodology': {
                'spreadsheet_weight': 50,
                'priority_weight': 50,
                'description': 'Strict 50/50 weighting between spreadsheet and priority scores'
            }
        })
        
    except Exception as e:
        print(f"Error in aircraft calculation API: {e}")
        return jsonify({'error': str(e)}), 500

def calculate_spreadsheet_score(aircraft, user_inputs=None):
    """
    Calculate spreadsheet-based score using the 5 key per-dollar metrics
    Returns a percentage score (0-100) based on performance per dollar
    """
    try:
        # Get the 5 key spreadsheet metrics (all normalized per-dollar values)
        speed_dollar = aircraft.get('normalized_speed_dollar', 0)
        range_dollar = aircraft.get('normalized_range_dollar', 0)
        performance_dollar = aircraft.get('normalized_performance_dollar', 0)
        efficiency_dollar = aircraft.get('normalized_efficiency_dollar', 0)
        all_around_dollar = aircraft.get('best_all_around_dollar', 0)
        
        # Collect valid metrics (non-zero values)
        valid_metrics = []
        for metric in [speed_dollar, range_dollar, performance_dollar, efficiency_dollar, all_around_dollar]:
            if metric and metric > 0:
                # Convert to percentage scale (0-100)
                percentage = min(100, max(0, metric * 10))  # Scale factor of 10
                valid_metrics.append(percentage)
        
        # Calculate average of valid metrics
        if valid_metrics:
            spreadsheet_score = sum(valid_metrics) / len(valid_metrics)
        else:
            spreadsheet_score = 0
        
        return max(0, min(100, spreadsheet_score))
        
    except Exception as e:
        print(f"Error calculating spreadsheet score: {e}")
        return 100

def calculate_priority_score(aircraft, priorities):
    """
    Calculate user priority score based on weighted preferences
    Returns a percentage score (0-100) based on how well aircraft matches user priorities
    """
    try:
        if not priorities:
            return 50  # Default score if no priorities specified
        
        weighted_scores = []
        total_weight = 0
        
        for metric_key, weight in priorities.items():
            if weight <= 0:
                continue
            
            # Get aircraft value for this metric
            aircraft_value = aircraft.get(metric_key, 0)
            if aircraft_value is None:
                continue
            
            # Normalize each metric to 0-100 scale
            normalized_score = normalize_metric_to_percentage(metric_key, aircraft_value)
            
            # Apply weight
            weighted_scores.append(normalized_score * weight)
            total_weight += weight
        
        # Calculate weighted average
        if total_weight > 0:
            priority_score = sum(weighted_scores) / total_weight
        else:
            priority_score = 50  # Default if no valid priorities
        
        return max(0, min(100, priority_score))
        
    except Exception as e:
        print(f"Error calculating priority score: {e}")
        return 100

def get_metric_bounds(metric_key):
    """
    Get the minimum and maximum values for a metric across all aircraft
    Returns (min_value, max_value) for proper 0-100% normalization
    """
    try:
        # Use current request's scoring dataset if available to ensure context-aware normalization
        global SCORING_DATASET
        source = SCORING_DATASET if SCORING_DATASET is not None else AIRCRAFT_DATA
        values = []
        for aircraft in source:
            value = aircraft.get(metric_key, 0)
            if value is not None and value > 0:
                values.append(value)
        
        if not values:
            return (0, 1)  # Default bounds if no valid values
        
        min_val = min(values)
        max_val = max(values)
        
        # Ensure we don't have division by zero
        if min_val == max_val:
            return (min_val, max_val + 1)
        
        return (min_val, max_val)
        
    except Exception as e:
        print(f"Error getting bounds for metric {metric_key}: {e}")
        return (0, 1)

def normalize_metric_to_percentage(metric_key, value):
    """
    Normalize different metrics to 0-100 percentage scale based on actual min/max values
    Best performing aircraft gets 100%, worst gets 0% (LOWER IS BETTER: lower value = higher score)
    """
    try:
        if value is None or value <= 0:
            return 0  # Worst
        # Get actual bounds for this metric across all aircraft
        min_val, max_val = get_metric_bounds(metric_key)
        # Handle edge case where all values are the same
        if min_val == max_val:
            return 50  # Middle score if all values are identical
        # Determine if higher or lower values are better
        higher_is_better = True  # Default assumption
        lower_is_better_metrics = [
            'price', 'total_hourly_cost', 'hourly_variable_cost', 
            'cost_per_mile', 'cost_per_seat_mile', 'runway_length',
            'depreciation_rate', 'variable_cost_per_seat', 
            'variable_cost_per_mile', 'variable_cost_per_seat_mile'
        ]
        if metric_key in lower_is_better_metrics:
            higher_is_better = False
        # Calculate normalized score (0-100, higher is always better)
        if higher_is_better:
            # Higher values are better: best gets 100, worst gets 0
            normalized = ((value - min_val) / (max_val - min_val)) * 100
        else:
            # Lower values are better: best gets 100, worst gets 0
            normalized = ((max_val - value) / (max_val - min_val)) * 100
        # Ensure score is within 0-100 range
        return max(0, min(100, normalized))
    except Exception as e:
        print(f"Error normalizing metric {metric_key}: {e}")
        return 0


# ===== Deal intelligence and upgrade detection =====
def _safe_lower(text):
    try:
        return (text or '').lower()
    except Exception:
        return ''


from typing import Tuple, List


def detect_upgrade_highlights(aircraft: dict) -> Tuple[bool, List[str]]:
    """Detect upgrade signals (interior/paint/avionics) from listing fields."""
    highlights = []
    desc = _safe_lower(aircraft.get('description', ''))
    avionics = _safe_lower(aircraft.get('avionics') or aircraft.get('avionics_description', ''))

    # Interior/paint cues
    interior_cues = ['new interior', 'refurb', 'interior redone', 'vvi', 'vip interior']
    paint_cues = ['new paint', 'repaint', 'fresh paint']
    if any(c in desc for c in interior_cues):
        highlights.append('Recent interior refurbishment')
    if any(c in desc for c in paint_cues):
        highlights.append('Recent exterior paint')

    # Avionics cues (tiers)
    superior_avionics = ['g5000', 'g3000', 'pro line fusion', 'symmetry flight deck', 'eas y iii', 'ace avionics']
    modern_avionics = ['pro line 21', 'g1000', 'perspective', 'avidyne r9']
    if any(a in avionics or a in desc for a in superior_avionics):
        highlights.append('Superior avionics suite')
    elif any(a in avionics or a in desc for a in modern_avionics):
        highlights.append('Modern avionics')

    is_upgraded = len(highlights) > 0
    return is_upgraded, highlights


def compute_category_medians(dataset: list) -> dict:
    """Compute median price per inferred category over dataset."""
    from statistics import median
    buckets = {}
    for a in dataset:
        price = a.get('price', 0) or 0
        if price <= 0:
            continue
        cat = categorize_aircraft(a)
        buckets.setdefault(cat, []).append(price)
    med = {}
    for cat, prices in buckets.items():
        try:
            med[cat] = median(prices)
        except Exception:
            if prices:
                med[cat] = prices[len(prices)//2]
    return med


def annotate_deal_intelligence(aircraft_list: list, reference_dataset: list):
    """Annotate each aircraft with deal intelligence: upgrade flags and value tags.
    Uses category median price as a simple market baseline.
    """
    medians = compute_category_medians(reference_dataset)
    for a in aircraft_list:
        is_upgraded, highlights = detect_upgrade_highlights(a)
        price = a.get('price', 0) or 0
        cat = categorize_aircraft(a)
        median_price = medians.get(cat)
        value_tag = 'Unknown'
        relative_price = 'Unknown'
        if price > 0 and median_price:
            ratio = price / median_price
            if ratio <= 0.85:
                value_tag = 'Great Deal'
                relative_price = 'Below Market'
            elif ratio <= 1.05:
                value_tag = 'Fair Value'
                relative_price = 'At Market'
            else:
                value_tag = 'Premium'
                relative_price = 'Above Market'
        a['deal_info'] = {
            'is_upgraded': is_upgraded,
            'highlights': highlights,
            'relative_price': relative_price,
            'value_tag': value_tag,
        }

def calculate_final_recommendation_score(aircraft, priorities, user_inputs=None):
    """
    Calculate the final recommendation score with STRICT 50/50 weighting:
    1. Calculate spreadsheet score (average of 5 per-dollar metrics) - 50%
    2. Calculate priority score (weighted user preferences) - 50%
    3. Final score = (Spreadsheet Score × 0.5) + (Priority Score × 0.5)
    4. Return final recommendation percentage (LOWER IS BETTER)
    """
    try:
        # Step 1: Calculate spreadsheet score (0-100, lower is better)
        spreadsheet_score = calculate_spreadsheet_score(aircraft, user_inputs)
        
        # Step 2: Calculate priority score (0-100, lower is better)
        priority_score = calculate_priority_score(aircraft, priorities)
        
        # Step 3: ENFORCED 50/50 weighting - NO averaging with all-around score
        final_score = (spreadsheet_score * 0.5) + (priority_score * 0.5)
        final_score = max(0, min(100, final_score))
        
        # Get all-around/$ for reference but don't include in final score
        all_around_dollar = aircraft.get('best_all_around_dollar', 0)
        all_around_percentage = (all_around_dollar * 10) if all_around_dollar > 0 else 0
        all_around_percentage = max(0, min(100, all_around_percentage))
        
        return {
            'final_score': final_score,
            'spreadsheet_score': spreadsheet_score,
            'priority_score': priority_score,
            'spreadsheet_weight': 50.0,
            'priority_weight': 50.0,
            'all_around_score': all_around_percentage,  # For reference only
            'breakdown': {
                'calculation': f"({spreadsheet_score:.1f} × 0.5) + ({priority_score:.1f} × 0.5) = {final_score:.1f}",
                'spreadsheet_components': get_spreadsheet_breakdown(aircraft),
                'priority_components': get_priority_breakdown(aircraft, priorities),
                'all_around_value': all_around_dollar,
                'scoring_method': 'Strict 50/50 weighting between spreadsheet and priority scores'
            }
        }
        
    except Exception as e:
        print(f"Error calculating final recommendation score: {e}")
        return {
            'final_score': 100,
            'spreadsheet_score': 100,
            'priority_score': 100,
            'combined_score': 100,
            'all_around_score': 100,
            'breakdown': {}
        }

def get_spreadsheet_breakdown(aircraft):
    """Get detailed breakdown of spreadsheet metrics"""
    return {
        'speed_per_dollar': aircraft.get('normalized_speed_dollar', 0),
        'range_per_dollar': aircraft.get('normalized_range_dollar', 0),
        'performance_per_dollar': aircraft.get('normalized_performance_dollar', 0),
        'efficiency_per_dollar': aircraft.get('normalized_efficiency_dollar', 0),
        'all_around_per_dollar': aircraft.get('best_all_around_dollar', 0)
    }

def get_priority_breakdown(aircraft, priorities):
    """Get detailed breakdown of priority scoring"""
    breakdown = {}
    for metric_key, weight in priorities.items():
        aircraft_value = aircraft.get(metric_key, 0)
        normalized_score = normalize_metric_to_percentage(metric_key, aircraft_value)
        breakdown[metric_key] = {
            'raw_value': aircraft_value,
            'normalized_score': normalized_score,
            'weight': weight,
            'weighted_score': normalized_score * weight
        }
    return breakdown

def calculate_mission_fit_score(aircraft, user_inputs, mission_profile):
    """Calculate how well aircraft fits mission requirements"""
    try:
        score = 100
        
        # Check range requirements
        required_range = user_inputs.get('range_requirement', 0)
        if required_range and aircraft.get('range', 0) < required_range:
            score -= 30  # Major penalty for insufficient range
        
        # Check passenger requirements
        required_passengers = user_inputs.get('passengers', 0)
        if required_passengers and aircraft.get('passengers', 0) < required_passengers:
            score -= 25  # Major penalty for insufficient capacity
        
        # Check budget constraints
        budget = user_inputs.get('budget', 0)
        if budget and aircraft.get('price', 0) > budget:
            score -= 40  # Major penalty for over budget
        
        # Check runway requirements
        runway_available = user_inputs.get('runway_length', 0)
        runway_required = aircraft.get('runway_length', 0)
        if runway_available and runway_required and runway_required > runway_available:
            score -= 20  # Penalty for runway incompatibility
        
        return max(0, score)
        
    except Exception as e:
        print(f"Error calculating mission fit score: {e}")
        return 50

def calculate_value_performance_score(aircraft):
    """Calculate value performance based on spreadsheet metrics"""
    try:
                # Use the comprehensive value metrics from spreadsheet
        value_metrics = [
            aircraft.get('best_speed_dollar', 0),
            aircraft.get('best_range_dollar', 0),
            aircraft.get('best_performance_dollar', 0),
            aircraft.get('best_efficiency_dollar', 0),
            aircraft.get('best_all_around_dollar', 0)
        ]
        
        # Normalize and average
        normalized_values = []
        for metric in value_metrics:
            if metric and metric > 0:
                normalized_values.append(min(100, metric * 5))  # Scale factor
        
        score = sum(normalized_values) / len(normalized_values) if normalized_values else 50
        return max(0, min(100, score))
        
    except Exception as e:
        print(f"Error calculating value performance score: {e}")
        return 100

def calculate_efficiency_score(aircraft, user_inputs):
    """Calculate operational efficiency score"""
    try:
        efficiency_factors = []
        
        # Operating cost efficiency
        hourly_cost = aircraft.get('total_hourly_cost', 0)
        if hourly_cost:
            # Lower cost per seat is better
            passengers = aircraft.get('passengers', 1)
            cost_per_seat = hourly_cost / passengers
            efficiency_factors.append(max(0, 100 - (cost_per_seat / 1000)))  # Normalize
        
        # Fuel efficiency (cost per mile)
        cost_per_mile = aircraft.get('cost_per_mile', 0)
        if cost_per_mile:
            efficiency_factors.append(max(0, 100 - cost_per_mile))
        
        # Range efficiency
        range_value = aircraft.get('range', 0)
        price = aircraft.get('price', 1)
        if range_value and price:
            range_efficiency = (range_value / price) * 1000000  # Normalize
            efficiency_factors.append(min(100, range_efficiency))
        
        score = sum(efficiency_factors) / len(efficiency_factors) if efficiency_factors else 50
        return max(0, min(100, score))
        
    except Exception as e:
        print(f"Error calculating efficiency score: {e}")
        return 100

def get_value_metrics(aircraft):
    """Get detailed value metrics for breakdown"""
    return {
        'speed_per_dollar': aircraft.get('best_speed_dollar', 0),
        'range_per_dollar': aircraft.get('best_range_dollar', 0),
        'performance_per_dollar': aircraft.get('best_performance_dollar', 0),
        'efficiency_per_dollar': aircraft.get('best_efficiency_dollar', 0),
        'all_around_value': aircraft.get('best_all_around_dollar', 0)
    }

def get_operational_fit(aircraft, user_inputs):
    """Get operational fit metrics"""
    return {
        'range_adequacy': aircraft.get('range', 0) >= user_inputs.get('range_requirement', 0),
        'passenger_adequacy': aircraft.get('passengers', 0) >= user_inputs.get('passengers', 0),
        'budget_fit': aircraft.get('price', 0) <= user_inputs.get('budget', float('inf')),
        'runway_compatibility': aircraft.get('runway_length', 0) <= user_inputs.get('runway_length', float('inf'))
    }

def get_priority_alignment(aircraft, priorities):
    """Get priority alignment scores"""
    alignment = {}
    for metric, weight in priorities.items():
        value = aircraft.get(metric, 0)
        alignment[metric] = {
            'value': value,
            'weight': weight,
            'normalized_score': calculate_priority_score(aircraft, {metric: weight})
        }
    return alignment

def generate_recommendation_reason(aircraft, user_inputs, mission_score, value_score, efficiency_score):
    """Generate explanation for recommendation"""
    reasons = []
    
    if mission_score >= 80:
        reasons.append("Excellent mission fit")
    elif mission_score >= 60:
        reasons.append("Good mission compatibility")
    
    if value_score >= 80:
        reasons.append("Outstanding value for money")
    elif value_score >= 60:
        reasons.append("Good performance per dollar")
    
    if efficiency_score >= 80:
        reasons.append("Highly efficient operations")
    elif efficiency_score >= 60:
        reasons.append("Reasonable operating costs")
    
    if not reasons:
        reasons.append("Meets basic requirements")
    
    return "; ".join(reasons)

def categorize_aircraft(aircraft):
    """Categorize aircraft based on various attributes"""
    price = aircraft.get('price', 0)
    passengers = aircraft.get('passengers', 0)
    manufacturer = aircraft.get('manufacturer', '').lower()
    model = aircraft.get('model', '').lower()
    multi_engine = aircraft.get('multi_engine', '').lower()
    
    # Light Aircraft (under $10M, typically 4-8 passengers)
    if price < 10000000 or passengers <= 8:
        if 'turboprop' in model or 'prop' in model or multi_engine == 'no':
            return 'Turboprop'
        return 'Light Jet'
    
    # Midsize Aircraft ($10M-$40M, typically 8-12 passengers)
    elif price < 40000000 or passengers <= 12:
        return 'Midsize Jet'
    
    # Heavy Aircraft (over $40M or more than 12 passengers)
    else:
        return 'Heavy Jet'

def get_current_user_info():
    """Get current user information for templates"""
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if user:
            subscription = get_user_subscription(user['id'])
            user['subscription'] = subscription
            return user
    return None

# Setup Jinja globals now that get_current_user_info is defined
def setup_jinja_globals():
    """Setup Jinja2 global functions"""
    app.jinja_env.globals.update(get_current_user_info=get_current_user_info)

# Call setup immediately
setup_jinja_globals()

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = get_user_by_email(email)
        if user and password and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            flash('Successfully logged in!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        company = request.form.get('company')
        phone = request.form.get('phone')
        
        if get_user_by_email(email):
            flash('Email already registered', 'error')
        else:
            user_id = create_user(email, password, first_name, last_name, company, phone)
            if user_id is not None:
                session['user_id'] = user_id
                flash('Account created successfully!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Error creating account', 'error')
    
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('Successfully logged out', 'success')
    return redirect(url_for('home'))

# Pro subscription removed - upgrade route removed

@app.route('/priority-ranking')
@login_required
def priority_ranking():
    """Priority ranking tool"""
    return render_template('aircraft_recommendations.html')

@app.route('/pricing')
def pricing():
    """Pricing page"""
    return render_template('pricing.html')

@app.route('/aircraft-recommendations')
@login_required
def aircraft_recommendations():
    """Aircraft recommendations page"""
    return render_template('aircraft_recommendations.html')

# Pro dashboard removed

@app.route('/create-listing')
@login_required
def create_listing():
    """Create listing page (login required)."""
    return render_template('create_listing.html')

@app.route('/my-listings')
@login_required
def my_listings():
    """My listings page (login required)."""
    return render_template('my_listings.html')

@app.route('/api/listings/create', methods=['POST'])
def create_listing_api():
    """API endpoint to handle listing creation"""
    try:
        data = request.get_json()
        listing_type = data.get('listing_type', 'aircraft')
        # Enforce performance profile for aircraft listings
        if listing_type == 'aircraft':
            profile = data.get('performance_profile')
            if not profile:
                # Try to auto-generate from provided fields
                # try:
                #     profile = generate_performance_profile(data)
                # except ValueError as e:
                #     return jsonify({'success': False, 'error': f'Missing performance profile: {e}'}), 400
                pass  # Skip auto-generation for now
            # Optionally: Save profile to DB or attach to listing here
        # ... existing code ...
        listing_id = f"{listing_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return jsonify({
            'success': True,
            'message': f'{listing_type.title()} listing created successfully!',
            'listing_id': listing_id,
            'status': 'pending_review'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('error.html', error_code=404, message="Page not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors"""
    return render_template('error.html', error_code=500, message="Internal server error"), 500

@app.route('/api/market-insights')
def api_market_insights():
    """Get market insights and trends"""
    try:
        # Analyze market data for insights
        insights = {
            'total_aircraft': len(AIRCRAFT_DATA),
            'categories': {},
            'price_ranges': {},
            'top_performers': {},
            'market_trends': []
        }
        
        # Category breakdown
        for aircraft in AIRCRAFT_DATA:
            category = categorize_aircraft(aircraft)
            insights['categories'][category] = insights['categories'].get(category, 0) + 1
        
        # Price range analysis
        price_ranges = {
            'Under $5M': 0,
            '$5M - $15M': 0,
            '$15M - $30M': 0,
            '$30M - $50M': 0,
            'Over $50M': 0
        }
        
        for aircraft in AIRCRAFT_DATA:
            price = aircraft.get('price', 0)
            if price < 5000000:
                price_ranges['Under $5M'] += 1
            elif price < 15000000:
                price_ranges['$5M - $15M'] += 1
            elif price < 30000000:
                price_ranges['$15M - $30M'] += 1
            elif price < 50000000:
                price_ranges['$30M - $50M'] += 1
            else:
                price_ranges['Over $50M'] += 1
        
        insights['price_ranges'] = price_ranges
        
        # Top performers by category
        best_value = max(AIRCRAFT_DATA, key=lambda x: x.get('best_all_around_dollar', 0))
        best_speed = max(AIRCRAFT_DATA, key=lambda x: x.get('speed', 0))
        best_range = max(AIRCRAFT_DATA, key=lambda x: x.get('range', 0))
        
        insights['top_performers'] = {
            'best_value': {
                'name': best_value.get('aircraft_name', 'Unknown'),
                'score': best_value.get('best_all_around_dollar', 0)
            },
            'fastest': {
                'name': best_speed.get('aircraft_name', 'Unknown'),
                'speed': best_speed.get('speed', 0)
            },
            'longest_range': {
                'name': best_range.get('aircraft_name', 'Unknown'),
                'range': best_range.get('range', 0)
            }
        }
        
        # Market trends
        insights['market_trends'] = [
            "Light jets dominate the market with highest volume",
            "Turboprops offer best value for short-range missions",
            "Heavy jets provide premium long-range capabilities",
            "Operating costs vary significantly by aircraft category"
        ]
        
        return jsonify(insights)
        
    except Exception as e:
        print(f"Error in market insights API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-recommendations')
def api_ai_recommendations():
    """Get AI-powered aircraft recommendations"""
    try:
        mission = request.args.get('mission', 'general')
        budget = request.args.get('budget', type=int)
        range_req = request.args.get('range', type=int)
        passengers = request.args.get('passengers', type=int)
        
        # Filter aircraft based on requirements
        suitable_aircraft = []
        
        for aircraft in AIRCRAFT_DATA:
            # Apply filters
            if budget and aircraft.get('price', 0) > budget:
                continue
            if range_req and aircraft.get('range', 0) < range_req:
                continue
            if passengers and aircraft.get('passengers', 0) < passengers:
                continue
            
            # Calculate AI recommendation score
            ai_score = calculate_ai_recommendation_score(aircraft, mission, budget, range_req, passengers)
            
            suitable_aircraft.append({
                'aircraft': aircraft,
                'ai_score': ai_score,
                'match_reasons': generate_ai_match_reasons(aircraft, mission, ai_score)
            })
        
        # Sort by AI score
        suitable_aircraft.sort(key=lambda x: x['ai_score'], reverse=True)
        
        return jsonify({
            'recommendations': suitable_aircraft[:10],  # Top 10 AI recommendations
            'mission_profile': mission,
            'filters_applied': {
                'budget': budget,
                'range': range_req,
                'passengers': passengers
            }
        })
        
    except Exception as e:
        print(f"Error in AI recommendations API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scenario-analysis', methods=['POST'])
def api_scenario_analysis():
    """Perform scenario analysis for aircraft selection"""
    try:
        data = request.get_json()
        scenarios = data.get('scenarios', [])
        
        results = []
        
        for scenario in scenarios:
            scenario_name = scenario.get('name', 'Unnamed Scenario')
            user_inputs = scenario.get('inputs', {})
            priorities = scenario.get('priorities', {})
            
            # Calculate scores for this scenario
            scenario_results = []
            
            for aircraft in AIRCRAFT_DATA:
                # Calculate comprehensive score for this scenario
                spreadsheet_score = calculate_spreadsheet_score(aircraft, user_inputs)
                priority_score = calculate_priority_score(aircraft, priorities)
                mission_fit = calculate_mission_fit_score(aircraft, user_inputs, {})
                
                # Weighted combined score
                combined_score = (spreadsheet_score * 0.4) + (priority_score * 0.3) + (mission_fit * 0.3)
                
                scenario_results.append({
                    'aircraft': aircraft,
                    'scenario_score': combined_score,
                    'component_scores': {
                        'spreadsheet': spreadsheet_score,
                        'priorities': priority_score,
                        'mission_fit': mission_fit
                    }
                })
            
            # Sort by scenario score
            scenario_results.sort(key=lambda x: x['scenario_score'], reverse=True)
            
            results.append({
                'scenario_name': scenario_name,
                'top_recommendations': scenario_results[:5],  # Top 5 for each scenario
                'scenario_summary': generate_scenario_summary(scenario_results[:5])
            })
        
        return jsonify({
            'scenario_analysis': results,
            'comparison_methodology': {
                'spreadsheet_weight': 0.4,
                'priorities_weight': 0.3,
                'mission_fit_weight': 0.3
            }
        })
        
    except Exception as e:
        print(f"Error in scenario analysis API: {e}")
        return jsonify({'error': str(e)}), 500

def calculate_ai_recommendation_score(aircraft, mission, budget, range_req, passengers):
    """Calculate AI recommendation score based on mission requirements"""
    try:
        score = 0
        
        # Base score from spreadsheet metrics
        score += aircraft.get('best_all_around_dollar', 0) * 10
        
        # Mission-specific scoring
        if mission == 'business':
            score += aircraft.get('speed', 0) / 10
            score += aircraft.get('range', 0) / 100
        elif mission == 'personal':
            score += aircraft.get('passengers', 0) * 5
            score += (100 - aircraft.get('total_hourly_cost', 1000) / 10)
        elif mission == 'charter':
            score += aircraft.get('passengers', 0) * 3
            score += aircraft.get('hourly_charter_rate', 0) / 100
        
        # Budget fit
        aircraft_price = aircraft.get('price', 0)
        if aircraft_price <= budget:
            score += 20
        elif aircraft_price <= budget * 1.2:
            score += 10
        
        # Range requirement
        aircraft_range = aircraft.get('range', 0)
        if aircraft_range >= range_req:
            score += 15
        elif aircraft_range >= range_req * 0.8:
            score += 8
        
        # Passenger requirement
        aircraft_passengers = aircraft.get('passengers', 0)
        if aircraft_passengers >= passengers:
            score += 10
        elif aircraft_passengers >= passengers * 0.8:
            score += 5
        
        # Efficiency bonus
        if aircraft.get('best_all_around_dollar', 0) > 5:
            score += 15
        
        return min(score, 100)  # Cap at 100
        
    except Exception as e:
        print(f"Error calculating AI recommendation score: {e}")
        return 0

def calculate_combined_score(aircraft, priorities, user_inputs, spreadsheet_weight=0.7, priority_weight=0.3):
    """
    Calculate combined score from spreadsheet metrics and user priorities
    
    Args:
        aircraft: Aircraft data dictionary
        priorities: User priority weightings (dict)
        user_inputs: User requirements (dict)
        spreadsheet_weight: Weight for spreadsheet-based score (default 0.7)
        priority_weight: Weight for priority-based score (default 0.3)
    
    Returns:
        float: Combined score (0-100)
    """
    try:
        # Calculate spreadsheet score (0-100)
        spreadsheet_score = calculate_spreadsheet_score(aircraft, user_inputs)
        
        # Calculate priority score (0-100)
        priority_score = calculate_priority_score(aircraft, priorities)
        
        # Combine scores with weights
        combined_score = (spreadsheet_score * spreadsheet_weight) + (priority_score * priority_weight)
        
        return min(combined_score, 100)  # Cap at 100
        
    except Exception as e:
        print(f"Error calculating combined score: {e}")
        return 0

def generate_ai_match_reasons(aircraft, mission, score):
    """Generate AI match reasons"""
    reasons = []
    
    if score >= 80:
        reasons.append(f"Excellent match for {mission} missions")
    elif score >= 60:
        reasons.append(f"Good fit for {mission} requirements")
    
    # Add specific strengths
    if aircraft.get('best_all_around_dollar', 0) > 5:
        reasons.append("Outstanding value proposition")
    if aircraft.get('speed', 0) > 500:
        reasons.append("High-speed capability")
    if aircraft.get('range', 0) > 3000:
        reasons.append("Long-range capability")
    
    return reasons

def generate_scenario_summary(top_aircraft):
    """Generate summary for scenario analysis"""
    if not top_aircraft:
        return "No suitable aircraft found for this scenario"
    
    winner = top_aircraft[0]
    summary = f"Top recommendation: {winner['aircraft'].get('aircraft_name', 'Unknown')} "
    summary += f"(Score: {winner['scenario_score']:.1f}). "
    
    # Add key strengths
    strengths = []
    if winner['component_scores']['spreadsheet'] >= 70:
        strengths.append("excellent performance metrics")
    if winner['component_scores']['priorities'] >= 70:
        strengths.append("strong priority alignment")
    if winner['component_scores']['mission_fit'] >= 70:
        strengths.append("perfect mission fit")
    
    if strengths:
        summary += f"Key strengths: {', '.join(strengths)}."
    
    return summary

# ===== NEW SCORING MODEL INTEGRATION =====

def calculate_priority_score_new(listing, aircraft_type_listings):
    """
    Calculate Priority Score based on engine hours, interior quality, avionics rank, 
    maintenance recency, and paint condition compared to other listings of the same type.
    
    Returns a score 0-100 where 100 is the best listing of this aircraft type.
    """
    try:
        # Component scores (0-100 each)
        engine_score = calculate_engine_hours_score(listing, aircraft_type_listings)
        interior_score = calculate_interior_quality_score(listing, aircraft_type_listings)
        avionics_score = calculate_avionics_rank_score(listing, aircraft_type_listings)
        maintenance_score = calculate_maintenance_recency_score(listing, aircraft_type_listings)
        paint_score = calculate_paint_condition_score(listing, aircraft_type_listings)
        
        # Weighted combination based on what typically drives resale value
        # These weights can be adjusted per aircraft model in the future
        weights = get_resale_value_weights(listing.get('model', ''))
        
        priority_score = (
            engine_score * weights['engine'] +
            interior_score * weights['interior'] +
            avionics_score * weights['avionics'] +
            maintenance_score * weights['maintenance'] +
            paint_score * weights['paint']
        )
        
        # Normalize against best in category
        if aircraft_type_listings:
            category_scores = []
            for other_listing in aircraft_type_listings:
                if other_listing['id'] != listing['id']:
                    other_score = (
                        calculate_engine_hours_score(other_listing, aircraft_type_listings) * weights['engine'] +
                        calculate_interior_quality_score(other_listing, aircraft_type_listings) * weights['interior'] +
                        calculate_avionics_rank_score(other_listing, aircraft_type_listings) * weights['avionics'] +
                        calculate_maintenance_recency_score(other_listing, aircraft_type_listings) * weights['maintenance'] +
                        calculate_paint_condition_score(other_listing, aircraft_type_listings) * weights['paint']
                    )
                    category_scores.append(other_score)
            
            if category_scores:
                max_score = max(category_scores + [priority_score])
                if max_score > 0:
                    priority_score = (priority_score / max_score) * 100
        
        return max(0, min(100, priority_score))
        
    except Exception as e:
        print(f"Error calculating priority score: {e}")
        return 0

def calculate_engine_hours_score(listing, aircraft_type_listings):
    """Calculate engine hours score based on remaining hours vs TBO"""
    try:
        # Get engine hours and TBO information
        engine_1_hours = listing.get('engine_1_time_since_new', 0) or 0
        engine_1_tbo = get_engine_tbo(listing.get('engine_1_model', ''))
        
        if engine_1_tbo <= 0:
            return 50  # Default score if TBO unknown
        
        # Calculate remaining hours
        remaining_hours = max(0, engine_1_tbo - engine_1_hours)
        remaining_percentage = (remaining_hours / engine_1_tbo) * 100
        
        # Cross-compare with other listings of same type
        if aircraft_type_listings:
            remaining_percentages = []
            for other in aircraft_type_listings:
                other_hours = other.get('engine_1_time_since_new', 0) or 0
                other_tbo = get_engine_tbo(other.get('engine_1_model', ''))
                if other_tbo > 0:
                    other_remaining = max(0, other_tbo - other_hours)
                    other_percentage = (other_remaining / other_tbo) * 100
                    remaining_percentages.append(other_percentage)
            
            if remaining_percentages:
                # Calculate percentile rank
                remaining_percentages.append(remaining_percentage)
                remaining_percentages.sort()
                rank = remaining_percentages.index(remaining_percentage)
                percentile = (rank / (len(remaining_percentages) - 1)) * 100
                return percentile
        
        # If no comparisons available, use absolute scale
        return remaining_percentage
        
    except Exception as e:
        print(f"Error calculating engine hours score: {e}")
        return 50

def calculate_interior_quality_score(listing, aircraft_type_listings):
    """Calculate interior quality score based on condition rating"""
    try:
        interior_condition = listing.get('interior_condition', '').lower()
        
        # Convert text ratings to numeric scores
        condition_scores = {
            'excellent': 100,
            'very good': 80,
            'good': 60,
            'fair': 40,
            'poor': 20,
            '': 0  # No rating provided
        }
        
        base_score = condition_scores.get(interior_condition, 0)
        
        # Cross-compare with other listings
        if aircraft_type_listings:
            all_scores = []
            for other in aircraft_type_listings:
                other_condition = other.get('interior_condition', '').lower()
                other_score = condition_scores.get(other_condition, 0)
                all_scores.append(other_score)
            
            if all_scores:
                # Calculate relative score
                all_scores.append(base_score)
                all_scores.sort()
                rank = all_scores.index(base_score)
                percentile = (rank / (len(all_scores) - 1)) * 100 if len(all_scores) > 1 else base_score
                return percentile
        
        return base_score
        
    except Exception as e:
        print(f"Error calculating interior quality score: {e}")
        return 50

def calculate_avionics_rank_score(listing, aircraft_type_listings):
    """Calculate avionics rank score based on avionics sophistication"""
    try:
        avionics_description = (listing.get('avionics_description', '') or '').lower()
        
        # Rank avionics systems (higher is better)
        avionics_rankings = {
            'g5000': 100,
            'g3000': 95,
            'pro line fusion': 90,
            'symmetry flight deck': 85,
            'easy iii': 80,
            'ace avionics': 75,
            'pro line 21': 70,
            'g1000': 65,
            'perspective': 60,
            'avidyne r9': 55,
            'collins proline': 50,
            'honeywell': 45,
            'garmin': 40,
            'bendix king': 35,
            'basic': 20,
            '': 0  # No avionics info
        }
        
        # Find best match in description
        base_score = 0
        for avionics_type, score in avionics_rankings.items():
            if avionics_type and avionics_type in avionics_description:
                base_score = max(base_score, score)
        
        # Cross-compare with other listings
        if aircraft_type_listings:
            all_scores = []
            for other in aircraft_type_listings:
                other_avionics = (other.get('avionics_description', '') or '').lower()
                other_score = 0
                for avionics_type, score in avionics_rankings.items():
                    if avionics_type and avionics_type in other_avionics:
                        other_score = max(other_score, score)
                all_scores.append(other_score)
            
            if all_scores:
                all_scores.append(base_score)
                all_scores.sort()
                rank = all_scores.index(base_score)
                percentile = (rank / (len(all_scores) - 1)) * 100 if len(all_scores) > 1 else base_score
                return percentile
        
        return base_score
        
    except Exception as e:
        print(f"Error calculating avionics rank score: {e}")
        return 50

def calculate_maintenance_recency_score(listing, aircraft_type_listings):
    """Calculate maintenance recency score based on inspection dates"""
    try:
        from datetime import datetime, timedelta
        
        last_annual = listing.get('last_annual_date')
        if not last_annual:
            return 0  # No maintenance info
        
        # Calculate days since last annual
        try:
            if isinstance(last_annual, str):
                annual_date = datetime.strptime(last_annual, '%Y-%m-%d')
            else:
                annual_date = last_annual
            
            days_since = (datetime.now() - annual_date).days
            
            # Fresh inspection (< 90 days) gets high score
            if days_since < 90:
                base_score = 100
            elif days_since < 180:
                base_score = 80
            elif days_since < 365:
                base_score = 60
            elif days_since < 500:
                base_score = 40
            else:
                base_score = 20  # Overdue
            
        except Exception:
            return 0
        
        # Cross-compare with other listings
        if aircraft_type_listings:
            all_scores = []
            for other in aircraft_type_listings:
                other_annual = other.get('last_annual_date')
                if other_annual:
                    try:
                        if isinstance(other_annual, str):
                            other_date = datetime.strptime(other_annual, '%Y-%m-%d')
                        else:
                            other_date = other_annual
                        other_days = (datetime.now() - other_date).days
                        
                        if other_days < 90:
                            other_score = 100
                        elif other_days < 180:
                            other_score = 80
                        elif other_days < 365:
                            other_score = 60
                        elif other_days < 500:
                            other_score = 40
                        else:
                            other_score = 20
                        
                        all_scores.append(other_score)
                    except Exception:
                        all_scores.append(0)
            
            if all_scores:
                all_scores.append(base_score)
                all_scores.sort()
                rank = all_scores.index(base_score)
                percentile = (rank / (len(all_scores) - 1)) * 100 if len(all_scores) > 1 else base_score
                return percentile
        
        return base_score
        
    except Exception as e:
        print(f"Error calculating maintenance recency score: {e}")
        return 50

def calculate_paint_condition_score(listing, aircraft_type_listings):
    """Calculate paint condition score"""
    try:
        exterior_condition = listing.get('exterior_condition', '').lower()
        
        # Convert text ratings to numeric scores
        condition_scores = {
            'excellent': 100,
            'very good': 80,
            'good': 60,
            'fair': 40,
            'poor': 20,
            '': 0  # No rating provided
        }
        
        base_score = condition_scores.get(exterior_condition, 0)
        
        # Cross-compare with other listings
        if aircraft_type_listings:
            all_scores = []
            for other in aircraft_type_listings:
                other_condition = other.get('exterior_condition', '').lower()
                other_score = condition_scores.get(other_condition, 0)
                all_scores.append(other_score)
            
            if all_scores:
                all_scores.append(base_score)
                all_scores.sort()
                rank = all_scores.index(base_score)
                percentile = (rank / (len(all_scores) - 1)) * 100 if len(all_scores) > 1 else base_score
                return percentile
        
        return base_score
        
    except Exception as e:
        print(f"Error calculating paint condition score: {e}")
        return 50

def get_resale_value_weights(aircraft_model):
    """Get resale value weights for different aircraft models"""
    # Default weights - can be customized per model
    default_weights = {
        'engine': 0.30,      # Engine hours most important
        'interior': 0.25,    # Interior quality
        'avionics': 0.20,    # Avionics sophistication
        'maintenance': 0.15, # Maintenance recency
        'paint': 0.10        # Paint condition
    }
    
    # Model-specific weights (could be stored in database)
    model_weights = {
        'citation x': {
            'engine': 0.35,
            'interior': 0.20,
            'avionics': 0.25,
            'maintenance': 0.15,
            'paint': 0.05
        },
        'gulfstream g550': {
            'engine': 0.25,
            'interior': 0.30,
            'avionics': 0.25,
            'maintenance': 0.15,
            'paint': 0.05
        }
    }
    
    return model_weights.get(aircraft_model.lower(), default_weights)

def get_engine_tbo(engine_model):
    """Get Time Between Overhaul for different engine models"""
    # Engine TBO database (hours)
    engine_tbos = {
        'pt6a-42': 3500,
        'pt6a-67': 3500,
        'pw306c': 5000,
        'pw307a': 5000,
        'cf34-3a': 6000,
        'br710-c4-11': 6000,
        'tfe731-2': 3000,
        'tfe731-3': 3500,
        'tfe731-40': 4000,
        'tfe731-60': 4000,
        'jt15d-4': 3000,
        'jt15d-5': 3500,
        'ae3007c': 6000,
        'cf700-2d2': 3000,
        'htf7000': 4000,
        'htf7500e': 5000,
        'pw545c': 4000,
        'pw610f': 5000,
        'rolls royce pearl 15': 6000,
        'ge passport': 6000
    }
    
    return engine_tbos.get(engine_model.lower(), 4000)  # Default 4000 hours

def calculate_data_score(listing):
    """
    Calculate Data Score based on listing completeness and verification status.
    Returns 0-100 score based on % of fields completed and verification level.
    """
    try:
        # Required fields for aircraft listings
        required_fields = [
            'title', 'manufacturer', 'model', 'year', 'price', 'location',
            'description', 'airframe_total_time', 'engine_1_manufacturer',
            'engine_1_model', 'engine_1_time_since_new', 'engine_1_time_since_overhaul',
            'interior_condition', 'exterior_condition', 'last_annual_date'
        ]
        
        # Highly valued fields (bonus points)
        bonus_fields = [
            'serial_number', 'registration_number', 'avionics_description',
            'equipment_list', 'maintenance_program', 'damage_history',
            'images', 'specifications'
        ]
        
        # Calculate completeness
        completed_required = 0
        for field in required_fields:
            value = listing.get(field)
            if value and str(value).strip() and str(value).strip() != '0':
                completed_required += 1
        
        completeness_percentage = (completed_required / len(required_fields)) * 100
        
        # Calculate bonus points
        completed_bonus = 0
        for field in bonus_fields:
            value = listing.get(field)
            if value and str(value).strip():
                completed_bonus += 1
        
        bonus_percentage = (completed_bonus / len(bonus_fields)) * 20  # Max 20 bonus points
        
        # Verification score
        verification_score = 0
        verification_status = listing.get('verification_status', 'pending')
        
        if verification_status == 'verified':
            verification_score = 20
        elif verification_status == 'partial':
            verification_score = 10
        elif verification_status == 'pending':
            verification_score = 0
        
        # Penalties for missing critical fields
        penalties = 0
        if not listing.get('engine_1_time_since_new'):
            penalties += 10
        if not listing.get('interior_condition'):
            penalties += 5
        if not listing.get('images'):
            penalties += 10
        
        # Calculate final data score
        data_score = completeness_percentage + bonus_percentage + verification_score - penalties
        
        return max(0, min(100, data_score))
        
    except Exception as e:
        print(f"Error calculating data score: {e}")
        return 0

def calculate_match_score(listing, buyer_preferences):
    """
    Calculate Match Score based on how well the listing fits buyer preferences.
    Uses cross-comparison logic similar to Zillow's "great match" system.
    """
    try:
        if not buyer_preferences:
            return 50  # Default score if no preferences
        
        # Individual match components
        hours_match = calculate_hours_match(listing, buyer_preferences)
        engine_match = calculate_engine_hours_match(listing, buyer_preferences)
        avionics_match = calculate_avionics_match(listing, buyer_preferences)
        interior_match = calculate_interior_match(listing, buyer_preferences)
        maintenance_match = calculate_maintenance_match(listing, buyer_preferences)
        paint_match = calculate_paint_match(listing, buyer_preferences)
        
        # Weighted combination based on buyer priorities
        weights = {
            'hours': buyer_preferences.get('engine_hours_weight', 0.2),
            'engine': buyer_preferences.get('engine_hours_weight', 0.2),
            'avionics': buyer_preferences.get('avionics_weight', 0.2),
            'interior': buyer_preferences.get('interior_weight', 0.2),
            'maintenance': buyer_preferences.get('maintenance_weight', 0.2),
            'paint': buyer_preferences.get('paint_weight', 0.2)
        }
        
        # Normalize weights to sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            for key in weights:
                weights[key] /= total_weight
        
        match_score = (
            hours_match * weights['hours'] +
            engine_match * weights['engine'] +
            avionics_match * weights['avionics'] +
            interior_match * weights['interior'] +
            maintenance_match * weights['maintenance'] +
            paint_match * weights['paint']
        )
        
        return max(0, min(100, match_score))
        
    except Exception as e:
        print(f"Error calculating match score: {e}")
        return 50

def calculate_hours_match(listing, buyer_preferences):
    """Calculate match score for total airframe hours"""
    try:
        max_hours = buyer_preferences.get('max_total_hours', 0)
        if not max_hours:
            return 100  # No preference specified
        
        listing_hours = listing.get('airframe_total_time', 0) or 0
        
        if listing_hours <= max_hours:
            # Perfect match or better
            excess_ratio = listing_hours / max_hours if max_hours > 0 else 0
            return max(80, 100 - (excess_ratio * 20))  # Scale from 100 to 80
        else:
            # Over preference
            over_ratio = (listing_hours - max_hours) / max_hours if max_hours > 0 else 1
            return max(0, 80 - (over_ratio * 80))  # Scale from 80 to 0
        
    except Exception as e:
        return 50

def calculate_engine_hours_match(listing, buyer_preferences):
    """Calculate match score for engine hours remaining"""
    try:
        min_remaining = buyer_preferences.get('min_engine_hours_remaining', 0)
        if not min_remaining:
            return 100  # No preference specified
        
        engine_hours = listing.get('engine_1_time_since_new', 0) or 0
        engine_tbo = get_engine_tbo(listing.get('engine_1_model', ''))
        remaining_hours = max(0, engine_tbo - engine_hours)
        
        if remaining_hours >= min_remaining:
            # Perfect match or better
            return 100
        else:
            # Below preference
            ratio = remaining_hours / min_remaining if min_remaining > 0 else 0
            return max(0, ratio * 100)
        
    except Exception as e:
        return 50

def calculate_avionics_match(listing, buyer_preferences):
    """Calculate match score for avionics preference"""
    try:
        preferred_avionics = buyer_preferences.get('preferred_avionics', '').lower()
        if not preferred_avionics:
            return 100  # No preference specified
        
        listing_avionics = (listing.get('avionics_description', '') or '').lower()
        
        if preferred_avionics in listing_avionics:
            return 100  # Perfect match
        
        # Partial matches for avionics families
        avionics_families = {
            'garmin': ['g5000', 'g3000', 'g1000', 'perspective'],
            'collins': ['pro line fusion', 'pro line 21'],
            'honeywell': ['symmetry', 'easy iii', 'ace']
        }
        
        for family, variants in avionics_families.items():
            if preferred_avionics in variants:
                for variant in variants:
                    if variant in listing_avionics:
                        return 80  # Family match
        
        return 20  # No match
        
    except Exception as e:
        return 50

def calculate_interior_match(listing, buyer_preferences):
    """Calculate match score for interior rating"""
    try:
        min_rating = buyer_preferences.get('min_interior_rating', 0)
        if not min_rating:
            return 100  # No preference specified
        
        interior_condition = listing.get('interior_condition', '').lower()
        
        rating_values = {
            'excellent': 5,
            'very good': 4,
            'good': 3,
            'fair': 2,
            'poor': 1,
            '': 0
        }
        
        listing_rating = rating_values.get(interior_condition, 0)
        
        if listing_rating >= min_rating:
            return 100
        elif listing_rating > 0:
            return (listing_rating / min_rating) * 100
        else:
            return 0
        
    except Exception as e:
        return 50

def calculate_maintenance_match(listing, buyer_preferences):
    """Calculate match score for maintenance recency"""
    try:
        max_age_months = buyer_preferences.get('max_maintenance_age_months', 0)
        if not max_age_months:
            return 100  # No preference specified
        
        from datetime import datetime
        last_annual = listing.get('last_annual_date')
        if not last_annual:
            return 0  # No maintenance data
        
        try:
            if isinstance(last_annual, str):
                annual_date = datetime.strptime(last_annual, '%Y-%m-%d')
            else:
                annual_date = last_annual
            
            months_since = ((datetime.now() - annual_date).days / 30.44)  # Average days per month
            
            if months_since <= max_age_months:
                return 100
            else:
                return max(0, 100 - ((months_since - max_age_months) / max_age_months * 100))
        
        except Exception:
            return 0
        
    except Exception as e:
        return 50

def calculate_paint_match(listing, buyer_preferences):
    """Calculate match score for paint condition"""
    try:
        min_rating = buyer_preferences.get('min_paint_rating', 0)
        if not min_rating:
            return 100  # No preference specified
        
        exterior_condition = listing.get('exterior_condition', '').lower()
        
        rating_values = {
            'excellent': 5,
            'very good': 4,
            'good': 3,
            'fair': 2,
            'poor': 1,
            '': 0
        }
        
        listing_rating = rating_values.get(exterior_condition, 0)
        
        if listing_rating >= min_rating:
            return 100
        elif listing_rating > 0:
            return (listing_rating / min_rating) * 100
        else:
            return 0
        
    except Exception as e:
        return 50

@app.route('/api/aircraft-scoring', methods=['POST'])
def api_aircraft_scoring():
    """
    New aircraft scoring system API endpoint
    Implements the exact scoring methodology as described:
    1. Calculate spreadsheet score (average of speed/$, range/$, performance/$, efficiency/$, all-around/$)
    2. Calculate priority score (weighted user preferences as percentages)
    3. Average spreadsheet and priority scores
    4. Average that with all-around/$ score for final recommendation
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        priorities = data.get('priorities', {})
        user_inputs = data.get('user_inputs', {})
        
        # Calculate scores for all aircraft
        scored_aircraft = []
        
        for aircraft in AIRCRAFT_DATA:
            # Step 1: Get all-around/$ score as percentage
            all_around_dollar = aircraft.get('best_all_around_dollar', 0)
            # INVERTED: Now the highest all-around dollar value gets the lowest percentage
            all_around_percentage = max(0, min(100, 100 - (all_around_dollar * 10))) if all_around_dollar > 0 else 100
            
            # Step 2: Calculate priority score (weighted user preferences)
            priority_score = 0
            if priorities:
                weighted_scores = []
                total_weight = 0
                
                for metric_key, weight in priorities.items():
                    if weight <= 0:
                        continue
                    
                    aircraft_value = aircraft.get(metric_key, 0)
                    if aircraft_value is None:
                        continue
                    
                    # Normalize to percentage
                    if metric_key == 'price':
                        normalized = max(0, 100 - (aircraft_value / 100000000 * 100))
                    elif metric_key == 'range':
                        normalized = min(100, (aircraft_value / 8000) * 100)
                    elif metric_key == 'speed':
                        normalized = min(100, (aircraft_value / 800) * 100)
                    elif metric_key == 'passengers':
                        normalized = min(100, (aircraft_value / 20) * 100)
                    elif metric_key in ['total_hourly_cost', 'hourly_variable_cost']:
                        normalized = max(0, 100 - (aircraft_value / 15000 * 100))
                    elif metric_key == 'runway_length':
                        normalized = max(0, 100 - (aircraft_value / 8000 * 100))
                    else:
                        normalized = min(100, aircraft_value) if aircraft_value > 0 else 0
                    
                    weighted_scores.append(normalized * weight)
                    total_weight += weight
                
                priority_score = sum(weighted_scores) / total_weight if total_weight > 0 else 50
            else:
                priority_score = 50  # Default if no priorities
            
            # Step 3: Final score = (All-Around/$ + Priority Score) ÷ 2
            final_recommendation_score = (all_around_percentage + priority_score) / 2
            
            scored_aircraft.append({
                'aircraft': aircraft,
                'final_recommendation_score': final_recommendation_score,
                'all_around_percentage': all_around_percentage,
                'priority_score': priority_score,
                'scoring_details': {
                    'all_around_per_dollar': aircraft.get('best_all_around_dollar', 0),
                    'priority_breakdown': {
                        metric: {
                            'value': aircraft.get(metric, 0),
                            'weight': weight,
                            'normalized_score': 0  # Would calculate this properly in production
                        } for metric, weight in priorities.items()
                    }
                }
            })
        
        # Sort by final recommendation score (highest first)
        scored_aircraft.sort(key=lambda x: x['final_recommendation_score'], reverse=True)
        
        return jsonify({
            'aircraft_rankings': scored_aircraft[:50],  # Top 50 recommendations
            'scoring_methodology': {
                'step_1': 'Get all-around/$ score as percentage',
                'step_2': 'Calculate priority score (weighted user preferences as percentages)', 
                'step_3': 'Average all-around/$ score and priority score for final recommendation',
                'formula': '(all_around_% + priority_score) / 2'
            },
            'total_aircraft_evaluated': len(AIRCRAFT_DATA),
            'filters_applied': user_inputs
        })
        
    except Exception as e:
        print(f"Error in aircraft scoring API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/scoring-demo')
def scoring_demo():
    """Aircraft scoring system demonstration page"""
    return render_template('aircraft_scoring_demo.html')

@app.route('/api/scoring-methodology')
def api_scoring_methodology():
    """Get information about the scoring methodology for frontend display"""
    try:
        return jsonify({
            'methodology': {
                'title': 'Aircraft Recommendation Scoring System',
                'description': 'Combines objective performance metrics with personalized priorities',
                'steps': [
                    {
                        'step': 1,
                        'title': 'All-Around/$ Score',
                        'description': 'Objective performance per dollar metric from spreadsheet',
                        'components': [
                            'All-Around per Dollar (converted to percentage)'
                        ]
                    },
                    {
                        'step': 2,
                        'title': 'Priority Score',
                        'description': 'Weighted user preferences as percentages',
                        'components': [
                            'Price (lower is better)',
                            'Range (higher is better)',
                            'Speed (higher is better)',
                            'Passengers (higher is better)',
                            'Operating Costs (lower is better)'
                        ]
                    },
                    {
                        'step': 3,
                        'title': 'Final Recommendation',
                        'description': 'Average of all-around/$ score and priority score',
                        'formula': '(all_around_% + priority_score) / 2'
                    }
                ]
            },
            'score_ranges': {
                'excellent': {'min': 80, 'max': 100, 'description': 'Outstanding value and performance'},
                'very_good': {'min': 60, 'max': 79, 'description': 'Strong performance and good value'},
                'good': {'min': 40, 'max': 59, 'description': 'Solid performance, reasonable value'},
                'fair': {'min': 20, 'max': 39, 'description': 'Basic performance, limited value'},
                'poor': {'min': 0, 'max': 19, 'description': 'Below average performance and value'}
            },
            'supported_priorities': [
                {'key': 'price', 'name': 'Purchase Price', 'unit': 'USD', 'direction': 'lower_better'},
                {'key': 'range', 'name': 'Range', 'unit': 'NM', 'direction': 'higher_better'},
                {'key': 'speed', 'name': 'Cruise Speed', 'unit': 'KTS', 'direction': 'higher_better'},
                {'key': 'passengers', 'name': 'Passenger Capacity', 'unit': 'seats', 'direction': 'higher_better'},
                {'key': 'total_hourly_cost', 'name': 'Operating Cost', 'unit': 'USD/hr', 'direction': 'lower_better'},
                {'key': 'runway_length', 'name': 'Runway Requirement', 'unit': 'ft', 'direction': 'lower_better'}
            ]
        })
        
    except Exception as e:
        print(f"Error in scoring methodology API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-scoring', methods=['GET'])
def api_test_scoring():
    """Test endpoint to verify the scoring system is working with sample data"""
    try:
        # Sample user priorities for testing
        test_priorities = {
            'price': 0.30,
            'range': 0.25, 
            'speed': 0.20,
            'passengers': 0.15,
            'total_hourly_cost': 0.10
        }
        
        # Get first 5 aircraft for testing
        test_aircraft = AIRCRAFT_DATA[:5]
        results = []
        
        for aircraft in test_aircraft:
            # Calculate scores using the new simplified methodology
            # Step 1: All-around/$ score as percentage
            all_around_dollar = aircraft.get('best_all_around_dollar', 0)
            # INVERTED: Now the highest all-around dollar value gets the lowest percentage
            all_around_percentage = max(0, min(100, 100 - (all_around_dollar * 10))) if all_around_dollar > 0 else 100
            all_around_percentage = max(0, min(100, all_around_percentage))
            
            # Step 2: Priority score
            weighted_scores = []
            total_weight = 0
            
            for metric_key, weight in test_priorities.items():
                aircraft_value = aircraft.get(metric_key, 0)
                if aircraft_value is None:
                    continue
                
                if metric_key == 'price':
                    normalized = max(0, 100 - (aircraft_value / 100000000 * 100))
                elif metric_key == 'range':
                    normalized = min(100, (aircraft_value / 8000) * 100)
                elif metric_key == 'speed':
                    normalized = min(100, (aircraft_value / 800) * 100)
                elif metric_key == 'passengers':
                    normalized = min(100, (aircraft_value / 20) * 100)
                elif metric_key == 'total_hourly_cost':
                    normalized = max(0, 100 - (aircraft_value / 15000 * 100))
                else:
                    normalized = min(100, aircraft_value) if aircraft_value > 0 else 0
                
                weighted_scores.append(normalized * weight)
                total_weight += weight
            
            priority_score = sum(weighted_scores) / total_weight if total_weight > 0 else 50
            priority_score = max(0, min(100, priority_score))
            
            # Step 3: Final score = (All-Around/$ + Priority Score) ÷ 2
            final_score = (all_around_percentage + priority_score) / 2
            final_score = max(0, min(100, final_score))
            
            results.append({
                'aircraft_name': aircraft.get('aircraft_name', 'Unknown'),
                'all_around_percentage': round(all_around_percentage, 2),
                'priority_score': round(priority_score, 2),
                'final_recommendation_score': round(final_score, 2),
                'value_rating': 'Excellent' if final_score <= 20 else 
                              'Very Good' if final_score <= 40 else
                              'Good' if final_score <= 60 else
                              'Fair' if final_score <= 80 else 'Poor'
            })
        
        return jsonify({
            'status': 'success',
            'methodology': 'final_score = (all_around_% + priority_score) / 2',
            'test_priorities': test_priorities,
            'sample_results': results,
            'total_aircraft_available': len(AIRCRAFT_DATA)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# ===== AVINODE CHARTER INTEGRATION ENDPOINTS =====

@app.route('/api/charter/search', methods=['POST'])
def api_charter_search():
    """Search for available charter aircraft using Avinode integration"""
    try:
        if not avinode_client:
            return jsonify({'error': 'Avinode integration not available'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No search parameters provided'}), 400
        
        # Extract search parameters
        departure_airport = data.get('departure_airport', '').strip().upper()
        arrival_airport = data.get('arrival_airport', '').strip().upper()
        departure_date = data.get('departure_date')
        passengers = int(data.get('passengers', 1))
        budget_range = data.get('budget_range')
        
        # Validate required parameters
        if not departure_airport or not arrival_airport or not departure_date:
            return jsonify({'error': 'Missing required parameters: departure_airport, arrival_airport, departure_date'}), 400
        
        # Search for charter aircraft
        charter_aircraft = avinode_client.search_charter_aircraft(
            departure_airport=departure_airport,
            arrival_airport=arrival_airport,
            departure_date=departure_date,
            passengers=passengers,
            budget_range=budget_range
        )
        
        return jsonify({
            'success': True,
            'aircraft': charter_aircraft,
            'search_params': {
                'departure_airport': departure_airport,
                'arrival_airport': arrival_airport,
                'departure_date': departure_date,
                'passengers': passengers,
                'budget_range': budget_range
            },
            'total_results': len(charter_aircraft)
        })
        
    except Exception as e:
        logger.error(f"Error in charter search: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/charter/aircraft/<aircraft_id>', methods=['GET'])
def api_charter_aircraft_details(aircraft_id):
    """Get detailed information about a specific charter aircraft"""
    try:
        if not avinode_client:
            return jsonify({'error': 'Avinode integration not available'}), 503
        
        aircraft_details = avinode_client.get_aircraft_details(aircraft_id)
        
        if not aircraft_details:
            return jsonify({'error': 'Aircraft not found'}), 404
        
        return jsonify({
            'success': True,
            'aircraft': aircraft_details
        })
        
    except Exception as e:
        logger.error(f"Error getting aircraft details: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/charter/quote', methods=['POST'])
def api_create_charter_quote():
    """Create a charter quote/booking request"""
    try:
        if not avinode_client:
            return jsonify({'error': 'Avinode integration not available'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No quote data provided'}), 400
        
        # Extract quote parameters
        aircraft_id = data.get('aircraft_id')
        departure_airport = data.get('departure_airport', '').strip().upper()
        arrival_airport = data.get('arrival_airport', '').strip().upper()
        departure_date = data.get('departure_date')
        passengers = int(data.get('passengers', 1))
        customer_info = data.get('customer_info', {})
        
        # Validate required parameters
        if not all([aircraft_id, departure_airport, arrival_airport, departure_date]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Create charter quote
        quote = avinode_client.create_charter_quote(
            aircraft_id=aircraft_id,
            departure_airport=departure_airport,
            arrival_airport=arrival_airport,
            departure_date=departure_date,
            passengers=passengers,
            customer_info=customer_info
        )
        
        if not quote:
            return jsonify({'error': 'Failed to create quote'}), 500
        
        return jsonify({
            'success': True,
            'quote': quote
        })
        
    except Exception as e:
        logger.error(f"Error creating charter quote: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/charter/quote/<quote_id>/status', methods=['GET'])
def api_charter_quote_status(quote_id):
    """Get the status of a charter quote"""
    try:
        if not avinode_client:
            return jsonify({'error': 'Avinode integration not available'}), 503
        
        quote_status = avinode_client.get_quote_status(quote_id)
        
        if not quote_status:
            return jsonify({'error': 'Quote not found'}), 404
        
        return jsonify({
            'success': True,
            'quote_status': quote_status
        })
        
    except Exception as e:
        logger.error(f"Error getting quote status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/charter/airports', methods=['GET'])
def api_charter_airports():
    """Get list of airports available for charter operations"""
    try:
        # Common charter airports (in a real implementation, this would come from Avinode)
        charter_airports = [
            {'code': 'LAX', 'name': 'Los Angeles International Airport', 'city': 'Los Angeles', 'state': 'CA'},
            {'code': 'JFK', 'name': 'John F. Kennedy International Airport', 'city': 'New York', 'state': 'NY'},
            {'code': 'ORD', 'name': "O'Hare International Airport", 'city': 'Chicago', 'state': 'IL'},
            {'code': 'MIA', 'name': 'Miami International Airport', 'city': 'Miami', 'state': 'FL'},
            {'code': 'SFO', 'name': 'San Francisco International Airport', 'city': 'San Francisco', 'state': 'CA'},
            {'code': 'DFW', 'name': 'Dallas/Fort Worth International Airport', 'city': 'Dallas', 'state': 'TX'},
            {'code': 'ATL', 'name': 'Hartsfield-Jackson Atlanta International Airport', 'city': 'Atlanta', 'state': 'GA'},
            {'code': 'DEN', 'name': 'Denver International Airport', 'city': 'Denver', 'state': 'CO'},
            {'code': 'LAS', 'name': 'McCarran International Airport', 'city': 'Las Vegas', 'state': 'NV'},
            {'code': 'BOS', 'name': 'Boston Logan International Airport', 'city': 'Boston', 'state': 'MA'},
            {'code': 'SEA', 'name': 'Seattle-Tacoma International Airport', 'city': 'Seattle', 'state': 'WA'},
            {'code': 'PHX', 'name': 'Phoenix Sky Harbor International Airport', 'city': 'Phoenix', 'state': 'AZ'},
            {'code': 'IAH', 'name': 'George Bush Intercontinental Airport', 'city': 'Houston', 'state': 'TX'},
            {'code': 'MCO', 'name': 'Orlando International Airport', 'city': 'Orlando', 'state': 'FL'},
            {'code': 'CLT', 'name': 'Charlotte Douglas International Airport', 'city': 'Charlotte', 'state': 'NC'},
            {'code': 'EWR', 'name': 'Newark Liberty International Airport', 'city': 'Newark', 'state': 'NJ'},
            {'code': 'DTW', 'name': 'Detroit Metropolitan Airport', 'city': 'Detroit', 'state': 'MI'},
            {'code': 'PHL', 'name': 'Philadelphia International Airport', 'city': 'Philadelphia', 'state': 'PA'},
            {'code': 'FLL', 'name': 'Fort Lauderdale-Hollywood International Airport', 'city': 'Fort Lauderdale', 'state': 'FL'},
            {'code': 'BWI', 'name': 'Baltimore/Washington International Airport', 'city': 'Baltimore', 'state': 'MD'}
        ]
        
        return jsonify({
            'success': True,
            'airports': charter_airports
        })
        
    except Exception as e:
        logger.error(f"Error getting charter airports: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/charter/calculate-price', methods=['POST'])
def api_charter_calculate_price():
    """Calculate estimated charter price for a route"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No route data provided'}), 400
        
        departure_airport = data.get('departure_airport', '').strip().upper()
        arrival_airport = data.get('arrival_airport', '').strip().upper()
        aircraft_type = data.get('aircraft_type', 'light_jet')
        
        if not departure_airport or not arrival_airport:
            return jsonify({'error': 'Missing departure or arrival airport'}), 400
        
        # Calculate distance (simplified)
        distance = avinode_client._calculate_distance(departure_airport, arrival_airport) if avinode_client else 1000
        
        # Estimate flight hours
        flight_hours = distance / 450.0  # Assume 450 knots average speed
        
        # Base hourly rates by aircraft type
        hourly_rates = {
            'turboprop': 2200,
            'light_jet': 3200,
            'midsize_jet': 4500,
            'super_midsize_jet': 5800,
            'heavy_jet': 8500,
            'ultra_long_range': 12000
        }
        
        hourly_rate = hourly_rates.get(aircraft_type, 3200)
        estimated_total = flight_hours * hourly_rate
        
        return jsonify({
            'success': True,
            'price_estimate': {
                'distance_nm': round(distance, 0),
                'flight_hours': round(flight_hours, 1),
                'hourly_rate': hourly_rate,
                'estimated_total': round(estimated_total, 0),
                'aircraft_type': aircraft_type
            }
        })
        
    except Exception as e:
        logger.error(f"Error calculating charter price: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/charter/recommend', methods=['POST'])
def api_charter_recommend():
    """Recommend suitable jet types and specific aircraft for a charter route.
    Inputs: departure_airport, arrival_airport, departure_date, passengers.
    Output: recommended aircraft list with estimated pricing and 10% commission plan.
    """
    try:
        data = request.get_json() or {}
        dep = (data.get('departure_airport') or '').strip().upper()
        arr = (data.get('arrival_airport') or '').strip().upper()
        passengers = int(data.get('passengers') or 1)
        if not dep or not arr:
            return jsonify({'success': False, 'error': 'departure_airport and arrival_airport are required'}), 400

        # Simple recommendation logic without external service
        def distance_fn(a, b):
            return avinode_client._calculate_distance(a, b) if avinode_client else 1000

        # Calculate distance for the route
        distance = distance_fn(dep, arr)
        
        # Filter aircraft that can make the trip
        suitable_aircraft = []
        for aircraft in AIRCRAFT_DATA:
            aircraft_range = aircraft.get('range', 0)
            aircraft_passengers = aircraft.get('passengers', 0)
            
            if aircraft_range >= distance and aircraft_passengers >= passengers:
                suitable_aircraft.append({
                    'aircraft': aircraft,
                    'category': categorize_aircraft(aircraft),
                    'hourly_rate': aircraft.get('charter_rate', 3500),
                    'estimated_total': distance * 2.5  # Simple estimate
                })
        
        recommendations = suitable_aircraft[:10]  # Top 10 recommendations
        meta = {'distance': distance, 'suitable_count': len(suitable_aircraft)}

        return jsonify({'success': True, 'recommendations': recommendations, 'requirements': {'passengers': passengers, **meta}})
    except Exception as e:
        logger.error(f"Error in charter recommend: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== SCORING MODEL API ENDPOINTS =====

@app.route('/api/scoring/calculate-all', methods=['POST'])
def api_calculate_all_scores():
    """Calculate Priority, Data, and Match scores for all aircraft listings"""
    try:
        # Group listings by aircraft type for cross-comparison
        aircraft_by_type = {}
        
        # For now, use CSV data to simulate marketplace listings
        for aircraft in AIRCRAFT_DATA:
            aircraft_type = f"{aircraft.get('manufacturer', '')} {aircraft.get('model', '')}".strip()
            if aircraft_type not in aircraft_by_type:
                aircraft_by_type[aircraft_type] = []
            aircraft_by_type[aircraft_type].append(aircraft)
        
        scored_aircraft = []
        
        for aircraft_type, type_listings in aircraft_by_type.items():
            for listing in type_listings:
                # Calculate Priority Score
                priority_score = calculate_priority_score_new(listing, type_listings)
                
                # Calculate Data Score
                data_score = calculate_data_score(listing)
                
                # Calculate average Match Score (without specific buyer preferences)
                match_score = 75  # Default good match score
                
                # Find best in category for relative positioning
                category_scores = []
                for other_listing in type_listings:
                    other_priority = calculate_priority_score_new(other_listing, type_listings)
                    category_scores.append(other_priority)
                
                best_in_category = max(category_scores) if category_scores else priority_score
                position = sorted(category_scores, reverse=True).index(priority_score) + 1
                
                scored_aircraft.append({
                    'aircraft': listing,
                    'aircraft_type': aircraft_type,
                    'scores': {
                        'priority_score': round(priority_score, 1),
                        'data_score': round(data_score, 1),
                        'match_score': round(match_score, 1)
                    },
                    'category_info': {
                        'best_in_category': round(best_in_category, 1),
                        'position': position,
                        'total_in_category': len(type_listings)
                    },
                    'score_breakdown': {
                        'priority_components': {
                            'engine_hours': calculate_engine_hours_score(listing, type_listings),
                            'interior_quality': calculate_interior_quality_score(listing, type_listings),
                            'avionics_rank': calculate_avionics_rank_score(listing, type_listings),
                            'maintenance_recency': calculate_maintenance_recency_score(listing, type_listings),
                            'paint_condition': calculate_paint_condition_score(listing, type_listings)
                        }
                    }
                })
        
        # Sort by priority score (highest first)
        scored_aircraft.sort(key=lambda x: x['scores']['priority_score'], reverse=True)
        
        return jsonify({
            'success': True,
            'total_aircraft': len(scored_aircraft),
            'aircraft_types': len(aircraft_by_type),
            'scored_aircraft': scored_aircraft[:50],  # Return top 50
            'scoring_summary': {
                'avg_priority_score': sum(a['scores']['priority_score'] for a in scored_aircraft) / len(scored_aircraft),
                'avg_data_score': sum(a['scores']['data_score'] for a in scored_aircraft) / len(scored_aircraft),
                'avg_match_score': sum(a['scores']['match_score'] for a in scored_aircraft) / len(scored_aircraft)
            }
        })
        
    except Exception as e:
        print(f"Error calculating all scores: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scoring/buyer-preferences', methods=['POST'])
def api_save_buyer_preferences():
    """Save buyer preferences for match scoring"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No preferences provided'}), 400
        
        user_id = session.get('user_id')
        session_id = session.get('session_id', 'anonymous')
        db_module.save_buyer_preferences(user_id, session_id, data)
        return jsonify({
            'success': True,
            'message': 'Buyer preferences saved successfully'
        })
        
    except Exception as e:
        print(f"Error saving buyer preferences: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scoring/match-scores', methods=['POST'])
def api_calculate_match_scores():
    """Calculate match scores for all aircraft based on buyer preferences"""
    try:
        user_id = session.get('user_id')
        session_id = session.get('session_id', 'anonymous')
        preferences = db_module.get_buyer_preferences(user_id, session_id)
        if not preferences:
            return jsonify({'error': 'No buyer preferences found. Please set preferences first.'}), 400
        # Calculate match scores for all aircraft
        aircraft_with_match_scores = []
        
        for aircraft in AIRCRAFT_DATA:
            match_score = calculate_match_score(aircraft, preferences)
            
            # Calculate individual component scores for transparency
            hours_match = calculate_hours_match(aircraft, preferences)
            engine_match = calculate_engine_hours_match(aircraft, preferences)
            avionics_match = calculate_avionics_match(aircraft, preferences)
            interior_match = calculate_interior_match(aircraft, preferences)
            maintenance_match = calculate_maintenance_match(aircraft, preferences)
            paint_match = calculate_paint_match(aircraft, preferences)
            
            aircraft_with_match_scores.append({
                'aircraft': aircraft,
                'match_score': round(match_score, 1),
                'match_components': {
                    'hours_match': round(hours_match, 1),
                    'engine_match': round(engine_match, 1),
                    'avionics_match': round(avionics_match, 1),
                    'interior_match': round(interior_match, 1),
                    'maintenance_match': round(maintenance_match, 1),
                    'paint_match': round(paint_match, 1)
                },
                'match_label': get_match_label(match_score)
            })
        
        # Sort by match score (highest first)
        aircraft_with_match_scores.sort(key=lambda x: x['match_score'], reverse=True)
        return jsonify({
            'success': True,
            'buyer_preferences': preferences,
            'aircraft_matches': aircraft_with_match_scores[:50],  # Top 50 matches
            'total_aircraft': len(aircraft_with_match_scores)
        })
        
    except Exception as e:
        print(f"Error calculating match scores: {e}")
        return jsonify({'error': str(e)}), 500

def get_match_label(score):
    """Convert match score to descriptive label"""
    if score >= 95:
        return "Perfect Match"
    elif score >= 85:
        return "Excellent Match"
    elif score >= 75:
        return "Very Good Match"
    elif score >= 65:
        return "Good Match"
    elif score >= 50:
        return "Fair Match"
    else:
        return "Poor Match"

@app.route('/api/scoring/aircraft/<int:aircraft_id>')
def api_get_aircraft_scores(aircraft_id):
    """Get detailed scoring information for a specific aircraft"""
    try:
        # Find the aircraft
        aircraft = None
        for a in AIRCRAFT_DATA:
            if a.get('id') == aircraft_id:
                aircraft = a
                break
        
        if not aircraft:
            return jsonify({'error': 'Aircraft not found'}), 404
        
        # Find other aircraft of the same type for comparison
        aircraft_type = f"{aircraft.get('manufacturer', '')} {aircraft.get('model', '')}".strip()
        type_listings = [a for a in AIRCRAFT_DATA if f"{a.get('manufacturer', '')} {a.get('model', '')}".strip() == aircraft_type]
        
        # Calculate scores
        priority_score = calculate_priority_score_new(aircraft, type_listings)
        data_score = calculate_data_score(aircraft)
        
        # Get buyer preferences for match score
        user_id = session.get('user_id')
        session_id = session.get('session_id', 'anonymous')
        preferences = db_module.get_buyer_preferences(user_id, session_id)
        match_score = calculate_match_score(aircraft, preferences) if preferences else 50
        
        # Calculate category position
        category_scores = []
        for other_aircraft in type_listings:
            other_priority = calculate_priority_score_new(other_aircraft, type_listings)
            category_scores.append(other_priority)
        
        category_scores.sort(reverse=True)
        position = category_scores.index(priority_score) + 1
        best_in_category = category_scores[0] if category_scores else priority_score
        return jsonify({
            'success': True,
            'aircraft': aircraft,
            'scores': {
                'priority_score': round(priority_score, 1),
                'data_score': round(data_score, 1),
                'match_score': round(match_score, 1)
            },
            'category_comparison': {
                'aircraft_type': aircraft_type,
                'position': position,
                'total_in_category': len(type_listings),
                'best_in_category': round(best_in_category, 1),
                'percentile': round((1 - (position - 1) / len(type_listings)) * 100, 1) if len(type_listings) > 1 else 100
            },
            'detailed_breakdown': {
                'priority_components': {
                    'engine_hours_score': round(calculate_engine_hours_score(aircraft, type_listings), 1),
                    'interior_quality_score': round(calculate_interior_quality_score(aircraft, type_listings), 1),
                    'avionics_rank_score': round(calculate_avionics_rank_score(aircraft, type_listings), 1),
                    'maintenance_recency_score': round(calculate_maintenance_recency_score(aircraft, type_listings), 1),
                    'paint_condition_score': round(calculate_paint_condition_score(aircraft, type_listings), 1),
                    'weights': get_resale_value_weights(aircraft.get('model', ''))
                },
                'data_components': {
                    'completeness_bonus': 'Calculated based on required fields filled',
                    'verification_bonus': aircraft.get('verification_status', 'pending'),
                    'critical_field_penalties': 'Applied for missing engine hours, interior rating, or photos'
                },
                'match_components': {
                    'hours_match': round(calculate_hours_match(aircraft, preferences), 1) if preferences else 'N/A',
                    'engine_match': round(calculate_engine_hours_match(aircraft, preferences), 1) if preferences else 'N/A',
                    'avionics_match': round(calculate_avionics_match(aircraft, preferences), 1) if preferences else 'N/A',
                    'interior_match': round(calculate_interior_match(aircraft, preferences), 1) if preferences else 'N/A',
                    'maintenance_match': round(calculate_maintenance_match(aircraft, preferences), 1) if preferences else 'N/A',
                    'paint_match': round(calculate_paint_match(aircraft, preferences), 1) if preferences else 'N/A'
                } if preferences else 'No buyer preferences set'
            }
        })
    except Exception as e:
        print(f"Error getting aircraft scores: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/scoring-system')
def scoring_system_demo():
    """Demo page for the new scoring system"""
    return render_template('scoring_system_demo.html')

@app.route('/api/scoring/demo-data', methods=['POST'])
def api_demo_scoring_data():
    """Create demo data to showcase the scoring system with realistic values"""
    try:
        # Create some sample marketplace listings with detailed information
        demo_listings = [
            {
                'id': 'demo_1',
                'manufacturer': 'Gulfstream',
                'model': 'G550',
                'aircraft_name': 'G550',
                'year': 2018,
                'price': 25000000,
                'airframe_total_time': 1200,
                'engine_1_manufacturer': 'Rolls-Royce',
                'engine_1_model': 'BR710-C4-11',
                'engine_1_time_since_new': 1100,
                'engine_1_time_since_overhaul': 0,
                'interior_condition': 'excellent',
                'exterior_condition': 'very good',
                'avionics_description': 'G5000 flight deck with PlaneView cockpit',
                'last_annual_date': '2024-01-15',
                'verification_status': 'verified',
                'images': 'uploaded',
                'maintenance_program': 'manufacturer warranty',
                'specifications': 'complete'
            },
            {
                'id': 'demo_2',
                'manufacturer': 'Gulfstream',
                'model': 'G550',
                'aircraft_name': 'G550',
                'year': 2015,
                'price': 22000000,
                'airframe_total_time': 2800,
                'engine_1_manufacturer': 'Rolls-Royce',
                'engine_1_model': 'BR710-C4-11',
                'engine_1_time_since_new': 2650,
                'engine_1_time_since_overhaul': 800,
                'interior_condition': 'good',
                'exterior_condition': 'fair',
                'avionics_description': 'G3000 avionics suite',
                'last_annual_date': '2023-08-10',
                'verification_status': 'partial',
                'images': None,
                'maintenance_program': None,
                'specifications': None
            },
            {
                'id': 'demo_3',
                'manufacturer': 'Gulfstream',
                'model': 'G550',
                'aircraft_name': 'G550',
                'year': 2020,
                'price': 28000000,
                'airframe_total_time': 450,
                'engine_1_manufacturer': 'Rolls-Royce',
                'engine_1_model': 'BR710-C4-11',
                'engine_1_time_since_new': 420,
                'engine_1_time_since_overhaul': 0,
                'interior_condition': 'excellent',
                'exterior_condition': 'excellent',
                'avionics_description': 'G5000 with latest software updates',
                'last_annual_date': '2024-02-20',
                'verification_status': 'verified',
                'images': 'uploaded',
                'maintenance_program': 'manufacturer warranty',
                'specifications': 'complete',
                'serial_number': 'available',
                'registration_number': 'available'
            }
        ]
        
        # Calculate scores for demo listings
        scored_demos = []
        demo_preferences = {
            'max_total_hours': 2000,
            'min_engine_hours_remaining': 2000,
            'preferred_avionics': 'g5000',
            'min_interior_rating': 4,
            'max_maintenance_age_months': 12,
            'min_paint_rating': 3
        }
        
        for listing in demo_listings:
            # Calculate Priority Score
            priority_score = calculate_priority_score_new(listing, demo_listings)
            
            # Calculate Data Score
            data_score = calculate_data_score(listing)
            
            # Calculate Match Score
            match_score = calculate_match_score(listing, demo_preferences)
            
            # Find position in category
            category_scores = []
            for other_listing in demo_listings:
                other_priority = calculate_priority_score_new(other_listing, demo_listings)
                category_scores.append(other_priority)
            
            category_scores.sort(reverse=True)
            position = category_scores.index(priority_score) + 1
            best_in_category = category_scores[0] if category_scores else priority_score
            
            scored_demos.append({
                'listing': listing,
                'scores': {
                    'priority_score': round(priority_score, 1),
                    'data_score': round(data_score, 1),
                    'match_score': round(match_score, 1)
                },
                'category_info': {
                    'aircraft_type': f"{listing['manufacturer']} {listing['model']}",
                    'position': position,
                    'total_in_category': len(demo_listings),
                    'best_in_category': round(best_in_category, 1),
                    'percentile': round((1 - (position - 1) / len(demo_listings)) * 100, 1)
                },
                'explanations': {
                    'priority_explanation': get_priority_explanation(listing, demo_listings),
                    'data_explanation': get_data_explanation(listing),
                    'match_explanation': get_match_explanation(listing, demo_preferences)
                }
            })
        
        # Sort by priority score
        scored_demos.sort(key=lambda x: x['scores']['priority_score'], reverse=True)
        
        return jsonify({
            'success': True,
            'demo_listings': scored_demos,
            'demo_preferences': demo_preferences,
            'scoring_methodology': {
                'priority_score': 'Compares engine hours, interior quality, avionics, maintenance, and paint against other G550s',
                'data_score': 'Based on listing completeness, verification status, and required field completion',
                'match_score': 'How well each aircraft fits your specific preferences and requirements'
            }
        })
        
    except Exception as e:
        print(f"Error creating demo data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_priority_explanation(listing, type_listings):
    """Generate explanation for priority score"""
    explanations = []
    
    # Engine hours
    engine_hours = listing.get('engine_1_time_since_new', 0)
    engine_tbo = get_engine_tbo(listing.get('engine_1_model', ''))
    remaining = max(0, engine_tbo - engine_hours)
    explanations.append(f"Engine: {remaining:,} hours remaining until TBO")
    
    # Interior condition
    interior = listing.get('interior_condition', 'unknown')
    explanations.append(f"Interior: {interior.title()} condition")
    
    # Avionics
    avionics = listing.get('avionics_description', 'basic')
    if 'g5000' in avionics.lower():
        explanations.append("Avionics: Top-tier G5000 flight deck")
    elif 'g3000' in avionics.lower():
        explanations.append("Avionics: Advanced G3000 suite")
    else:
        explanations.append("Avionics: Standard equipment")
    
    return "; ".join(explanations)

def get_data_explanation(listing):
    """Generate explanation for data score"""
    completeness = 0
    required_fields = ['manufacturer', 'model', 'year', 'price', 'airframe_total_time']
    
    for field in required_fields:
        if listing.get(field):
            completeness += 20
    
    verification = listing.get('verification_status', 'pending')
    if verification == 'verified':
        verification_bonus = 20
    elif verification == 'partial':
        verification_bonus = 10
    else:
        verification_bonus = 0
    
    return f"{completeness}% field completion + {verification_bonus} verification bonus"

def get_match_explanation(listing, preferences):
    """Generate explanation for match score"""
    explanations = []
    
    # Hours check
    max_hours = preferences.get('max_total_hours', 0)
    listing_hours = listing.get('airframe_total_time', 0)
    if max_hours and listing_hours <= max_hours:
        explanations.append(f"✓ {listing_hours:,} hours within {max_hours:,} preference")
    elif max_hours:
        explanations.append(f"✗ {listing_hours:,} hours exceeds {max_hours:,} preference")
    
    # Avionics check
    preferred = preferences.get('preferred_avionics', '').lower()
    listing_avionics = listing.get('avionics_description', '').lower()
    if preferred and preferred in listing_avionics:
        explanations.append(f"✓ Has preferred {preferred.upper()} avionics")
    elif preferred:
        explanations.append(f"✗ Does not have preferred {preferred.upper()} avionics")
    
    return "; ".join(explanations) if explanations else "No specific preferences to match"

# New API endpoints for performance profiles and user listings
@app.route('/api/performance-profiles')
def api_performance_profiles():
    """API endpoint to get all performance profiles (formerly aircraft data)"""
    try:
        aircraft_data = get_unified_aircraft_data()
        
        # Transform aircraft data into performance profiles
        profiles = []
        for aircraft in aircraft_data:
            profile = {
                'id': aircraft.get('id'),
                'name': aircraft.get('aircraft_name', 'Unknown Aircraft'),
                'manufacturer': aircraft.get('manufacturer', 'Unknown'),
                'category': aircraft.get('category', 'Unknown'),
                'range': aircraft.get('range', 0),
                'speed': aircraft.get('speed', 0),
                'passengers': aircraft.get('passengers', 0),
                'max_altitude': aircraft.get('max_altitude', 0),
                'cabin_volume': aircraft.get('cabin_volume', 0),
                'baggage_volume': aircraft.get('baggage_volume', 0),
                'engine_type': aircraft.get('engine_type') or aircraft.get('category'),
                'runway_length': aircraft.get('runway_length', 0),
                'fuel_capacity': aircraft.get('fuel_capacity', 0),
                'empty_weight': aircraft.get('empty_weight', 0),
                'max_weight': aircraft.get('max_weight', 0),
                'image': aircraft.get('image', '/static/images/aircraft_placeholder.jpg'),
                # Performance metrics for reference
                'best_speed_dollar': aircraft.get('best_speed_dollar', 0),
                'best_range_dollar': aircraft.get('best_range_dollar', 0),
                'best_performance_dollar': aircraft.get('best_performance_dollar', 0),
                'best_efficiency_dollar': aircraft.get('best_efficiency_dollar', 0),
                'best_all_around_dollar': aircraft.get('best_all_around_dollar', 0)
            }
            profiles.append(profile)
        
        return jsonify(profiles)
    except Exception as e:
        print(f"Error loading performance profiles: {e}")
        return jsonify([]), 500

def _row_to_combined_listing(row, aircraft_map):
    """Build combined listing dict from db row and profile map."""
    listing_id = row['id']
    profile_id = row['profile_id']
    title = row.get('title') or ''
    year = row.get('year')
    price = row.get('price')
    hours = row.get('hours', 0)
    location = row.get('location') or ''
    email = row.get('email') or ''
    description = row.get('description') or ''
    images = row.get('images') or ''
    documents = row.get('documents') or ''
    status = row.get('status') or 'active'
    payment_status = row.get('payment_status') or 'pending'
    engine_type = row.get('engine_type')
    listing_manufacturer = row.get('manufacturer')
    pricing_plan = row.get('pricing_plan') or 'monthly'
    created_at = row.get('created_at')
    updated_at = row.get('updated_at')
    profile = aircraft_map.get(profile_id)
    if not profile:
        return None
    profile_copy = dict(profile)
    image_list = [img.strip() for img in (images or '').split(',') if img.strip()]
    document_list = [doc.strip() for doc in (documents or '').split(',') if doc.strip()]
    resolved_manufacturer = listing_manufacturer or profile_copy.get('manufacturer') or 'Unknown'
    resolved_engine_type = engine_type or profile_copy.get('engine_type') or profile_copy.get('category') or 'Unknown'
    listing_title = title or f"{resolved_manufacturer} {profile_copy.get('aircraft_name', profile_copy.get('name', 'Aircraft'))}".strip()
    hero_image = image_list[0] if image_list else profile_copy.get('image', '/static/images/aircraft_placeholder.jpg')
    return {
        **profile_copy,
        'id': listing_id,
        'listing_id': listing_id,
        'profile_id': profile_id,
        'title': listing_title,
        'listing_title': listing_title,
        'price': price,
        'listing_price': price,
        'hours': hours,
        'location': location,
        'contact_email': email,
        'email': email,
        'description': description,
        'listing_description': description,
        'engine_type': resolved_engine_type,
        'manufacturer': resolved_manufacturer,
        'pricing_plan': pricing_plan,
        'status': status,
        'payment_status': payment_status,
        'images': image_list,
        'documents': document_list,
        'image': hero_image,
        'year': year or profile_copy.get('year'),
        'created_at': created_at,
        'updated_at': updated_at,
        'is_user_listing': True,
    }


@app.route('/api/user-listings')
def api_user_listings():
    """API endpoint to get user-created listings (from Postgres/SQLite via db layer)."""
    try:
        rows = db_module.get_active_user_listings()
        aircraft_data = get_unified_aircraft_data()
        aircraft_map = {aircraft.get('id'): aircraft for aircraft in aircraft_data}
        listings = []
        for row in rows:
            combined = _row_to_combined_listing(row, aircraft_map)
            if combined:
                listings.append(combined)
        return jsonify(listings)
    except Exception as e:
        logger.exception("Error loading user listings")
        return jsonify([]), 500

@app.route('/api/user-listings', methods=['POST'])
def api_create_user_listing():
    """Create a new user listing (login required; saved to DB, goes live immediately)."""
    if not session.get('user_id'):
        return jsonify({'error': 'You must be logged in to create a listing. Please register or log in.'}), 401
    try:
        data = request.get_json()
        required_fields = ['profile_id', 'price', 'location', 'email', 'description', 'engine_type', 'manufacturer', 'pricing_plan']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        aircraft_data = get_unified_aircraft_data()
        profile = None
        for aircraft in aircraft_data:
            if aircraft.get('id') == data['profile_id']:
                profile = aircraft
                break
        if not profile:
            return jsonify({'error': 'Performance profile not found'}), 404
        
        images_str = ','.join(data.get('images', [])) if data.get('images') else ''
        documents_str = ','.join(data.get('documents', [])) if data.get('documents') else ''
        listing_title = data.get('title') or f"{data.get('manufacturer') or profile.get('manufacturer', '')} {profile.get('aircraft_name', profile.get('name', 'Aircraft'))}".strip()
        if not listing_title:
            listing_title = profile.get('aircraft_name', 'Aircraft Listing')
        year_value = profile.get('year') or datetime.now().year
        valid_pricing_plans = {'monthly', 'six_month'}
        pricing_plan = data.get('pricing_plan', 'monthly')
        if pricing_plan not in valid_pricing_plans:
            return jsonify({'error': 'Invalid pricing plan selected'}), 400

        user_id = session.get('user_id')
        listing_id = db_module.create_user_listing(
            data['profile_id'],
            listing_title,
            year_value,
            float(data['price']),
            data.get('hours', 0),
            data['location'],
            data['email'],
            data.get('description', ''),
            images_str,
            documents_str,
            data.get('engine_type', profile.get('category', 'Unknown')),
            data.get('manufacturer', profile.get('manufacturer', 'Unknown')),
            pricing_plan,
            user_id=user_id,
        )
        
        new_listing = {
            'id': listing_id,
            'profile_id': data['profile_id'],
            'title': listing_title,
            'year': year_value,
            'price': data['price'],
            'hours': data.get('hours', 0),
            'location': data['location'],
            'email': data['email'],
            'description': data.get('description', ''),
            'images': data.get('images', []),
            'documents': data.get('documents', []),
            'engine_type': data.get('engine_type', profile.get('category', 'Unknown')),
            'manufacturer': data.get('manufacturer', profile.get('manufacturer', 'Unknown')),
            'pricing_plan': pricing_plan,
            'status': 'pending',
            'payment_status': 'pending',
            'message': 'Listing submitted successfully! Payment required for approval. Admin will review after payment.',
            'name': profile.get('aircraft_name', 'Unknown Aircraft'),
            'category': profile.get('category', 'Unknown'),
            'range': profile.get('range', 0),
            'speed': profile.get('speed', 0),
            'passengers': profile.get('passengers', 0),
            'max_altitude': profile.get('max_altitude', 0),
            'cabin_volume': profile.get('cabin_volume', 0),
            'baggage_volume': profile.get('baggage_volume', 0),
            'image': profile.get('image', '/static/images/aircraft_placeholder.jpg')
        }
        return jsonify(new_listing), 201
    except Exception as e:
        logger.exception("Error creating user listing")
        return jsonify({'error': 'Failed to create listing'}), 500

@app.route('/api/my-listings')
def api_my_listings():
    """Return the current user's listings (login required)."""
    if not session.get('user_id'):
        return jsonify({'error': 'Not logged in'}), 401
    try:
        rows = db_module.get_listings_by_user_id(session['user_id'])
        aircraft_data = get_unified_aircraft_data()
        aircraft_map = {a.get('id'): a for a in aircraft_data}
        out = []
        for row in rows:
            combined = _row_to_combined_listing(row, aircraft_map)
            if combined:
                combined['status'] = row.get('status')
                combined['created_at'] = row.get('created_at')
                out.append(combined)
        return jsonify(out)
    except Exception as e:
        logger.exception("Error loading my listings")
        return jsonify([]), 500

@app.route('/api/user-listings/<int:listing_id>', methods=['GET'])
def api_get_user_listing(listing_id):
    """API endpoint to get a specific user listing (from db layer)."""
    try:
        row = db_module.get_user_listing_by_id(listing_id, active_only=True)
        if not row:
            return jsonify({'error': 'Listing not found'}), 404
        aircraft_data = get_unified_aircraft_data()
        profile = None
        for aircraft in aircraft_data:
            if aircraft.get('id') == row['profile_id']:
                profile = aircraft
                break
        if not profile:
            return jsonify({'error': 'Performance profile not found'}), 404
        images = row.get('images') or ''
        listing = {
            'id': row['id'],
            'profile_id': row['profile_id'],
            'title': row.get('title'),
            'year': row.get('year'),
            'price': row.get('price'),
            'hours': row.get('hours', 0),
            'location': row.get('location'),
            'email': row.get('email'),
            'description': row.get('description'),
            'images': [x.strip() for x in images.split(',') if x.strip()] if images else [],
            'status': row.get('status'),
            'created_at': row.get('created_at'),
            'updated_at': row.get('updated_at'),
            'name': profile.get('aircraft_name', 'Unknown Aircraft'),
            'manufacturer': profile.get('manufacturer', 'Unknown'),
            'category': profile.get('category', 'Unknown'),
            'range': profile.get('range', 0),
            'speed': profile.get('speed', 0),
            'passengers': profile.get('passengers', 0),
            'max_altitude': profile.get('max_altitude', 0),
            'cabin_volume': profile.get('cabin_volume', 0),
            'baggage_volume': profile.get('baggage_volume', 0),
            'image': profile.get('image', '/static/images/aircraft_placeholder.jpg')
        }
        return jsonify(listing)
    except Exception as e:
        logger.exception("Error getting user listing")
        return jsonify({'error': 'Failed to get listing'}), 500

@app.route('/api/user-listings/<int:listing_id>', methods=['DELETE'])
def api_delete_user_listing(listing_id):
    """API endpoint to delete a user listing (soft delete via db layer)."""
    try:
        ok = db_module.delete_user_listing_soft(listing_id)
        if not ok:
            return jsonify({'error': 'Listing not found'}), 404
        return jsonify({'message': 'Listing deleted successfully'}), 200
    except Exception as e:
        logger.exception("Error deleting user listing")
        return jsonify({'error': 'Failed to delete listing'}), 500

@app.route('/api/listings/search')
def api_search_listings():
    """API endpoint to search and filter user listings (db layer)."""
    try:
        search_query = request.args.get('q', '').lower()
        category = request.args.get('category', '')
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        min_year = request.args.get('min_year', type=int)
        max_year = request.args.get('max_year', type=int)
        location = request.args.get('location', '').lower()
        
        rows = db_module.search_user_listings(
            min_price=min_price, max_price=max_price,
            min_year=min_year, max_year=max_year,
        )
        aircraft_data = get_unified_aircraft_data()
        aircraft_map = {aircraft.get('id'): aircraft for aircraft in aircraft_data}
        listings = []
        for row in rows:
            if location and (row.get('location') or '').lower().find(location) < 0:
                continue
            if search_query:
                tit = (row.get('title') or '').lower()
                desc = (row.get('description') or '').lower()
                if search_query not in tit and search_query not in desc:
                    continue
            combined = _row_to_combined_listing(row, aircraft_map)
            if not combined:
                continue
            if category and (combined.get('category') or '').lower() != category.lower():
                continue
            listings.append({
                'id': combined['id'],
                'profile_id': combined['profile_id'],
                'title': combined.get('title'),
                'year': combined.get('year'),
                'price': combined.get('price'),
                'hours': combined.get('hours', 0),
                'location': combined.get('location'),
                'email': combined.get('email'),
                'description': combined.get('description'),
                'images': combined.get('images', []),
                'status': combined.get('status'),
                'created_at': combined.get('created_at'),
                'updated_at': combined.get('updated_at'),
                'name': combined.get('name', 'Unknown Aircraft'),
                'manufacturer': combined.get('manufacturer', 'Unknown'),
                'category': combined.get('category', 'Unknown'),
                'range': combined.get('range', 0),
                'speed': combined.get('speed', 0),
                'passengers': combined.get('passengers', 0),
                'max_altitude': combined.get('max_altitude', 0),
                'cabin_volume': combined.get('cabin_volume', 0),
                'baggage_volume': combined.get('baggage_volume', 0),
                'image': combined.get('image', '/static/images/aircraft_placeholder.jpg')
            })
        return jsonify({'listings': listings, 'total': len(listings)})
    except Exception as e:
        logger.exception("Error searching user listings")
        return jsonify({'error': 'Failed to search listings'}), 500

# Admin approval routes
@app.route('/admin/listings')
def admin_listings():
    """Admin page to approve/reject pending listings (from db layer)."""
    if not session.get('user_id'):
        flash('Please login to access admin panel', 'warning')
        return redirect(url_for('home'))
    rows = db_module.get_pending_user_listings()
    aircraft_data = get_unified_aircraft_data()
    aircraft_map = {aircraft.get('id'): aircraft for aircraft in aircraft_data}
    pending_listings = []
    for row in rows:
        profile = aircraft_map.get(row['profile_id'])
        if not profile:
            continue
        images = row.get('images') or ''
        documents = row.get('documents') or ''
        pending_listings.append({
            'id': row['id'],
            'profile_id': row['profile_id'],
            'title': row.get('title'),
            'year': row.get('year'),
            'price': row.get('price'),
            'hours': row.get('hours', 0),
            'location': row.get('location'),
            'email': row.get('email'),
            'description': row.get('description'),
            'images': [x.strip() for x in images.split(',') if x.strip()] if images else [],
            'documents': [x.strip() for x in documents.split(',') if x.strip()] if documents else [],
            'status': row.get('status'),
            'payment_status': row.get('payment_status'),
            'pricing_plan': row.get('pricing_plan') or 'monthly',
            'engine_type': row.get('engine_type') or profile.get('engine_type') or profile.get('category', 'Unknown'),
            'created_at': row.get('created_at'),
            'manufacturer': row.get('manufacturer') or profile.get('manufacturer', 'Unknown'),
            'model': profile.get('aircraft_name', 'Unknown'),
            'category': profile.get('category', 'Unknown')
        })
    return render_template('admin/listings.html', pending_listings=pending_listings)

@app.route('/api/admin/listings/<int:listing_id>/approve', methods=['POST'])
def admin_approve_listing(listing_id):
    """API endpoint to approve a pending listing (db layer)."""
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        raw_status, _ = db_module.get_user_listing_status(listing_id)
        status = cast("str | None", raw_status)
        if status is None:
            return jsonify({'error': 'Listing not found'}), 404
        if status != 'pending':
            return jsonify({'error': f'Listing is already {status}'}), 400
        ok = cast(bool, db_module.approve_user_listing(listing_id, session.get('user_id')))
        if not ok:
            return jsonify({'error': 'Listing not found or not pending'}), 404
        return jsonify({'message': 'Listing approved successfully', 'status': 'active'}), 200
    except Exception as e:
        logger.exception("Error approving listing")
        return jsonify({'error': 'Failed to approve listing'}), 500

@app.route('/api/admin/listings/<int:listing_id>/reject', methods=['POST'])
def admin_reject_listing(listing_id):
    """API endpoint to reject a pending listing (db layer)."""
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json() or {}
        rejection_reason = data.get('reason', 'No reason provided')
        raw_status, _ = db_module.get_user_listing_status(listing_id)
        status = cast("str | None", raw_status)
        if status is None:
            return jsonify({'error': 'Listing not found'}), 404
        if status != 'pending':
            return jsonify({'error': f'Listing is already {status}'}), 400
        ok = cast(bool, db_module.reject_user_listing(listing_id, rejection_reason))
        if not ok:
            return jsonify({'error': 'Listing not found or not pending'}), 404
        return jsonify({'message': 'Listing rejected successfully', 'status': 'rejected'}), 200
    except Exception as e:
        logger.exception("Error rejecting listing")
        return jsonify({'error': 'Failed to reject listing'}), 500

@app.route('/admin/populate-profiles')
def admin_populate_profiles():
    """Admin endpoint to populate performance profiles cache table (DB layer for Railway)."""
    try:
        aircraft_data = get_unified_aircraft_data()
        db_module.clear_performance_profiles()
        db_module.add_performance_profiles(aircraft_data)
        return jsonify({
            'message': f'Successfully populated {len(aircraft_data)} performance profiles',
            'total': len(aircraft_data)
        })
    except Exception as e:
        print(f"Error populating performance profiles: {e}")
        return jsonify({'error': 'Failed to populate profiles'}), 500

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, host="0.0.0.0", port=5015)

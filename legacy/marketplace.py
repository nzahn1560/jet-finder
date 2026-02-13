from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime
import uuid

# Create blueprint
marketplace = Blueprint('marketplace', __name__, url_prefix='/marketplace')

# Simulated database - in a real app, this would be in a database
USERS_DB_FILE = 'data/users.json'
LISTINGS_DB_FILE = 'data/listings.json'

# Helper function to load users


def load_users():
    if os.path.exists(USERS_DB_FILE):
        with open(USERS_DB_FILE, 'r') as f:
            return json.load(f)
    return []

# Helper function to save users


def save_users(users):
    os.makedirs(os.path.dirname(USERS_DB_FILE), exist_ok=True)
    with open(USERS_DB_FILE, 'w') as f:
        json.dump(users, f, indent=2)

# Helper function to load listings


def load_listings():
    if os.path.exists(LISTINGS_DB_FILE):
        with open(LISTINGS_DB_FILE, 'r') as f:
            return json.load(f)
    return []

# Helper function to save listings


def save_listings(listings):
    os.makedirs(os.path.dirname(LISTINGS_DB_FILE), exist_ok=True)
    with open(LISTINGS_DB_FILE, 'w') as f:
        json.dump(listings, f, indent=2)

# Helper to check if user is logged in


def is_logged_in():
    return 'user_id' in session

# Helper to get current user


def get_current_user():
    if 'user_id' not in session:
        return None

    users = load_users()
    for user in users:
        if user['id'] == session['user_id']:
            return user

    return None

# Helper for aircraft recommendation based on criteria


def recommend_aircraft(listings, criteria=None):
    """Recommend aircraft based on criteria"""
    if criteria is None:
        criteria = {
            'budget': 10000000,
            'min_range': 0,
            'min_speed': 0,
            'purpose': 'business',
            'pax': 4,
            'category': ''
        }

    # Convert criteria to appropriate types
    try:
        budget = float(criteria.get('budget', 10000000))
        min_range = int(criteria.get('min_range', 0))
        min_speed = int(criteria.get('min_speed', 0))
        purpose = criteria.get('purpose', 'business')
        pax = int(criteria.get('pax', 4))
    except (ValueError, TypeError):
        # Handle conversion errors by using defaults
        budget = 10000000
        min_range = 0
        min_speed = 0
        purpose = 'business'
        pax = 4

    # Prepare results list
    results = []

    # Special case handling if parameter is a single listing instead of a list
    if not isinstance(listings, list):
        listings = [listings]

    # Iterate over each listing to calculate match score
    for listing in listings:
        # Initialize score components
        score_components = {
            'budget': 0,
            'range': 0,
            'speed': 0,
            'purpose': 0,
            'pax': 0
        }

        # Helper function to safely get numeric values from listing
        def get_numeric(key, default=0):
            try:
                value = listing.get(key, default)
                return float(value) if value is not None else default
            except (ValueError, TypeError):
                return default

        # Get listing properties
        price = get_numeric('price', 0)
        range_nm = get_numeric('range', 0)
        max_speed = get_numeric('max_speed', 0)
        seats = get_numeric('seats', 0)

        # Skip listings that don't meet minimum requirements
        if listing.get('price', 0) > budget:
            continue
        if range_nm < min_range:
            continue
        if max_speed < min_speed:
            continue
        if seats < pax:
            continue

        # Calculate budget score (higher score for better value, max 25 points)
        budget_ratio = price / budget
        if budget_ratio <= 0.5:
            score_components['budget'] = 25
        elif budget_ratio <= 0.75:
            score_components['budget'] = 20
        elif budget_ratio <= 0.9:
            score_components['budget'] = 15
        else:
            score_components['budget'] = 10

        # Calculate range score (max 25 points)
        if range_nm >= 5000:
            score_components['range'] = 25
        elif range_nm >= 3000:
            score_components['range'] = 20
        elif range_nm >= 2000:
            score_components['range'] = 15
        elif range_nm >= 1000:
            score_components['range'] = 10
        else:
            score_components['range'] = 5

        # Calculate speed score (max 25 points)
        if max_speed >= 500:
            score_components['speed'] = 25
        elif max_speed >= 450:
            score_components['speed'] = 20
        elif max_speed >= 400:
            score_components['speed'] = 15
        elif max_speed >= 300:
            score_components['speed'] = 10
        else:
            score_components['speed'] = 5

        # Calculate purpose match (max 15 points)
        # This would ideally use more sophisticated matching logic
        if purpose == 'business':
            if listing.get('category', '').lower() in ['jet', 'turboprop']:
                score_components['purpose'] = 15
            else:
                score_components['purpose'] = 5
        else:  # leisure
            if listing.get('category', '').lower() in ['piston', 'turboprop']:
                score_components['purpose'] = 15
            else:
                score_components['purpose'] = 10

        # Calculate passenger capacity score (max 10 points)
        if seats >= pax + 4:
            score_components['pax'] = 10
        elif seats >= pax + 2:
            score_components['pax'] = 8
        elif seats >= pax:
            score_components['pax'] = 5
        else:
            score_components['pax'] = 0

        # Calculate total score as a percentage
        total_score = sum(score_components.values())
        percentage_score = (total_score / 100) * 100  # Scale to percentage out of max possible 100

        # Calculate additional metrics

        # Estimate annual operating costs based on category and size
        annual_fixed_cost = 0
        hourly_variable_cost = 0
        yearly_usage_hours = 150  # Assumed average usage

        if listing.get('category') == 'jet':
            if seats <= 6:  # Light jet
                annual_fixed_cost = 400000
                hourly_variable_cost = 1800
            elif seats <= 10:  # Midsize jet
                annual_fixed_cost = 700000
                hourly_variable_cost = 2500
            else:  # Large jet
                annual_fixed_cost = 1200000
                hourly_variable_cost = 3500
        elif listing.get('category') == 'turboprop':
            annual_fixed_cost = 250000
            hourly_variable_cost = 1200
        else:  # Piston
            annual_fixed_cost = 150000
            hourly_variable_cost = 600

        # Calculate multi-year total cost (5-year cost of ownership)
        acquisition_cost = price
        annual_operating_cost = annual_fixed_cost + (hourly_variable_cost * yearly_usage_hours)
        five_year_cost = acquisition_cost + (annual_operating_cost * 5)

        # Calculate value metrics
        efficiency_score = range_nm / max(1, price / 1000000)  # Range per million dollars
        performance_score = max_speed / max(1, price / 1000000)  # Speed per million dollars

        # All-around value score
        all_around_score = (efficiency_score * 0.4) + (performance_score * 0.4) + (percentage_score * 0.2)

        # Add this result to the list with all scores
        results.append({
            'listing': listing,
            'score': percentage_score,
            'score_components': score_components,
            'metrics': {
                'five_year_cost': five_year_cost,
                'efficiency': efficiency_score,
                'performance': performance_score,
                'all_around': all_around_score,
                'annual_operating_cost': annual_operating_cost,
                'hourly_cost': hourly_variable_cost
            }
        })

    # Sort results by overall score (highest first)
    results.sort(key=lambda x: x['score'], reverse=True)

    return results

# Routes


@marketplace.route('/')
@marketplace.route('/listings')
def listings():
    """Main marketplace listings page with filtering"""
    # Get filter criteria from query parameters with defaults
    criteria = {
        'budget': request.args.get('budget', '10000000'),
        'min_range': request.args.get('min_range', '0'),
        'min_speed': request.args.get('min_speed', '0'),
        'purpose': request.args.get('purpose', 'business'),
        'pax': request.args.get('pax', '4'),
        'category': request.args.get('category', ''),
        'trip_origin': request.args.get('trip_origin', ''),
        'trip_destination': request.args.get('trip_destination', ''),
        'home_airport': request.args.get('home_airport', ''),
        'max_distance': request.args.get('max_distance', '0')
    }

    # Get sort parameter
    sort_by = request.args.get('sort', 'match')

    # Check if this is a Jet Finder integration request
    from_jet_finder = request.args.get('from_jet_finder', False)
    selected_aircraft = request.args.get('aircraft', None)

    # Load all listings
    all_listings = load_listings()

    # Filter listings by category if specified
    filtered_listings = all_listings
    if criteria['category']:
        filtered_listings = [listing for listing in all_listings if listing['category'].lower() == criteria['category'].lower()]

    # Filter by trip distance if origin and destination are provided
    if criteria['trip_origin'] and criteria['trip_destination'] and criteria['trip_origin'] != criteria['trip_destination']:
        # In a real app, we would calculate the actual distance between airports
        # For now, we'll just use the min_range as a proxy for trip distance filtering
        pass

    # Filter by home airport range if specified
    if criteria['home_airport'] and criteria['max_distance'] and int(criteria['max_distance']) > 0:
        # In a real app, we would filter based on aircraft range vs. home airport
        # For now, we use min_range from the criteria
        pass

    # Generate aircraft recommendations by calling recommend_aircraft for the whole list
    recommendations = recommend_aircraft(filtered_listings, criteria)

    # Sort by appropriate criteria
    if sort_by == 'price_low':
        recommendations.sort(key=lambda x: x['listing']['price'])
    elif sort_by == 'price_high':
        recommendations.sort(key=lambda x: x['listing']['price'], reverse=True)
    elif sort_by == 'year_new':
        recommendations.sort(key=lambda x: x['listing']['year'], reverse=True)
    elif sort_by == 'year_old':
        recommendations.sort(key=lambda x: x['listing']['year'])
    elif sort_by == 'range_high':
        recommendations.sort(key=lambda x: x['listing']['range'], reverse=True)
    elif sort_by == 'speed_high':
        recommendations.sort(key=lambda x: x['listing']['max_speed'], reverse=True)
    elif sort_by == 'efficiency':
        # Sort by efficiency (range per dollar)
        recommendations.sort(key=lambda x: x['listing'].get('range', 0) /
                             max(x['listing'].get('price', 1), 1), reverse=True)
    elif sort_by == 'performance':
        # Sort by performance (speed per dollar)
        recommendations.sort(key=lambda x: x['listing'].get('max_speed', 0) /
                             max(x['listing'].get('price', 1), 1), reverse=True)
    else:
        # Default sort by match score
        recommendations.sort(key=lambda x: x['score'], reverse=True)

    # Get top recommendation
    top_recommendation = recommendations[0] if recommendations else None

    # Get current user
    current_user = get_current_user()

    # Get URL for Jet Finder page
    jet_finder_url = url_for('home')

    # Pass all the variables to the template
    return render_template('marketplace/listings.html',
                           listings=[r['listing'] for r in recommendations],
                           top_recommendation=top_recommendation,
                           recommendation_scores={r['listing']['id']: {
                               'score': r['score'],
                               'metrics': r['metrics']
                           } for r in recommendations},
                           criteria=criteria,
                           sort_by=sort_by,
                           current_user=current_user,
                           get_recommendation_reasons=get_recommendation_reasons,
                           from_jet_finder=from_jet_finder,
                           selected_aircraft=selected_aircraft,
                           jet_finder_url=jet_finder_url)


@marketplace.route('/listing/<string:listing_id>')
def listing_detail(listing_id):
    """Individual listing detail page"""
    listings = load_listings()

    # Find the listing by ID
    listing = next((item for item in listings if item['id'] == listing_id), None)

    if not listing:
        flash('Listing not found', 'danger')
        return redirect(url_for('marketplace.listings'))

    # Get similar listings (simplified for demo)
    similar_listings = [item for item in listings if item['id'] != listing_id
                        and item['category'] == listing['category']][:3]

    return render_template('marketplace/listing_detail.html',
                           listing=listing,
                           similar_listings=similar_listings,
                           current_user=get_current_user())


@marketplace.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')

        users = load_users()
        user = next((u for u in users if u['email'] == email), None)

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash('Login successful!', 'success')
            return redirect(url_for('marketplace.listings'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('marketplace/login.html', current_user=get_current_user())


@marketplace.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '')
        account_type = request.form.get('account_type', 'buyer')

        # Validate data
        if not all([first_name, last_name, email, password, confirm_password, account_type]):
            flash('All required fields must be filled', 'danger')
            return render_template('marketplace/register.html', current_user=get_current_user())

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('marketplace/register.html', current_user=get_current_user())

        # Check if user already exists
        users = load_users()
        if any(u['email'] == email for u in users):
            flash('Email already registered', 'danger')
            return render_template('marketplace/register.html', current_user=get_current_user())

        # Create new user
        new_user = {
            'id': str(uuid.uuid4()),
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password': generate_password_hash(password),
            'phone': phone,
            'account_type': account_type,
            'created_at': datetime.now().isoformat(),
            'favorites': []
        }

        users.append(new_user)
        save_users(users)

        # Log the user in
        session['user_id'] = new_user['id']
        flash('Registration successful!', 'success')
        return redirect(url_for('marketplace.listings'))

    return render_template('marketplace/register.html', current_user=get_current_user())


@marketplace.route('/logout')
def logout():
    """Logout user"""
    session.pop('user_id', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('marketplace.login'))


@marketplace.route('/dashboard')
def dashboard():
    """User dashboard"""
    if not is_logged_in():
        flash('Please login to access your dashboard', 'danger')
        return redirect(url_for('marketplace.login'))

    current_user = get_current_user()
    return render_template('marketplace/dashboard.html', current_user=current_user)


@marketplace.route('/my-listings')
def my_listings():
    """User's listings"""
    if not is_logged_in():
        flash('Please login to access your listings', 'danger')
        return redirect(url_for('marketplace.login'))

    current_user = get_current_user()
    if current_user is None:
        flash('User not found', 'danger')
        return redirect(url_for('marketplace.login'))

    listings = load_listings()

    # Get listings owned by current user
    user_listings = [listing for listing in listings if listing.get('seller_id') == current_user['id']]

    return render_template('marketplace/my_listings.html',
                           listings=user_listings,
                           current_user=current_user)


@marketplace.route('/saved-listings')
def saved_listings():
    """User's saved/favorite listings"""
    if not is_logged_in():
        flash('Please login to access your saved listings', 'danger')
        return redirect(url_for('marketplace.login'))

    current_user = get_current_user()
    if current_user is None:
        flash('User not found', 'danger')
        return redirect(url_for('marketplace.login'))

    listings = load_listings()

    # Get listings that are in the user's favorites
    favorite_listings = [listing for listing in listings if listing['id'] in current_user.get('favorites', [])]

    return render_template('marketplace/saved_listings.html',
                           listings=favorite_listings,
                           current_user=current_user)


@marketplace.route('/create-listing', methods=['GET', 'POST'])
def create_listing():
    """Create a new listing"""
    if not is_logged_in():
        flash('Please login to create a listing', 'danger')
        return redirect(url_for('marketplace.login'))

    current_user = get_current_user()
    if current_user is None:
        flash('User not found', 'danger')
        return redirect(url_for('marketplace.login'))

    # Check if user is a seller or both
    if current_user['account_type'] not in ['seller', 'both']:
        flash('You need a seller account to create listings', 'danger')
        return redirect(url_for('marketplace.dashboard'))

    if request.method == 'POST':
        # Get form data and create listing
        # This would be more complex in a real application
        title = request.form.get('title', '')
        category = request.form.get('category', '')
        description = request.form.get('description', '')
        price = request.form.get('price', '0')

        if not all([title, category, description, price]):
            flash('All required fields must be filled', 'danger')
            return render_template('marketplace/create_listing.html', current_user=current_user)

        new_listing = {
            'id': str(uuid.uuid4()),
            'title': title,
            'category': category,
            'description': description,
            'price': float(price),
            'seller_id': current_user['id'],
            'seller_name': f"{current_user['first_name']} {current_user['last_name']}",
            'created_at': datetime.now().isoformat(),
            'status': 'active'
        }

        listings = load_listings()
        listings.append(new_listing)
        save_listings(listings)

        flash('Listing created successfully!', 'success')
        return redirect(url_for('marketplace.my_listings'))

    return render_template('marketplace/create_listing.html', current_user=current_user)

# API endpoints for favorites


@marketplace.route('/api/favorites/add', methods=['POST'])
def add_favorite():
    """Add a listing to user's favorites"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    data = request.get_json()
    listing_id = data.get('listing_id')

    if not listing_id:
        return jsonify({'success': False, 'message': 'Listing ID is required'}), 400

    users = load_users()
    for i, user in enumerate(users):
        if user['id'] == session['user_id']:
            if 'favorites' not in user:
                user['favorites'] = []

            if listing_id not in user['favorites']:
                user['favorites'].append(listing_id)
                save_users(users)
                return jsonify({'success': True, 'message': 'Added to favorites'})
            else:
                return jsonify({'success': False, 'message': 'Already in favorites'})

    return jsonify({'success': False, 'message': 'User not found'}), 404


@marketplace.route('/api/favorites/remove', methods=['POST'])
def remove_favorite():
    """Remove a listing from user's favorites"""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    data = request.get_json()
    listing_id = data.get('listing_id')

    if not listing_id:
        return jsonify({'success': False, 'message': 'Listing ID is required'}), 400

    users = load_users()
    for i, user in enumerate(users):
        if user['id'] == session['user_id']:
            if 'favorites' in user and listing_id in user['favorites']:
                user['favorites'].remove(listing_id)
                save_users(users)
                return jsonify({'success': True, 'message': 'Removed from favorites'})
            else:
                return jsonify({'success': False, 'message': 'Not in favorites'})

    return jsonify({'success': False, 'message': 'User not found'}), 404

# API endpoint for recommendation


@marketplace.route('/api/recommend', methods=['POST'])
def recommend_api():
    """Get aircraft recommendations based on criteria"""
    data = request.get_json() or {}
    listings = load_listings()

    recommendations = recommend_aircraft(listings, data)

    # Format the response
    response = {
        'success': True,
        'recommendations': [
            {
                'listing': item['listing'],
                'score': item['score'],
                'reasons': get_recommendation_reasons(item['listing'], item['score'], data)
            } for item in recommendations[:5]  # Just return top 5
        ]
    }

    return jsonify(response)


def get_recommendation_reasons(listing, score, criteria):
    """Generate human-readable reasons for recommendations"""
    reasons = []

    # Value reason
    if listing.get('price', 0) <= float(criteria.get('budget', 10000000)) * 0.7:
        reasons.append(f"Great value at {int(listing.get('price', 0)/1000000)}M - well under your budget")

    # Range reason
    if listing.get('range', 0) >= float(criteria.get('min_range', 0)) * 1.2:
        reasons.append(f"Excellent range of {listing.get('range', 0)} NM exceeds your requirements")

    # Speed reason
    if listing.get('max_speed', 0) >= float(criteria.get('min_speed', 0)) * 1.1:
        reasons.append(f"High-performance speed of {listing.get('max_speed', 0)} KTAS")

    # Add aircraft-specific reasons
    if 'Citation X' in listing.get('title', ''):
        reasons.append("The Citation X is one of the fastest civilian jets available")
    elif 'Phenom 300' in listing.get('title', ''):
        reasons.append("The Phenom 300 offers excellent efficiency and comfort")
    elif 'G500' in listing.get('title', ''):
        reasons.append("Gulfstream's renowned comfort and capabilities")

    # If few reasons, add a generic one
    if len(reasons) < 2:
        reasons.append(f"This aircraft matches {int(score)}% of your requirements")

    return reasons

# Initialize sample data


def init_sample_data():
    """Initialize sample data if none exists"""
    # Create sample users if none exist
    if not os.path.exists(USERS_DB_FILE) or os.path.getsize(USERS_DB_FILE) == 0:
        sample_users = [
            {
                'id': str(uuid.uuid4()),
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'password': generate_password_hash('password'),
                'phone': '555-123-4567',
                'account_type': 'both',
                'created_at': datetime.now().isoformat(),
                'favorites': []
            }
        ]
        save_users(sample_users)

    # Create sample listings if none exist
    if not os.path.exists(LISTINGS_DB_FILE) or os.path.getsize(LISTINGS_DB_FILE) == 0:
        users = load_users()
        seller_id = users[0]['id'] if users else str(uuid.uuid4())

        sample_listings = [{'id': str(uuid.uuid4()),
                            'title': '2015 Cessna Citation X+',
                            'category': 'jet',
                            'manufacturer': 'Cessna',
                            'model': 'Citation X+',
                            'year': 2015,
                            'description': 'Exceptionally well-maintained Citation X+ with upgraded avionics, new paint and interior. Enrolled in all maintenance programs.',
                            'price': 7900000,
                            'total_time': 3200,
                            'registration': 'N123CX',
                            'serial': '750-0346',
                            'location': 'Dallas, TX (KDAL)',
                            'engines': 'Rolls-Royce AE3007C2',
                            'engine_hours': '3,200 / 3,200',
                            'programs': 'JSSI, ProParts, PowerAdvantage',
                            'avionics': 'Garmin G5000',
                            'max_speed': 527,
                            'range': 3460,
                            'service_ceiling': 51000,
                            'seats': 8,
                            'images': ['citation-x.jpg',
                                        'citation-x-cockpit.jpg',
                                        'citation-x-cabin.jpg',
                                        'citation-x-rear.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': True},
                           {'id': str(uuid.uuid4()),
                            'title': '2018 Embraer Phenom 300E',
                            'category': 'jet',
                            'manufacturer': 'Embraer',
                            'model': 'Phenom 300E',
                            'year': 2018,
                            'description': 'Beautiful Phenom 300E with premium interior configuration. Spotless maintenance history with all inspections up to date.',
                            'price': 8450000,
                            'total_time': 1850,
                            'registration': 'N456PH',
                            'serial': 'PHENOM-789',
                            'location': 'Fort Lauderdale, FL (KFLL)',
                            'engines': 'Pratt & Whitney PW535E',
                            'engine_hours': '1,850 / 1,850',
                            'programs': 'ESP Gold, Embraer Executive Care',
                            'avionics': 'Prodigy Touch Flight Deck',
                            'max_speed': 453,
                            'range': 1971,
                            'service_ceiling': 45000,
                            'seats': 9,
                            'images': ['phenom-300.jpg',
                                       'phenom-300-cockpit.jpg',
                                       'phenom-300-cabin.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': False},
                           {'id': str(uuid.uuid4()),
                            'title': '2020 Gulfstream G500',
                            'category': 'jet',
                            'manufacturer': 'Gulfstream',
                            'model': 'G500',
                            'year': 2020,
                            'description': 'Practically new G500 with custom VVIP interior. Features state-of-the-art avionics suite and entertainment system.',
                            'price': 42500000,
                            'total_time': 820,
                            'registration': 'N789GS',
                            'serial': 'G500-012',
                            'location': 'Teterboro, NJ (KTEB)',
                            'engines': 'Pratt & Whitney PW814GA',
                            'engine_hours': '820 / 820',
                            'programs': 'Gulfstream CMP, PowerAdvantage+',
                            'avionics': 'Symmetry Flight Deck',
                            'max_speed': 488,
                            'range': 5200,
                            'service_ceiling': 51000,
                            'seats': 14,
                            'images': ['g500.jpg',
                                       'g500-cockpit.jpg',
                                       'g500-cabin.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': False},
                           {'id': str(uuid.uuid4()),
                            'title': '2017 Bombardier Challenger 350',
                            'category': 'jet',
                            'manufacturer': 'Bombardier',
                            'model': 'Challenger 350',
                            'year': 2017,
                            'description': 'Immaculate Challenger 350 with Low Time. Perfect for transcontinental flights with exceptional comfort.',
                            'price': 12200000,
                            'total_time': 1450,
                            'registration': 'N350CL',
                            'serial': 'CL350-10215',
                            'location': 'Chicago, IL (KMDW)',
                            'engines': 'Honeywell HTF7350',
                            'engine_hours': '1,450 / 1,450',
                            'programs': 'Smart Parts Plus, MSP Gold',
                            'avionics': 'Rockwell Collins Pro Line 21',
                            'max_speed': 470,
                            'range': 3200,
                            'service_ceiling': 45000,
                            'seats': 10,
                            'images': ['challenger-350.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': True},
                           {'id': str(uuid.uuid4()),
                            'title': '2016 Pilatus PC-12 NG',
                            'category': 'turboprop',
                            'manufacturer': 'Pilatus',
                            'model': 'PC-12 NG',
                            'year': 2016,
                            'description': 'Versatile single-engine turboprop with excellent short-field capabilities and spacious cabin.',
                            'price': 3950000,
                            'total_time': 1780,
                            'registration': 'N912PC',
                            'serial': 'PC12-1782',
                            'location': 'Denver, CO (KAPA)',
                            'engines': 'Pratt & Whitney PT6A-67P',
                            'engine_hours': '1,780',
                            'programs': 'ESP Silver',
                            'avionics': 'Honeywell Primus Apex',
                            'max_speed': 290,
                            'range': 1845,
                            'service_ceiling': 30000,
                            'seats': 9,
                            'images': ['pc-12.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': False},
                           {'id': str(uuid.uuid4()),
                            'title': '2019 Dassault Falcon 8X',
                            'category': 'jet',
                            'manufacturer': 'Dassault',
                            'model': 'Falcon 8X',
                            'year': 2019,
                            'description': 'Ultra-long-range business jet with tri-jet configuration. Offers exceptional range and performance with the latest avionics.',
                            'price': 38900000,
                            'total_time': 1120,
                            'registration': 'N888FX',
                            'serial': 'F8X-045',
                            'location': 'Van Nuys, CA (KVNY)',
                            'engines': 'Pratt & Whitney PW307D',
                            'engine_hours': '1,120 / 1,120 / 1,120',
                            'programs': 'FalconCare Premium, Engine Support Program',
                            'avionics': 'EASy III Flight Deck',
                            'max_speed': 482,
                            'range': 6450,
                            'service_ceiling': 51000,
                            'seats': 14,
                            'images': ['falcon-8x.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': True},
                           {'id': str(uuid.uuid4()),
                            'title': '2010 Cirrus SR22 GTS G3',
                            'category': 'piston',
                            'manufacturer': 'Cirrus',
                            'model': 'SR22 GTS G3',
                            'year': 2010,
                            'description': 'Well-maintained SR22 with CAPS parachute system. Perfect for personal travel and training. Great avionics package.',
                            'price': 349000,
                            'total_time': 2450,
                            'registration': 'N22SR',
                            'serial': '1045',
                            'location': 'Scottsdale, AZ (KSDL)',
                            'engines': 'Continental IO-550-N',
                            'engine_hours': '950 SMOH',
                            'programs': 'Cirrus Approach Training',
                            'avionics': 'Avidyne Entegra R9',
                            'max_speed': 183,
                            'range': 1150,
                            'service_ceiling': 17500,
                            'seats': 4,
                            'images': ['cirrus-sr22.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': False},
                           {'id': str(uuid.uuid4()),
                            'title': '2022 Beechcraft King Air 360',
                            'category': 'turboprop',
                            'manufacturer': 'Beechcraft',
                            'model': 'King Air 360',
                            'year': 2022,
                            'description': 'The latest model King Air with upgraded cabin and avionics. Dual-club seating configuration. Only 350 hours since new.',
                            'price': 7950000,
                            'total_time': 350,
                            'registration': 'N360KB',
                            'serial': 'FL-1022',
                            'location': 'Wichita, KS (KICT)',
                            'engines': 'Pratt & Whitney PT6A-67A',
                            'engine_hours': '350 / 350',
                            'programs': 'ProParts, PowerAdvantage, MSP Gold',
                            'avionics': 'Rockwell Collins Pro Line Fusion',
                            'max_speed': 312,
                            'range': 1806,
                            'service_ceiling': 35000,
                            'seats': 11,
                            'images': ['king-air-360.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': True},
                           {'id': str(uuid.uuid4()),
                            'title': '2014 Learjet 75',
                            'category': 'jet',
                            'manufacturer': 'Bombardier',
                            'model': 'Learjet 75',
                            'year': 2014,
                            'description': 'Classic Learjet performance with modern avionics and comfort. Double-club configuration with flat-floor cabin.',
                            'price': 5900000,
                            'total_time': 3100,
                            'registration': 'N75LJ',
                            'serial': '45-455',
                            'location': 'Las Vegas, NV (KLAS)',
                            'engines': 'Honeywell TFE731-40BR',
                            'engine_hours': '3,100 / 3,100',
                            'programs': 'MSP Gold',
                            'avionics': 'Garmin G5000',
                            'max_speed': 464,
                            'range': 2040,
                            'service_ceiling': 51000,
                            'seats': 9,
                            'images': ['learjet-75.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': False},
                           {'id': str(uuid.uuid4()),
                            'title': '2021 Piper M600/SLS',
                            'category': 'turboprop',
                            'manufacturer': 'Piper',
                            'model': 'M600/SLS',
                            'year': 2021,
                            'description': 'Nearly new M600 with HALO safety system and full warranty. Excellent performer with G3000 avionics.',
                            'price': 2950000,
                            'total_time': 325,
                            'registration': 'N600MP',
                            'serial': '4698235',
                            'location': 'Vero Beach, FL (KVRB)',
                            'engines': 'Pratt & Whitney PT6A-42A',
                            'engine_hours': '325',
                            'programs': 'Factory Warranty',
                            'avionics': 'Garmin G3000',
                            'max_speed': 274,
                            'range': 1658,
                            'service_ceiling': 30000,
                            'seats': 6,
                            'images': ['piper-m600.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': False},
                           {'id': str(uuid.uuid4()),
                            'title': '2018 Daher TBM 930',
                            'category': 'turboprop',
                            'manufacturer': 'Daher',
                            'model': 'TBM 930',
                            'year': 2018,
                            'description': 'High-performance single-engine turboprop with jet-like speeds. Full de-ice system and G3000 avionics.',
                            'price': 3400000,
                            'total_time': 780,
                            'registration': 'N930TB',
                            'serial': '1237',
                            'location': 'Seattle, WA (KBFI)',
                            'engines': 'Pratt & Whitney PT6A-66D',
                            'engine_hours': '780',
                            'programs': 'TBM Care Program',
                            'avionics': 'Garmin G3000',
                            'max_speed': 330,
                            'range': 1730,
                            'service_ceiling': 31000,
                            'seats': 6,
                            'images': ['tbm-930.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': False},
                           {'id': str(uuid.uuid4()),
                            'title': '2015 Bell 429 GlobalRanger',
                            'category': 'helicopter',
                            'manufacturer': 'Bell',
                            'model': '429 GlobalRanger',
                            'year': 2015,
                            'description': 'Twin-engine, light-medium helicopter with advanced glass cockpit. VIP interior with 7 seats and air conditioning.',
                            'price': 5200000,
                            'total_time': 1350,
                            'registration': 'N429BH',
                            'serial': '57239',
                            'location': 'Houston, TX (KHOU)',
                            'engines': 'Pratt & Whitney PW207D1',
                            'engine_hours': '1,350 / 1,350',
                            'programs': 'Bell CAP',
                            'avionics': 'Garmin GTN 750',
                            'max_speed': 155,
                            'range': 411,
                            'service_ceiling': 20000,
                            'seats': 7,
                            'images': ['bell-429.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': False},
                           {'id': str(uuid.uuid4()),
                            'title': '2022 HondaJet Elite II',
                            'category': 'jet',
                            'manufacturer': 'Honda',
                            'model': 'HondaJet Elite II',
                            'year': 2022,
                            'description': 'Latest HondaJet with over-the-wing engine mount design and maximum range. Perfect for owner-pilots.',
                            'price': 6400000,
                            'total_time': 210,
                            'registration': 'N2HJ',
                            'serial': '42000156',
                            'location': 'Greensboro, NC (KGSO)',
                            'engines': 'GE Honda HF120',
                            'engine_hours': '210 / 210',
                            'programs': 'HondaCare',
                            'avionics': 'Garmin G3000',
                            'max_speed': 422,
                            'range': 1547,
                            'service_ceiling': 43000,
                            'seats': 7,
                            'images': ['hondajet.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': True},
                           {'id': str(uuid.uuid4()),
                            'title': '2019 Dassault Falcon 7X',
                            'category': 'jet',
                            'manufacturer': 'Dassault',
                            'model': 'Falcon 7X',
                            'year': 2019,
                            'description': 'Exceptional tri-jet aircraft with global range capabilities. Features a luxurious interior with three-zone cabin configuration.',
                            'price': 32800000,
                            'total_time': 890,
                            'registration': 'N7X777',
                            'serial': '7X-289',
                            'location': 'Miami, FL (KOPF)',
                            'engines': 'Pratt & Whitney PW307A',
                            'engine_hours': '890 / 890 / 890',
                            'programs': 'FalconCare Unlimited, ESP Gold',
                            'avionics': 'EASy III Flight Deck',
                            'max_speed': 485,
                            'range': 5950,
                            'service_ceiling': 51000,
                            'seats': 14,
                            'images': ['falcon-7x.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': True},
                           {'id': str(uuid.uuid4()),
                            'title': '2018 Cirrus Vision SF50 G2',
                            'category': 'jet',
                            'manufacturer': 'Cirrus',
                            'model': 'Vision SF50 G2',
                            'year': 2018,
                            'description': 'The innovative personal jet with CAPS parachute system. Perfect for owner-pilots with low operating costs and single-engine efficiency.',
                            'price': 2650000,
                            'total_time': 480,
                            'registration': 'N50SF',
                            'serial': 'SF50-087',
                            'location': 'Knoxville, TN (KTYS)',
                            'engines': 'Williams FJ33-5A',
                            'engine_hours': '480',
                            'programs': 'Cirrus JetStream',
                            'avionics': 'Cirrus Perspective Touch+',
                            'max_speed': 311,
                            'range': 1200,
                            'service_ceiling': 31000,
                            'seats': 7,
                            'images': ['vision-sf50.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': False},
                           {'id': str(uuid.uuid4()),
                            'title': '2021 Pilatus PC-24',
                            'category': 'jet',
                            'manufacturer': 'Pilatus',
                            'model': 'PC-24',
                            'year': 2021,
                            'description': 'The Super Versatile Jet with rough field capability. Unique design allows operations from unpaved runways and short fields.',
                            'price': 11250000,
                            'total_time': 420,
                            'registration': 'N24PC',
                            'serial': 'PC24-152',
                            'location': 'Denver, CO (KAPA)',
                            'engines': 'Williams FJ44-4A',
                            'engine_hours': '420 / 420',
                            'programs': 'CrystalCare',
                            'avionics': 'ACE Avionics by Honeywell',
                            'max_speed': 440,
                            'range': 2000,
                            'service_ceiling': 45000,
                            'seats': 10,
                            'images': ['pc-24.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': True},
                           {'id': str(uuid.uuid4()),
                            'title': '2023 Embraer Praetor 600',
                            'category': 'jet',
                            'manufacturer': 'Embraer',
                            'model': 'Praetor 600',
                            'year': 2023,
                            'description': 'Brand new Praetor 600 with transcontinental range and best-in-class cabin altitude. Features full digital cabin controls and Ka-band internet.',
                            'price': 21500000,
                            'total_time': 110,
                            'registration': 'N600PR',
                            'serial': 'PRAETOR-031',
                            'location': 'Melbourne, FL (KMLB)',
                            'engines': 'Honeywell HTF7500E',
                            'engine_hours': '110 / 110',
                            'programs': 'Embraer Executive Care',
                            'avionics': 'Rockwell Collins Pro Line Fusion',
                            'max_speed': 466,
                            'range': 4018,
                            'service_ceiling': 45000,
                            'seats': 12,
                            'images': ['praetor-600.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': True},
                           {'id': str(uuid.uuid4()),
                            'title': '2017 Cessna Caravan 208B Grand',
                            'category': 'turboprop',
                            'manufacturer': 'Cessna',
                            'model': 'Caravan 208B Grand',
                            'year': 2017,
                            'description': 'Versatile utility turboprop with executive interior. Perfect for short hauls to remote locations.',
                            'price': 3100000,
                            'total_time': 2700,
                            'registration': 'N208GC',
                            'serial': '208B-5107',
                            'location': 'Juneau, AK (PAJN)',
                            'engines': 'Pratt & Whitney PT6A-140',
                            'engine_hours': '2,700',
                            'programs': 'ProAdvantage',
                            'avionics': 'Garmin G1000 NXi',
                            'max_speed': 186,
                            'range': 1070,
                            'service_ceiling': 25000,
                            'seats': 10,
                            'images': ['caravan-208b.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': False},
                           {'id': str(uuid.uuid4()),
                            'title': '2014 Sikorsky S-76D',
                            'category': 'helicopter',
                            'manufacturer': 'Sikorsky',
                            'model': 'S-76D',
                            'year': 2014,
                            'description': 'Premium medium-size twin-engine helicopter with VIP configuration. Features low noise signature and vibration control.',
                            'price': 7200000,
                            'total_time': 1350,
                            'registration': 'N76SK',
                            'serial': '76D-0058',
                            'location': 'New York, NY (KJRB)',
                            'engines': 'Pratt & Whitney PW210S',
                            'engine_hours': '1,350 / 1,350',
                            'programs': 'TAP Blue',
                            'avionics': 'Thales TopDeck',
                            'max_speed': 178,
                            'range': 380,
                            'service_ceiling': 15000,
                            'seats': 8,
                            'images': ['sikorsky-s76d.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': False},
                           {'id': str(uuid.uuid4()),
                            'title': '2020 Airbus ACH145',
                            'category': 'helicopter',
                            'manufacturer': 'Airbus',
                            'model': 'ACH145',
                            'year': 2020,
                            'description': 'Airbus Corporate Helicopters flagship model with ultra-luxury interior. Features Fenestron tail rotor for quiet operations.',
                            'price': 9500000,
                            'total_time': 580,
                            'registration': 'N145AH',
                            'serial': '9785',
                            'location': 'Los Angeles, CA (KVNY)',
                            'engines': 'Safran Arriel 2E',
                            'engine_hours': '580 / 580',
                            'programs': 'HCare Smart',
                            'avionics': 'Helionix',
                            'max_speed': 150,
                            'range': 370,
                            'service_ceiling': 18000,
                            'seats': 9,
                            'images': ['airbus-ach145.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': True},
                           {'id': str(uuid.uuid4()),
                            'title': '2013 Beechcraft Baron G58',
                            'category': 'piston',
                            'manufacturer': 'Beechcraft',
                            'model': 'Baron G58',
                            'year': 2013,
                            'description': 'Twin-engine piston aircraft with excellent handling characteristics. Perfect for personal travel and business.',
                            'price': 850000,
                            'total_time': 1850,
                            'registration': 'N58BG',
                            'serial': 'TH-2394',
                            'location': 'Orlando, FL (KORL)',
                            'engines': 'Continental IO-550-C',
                            'engine_hours': '950 / 950 SMOH',
                            'programs': 'N/A',
                            'avionics': 'Garmin G1000',
                            'max_speed': 202,
                            'range': 1480,
                            'service_ceiling': 20688,
                            'seats': 6,
                            'images': ['baron-g58.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': False},
                           {'id': str(uuid.uuid4()),
                            'title': '2022 Diamond DA62',
                            'category': 'piston',
                            'manufacturer': 'Diamond',
                            'model': 'DA62',
                            'year': 2022,
                            'description': 'Modern twin-engine with carbon fiber construction and diesel engines. Offers exceptional efficiency and safety.',
                            'price': 1350000,
                            'total_time': 230,
                            'registration': 'N62DA',
                            'serial': '62.091',
                            'location': 'Austin, TX (KAUS)',
                            'engines': 'Austro AE330',
                            'engine_hours': '230 / 230',
                            'programs': 'Diamond Care',
                            'avionics': 'Garmin G1000 NXi',
                            'max_speed': 190,
                            'range': 1500,
                            'service_ceiling': 20000,
                            'seats': 7,
                            'images': ['diamond-da62.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': False},
                           {'id': str(uuid.uuid4()),
                            'title': '2022 Textron Aviation Cessna Denali',
                            'category': 'turboprop',
                            'manufacturer': 'Textron Aviation',
                            'model': 'Cessna Denali',
                            'year': 2022,
                            'description': 'Brand new single-engine turboprop with large cabin cross-section. Features GE Catalyst engine and advanced avionics.',
                            'price': 5850000,
                            'total_time': 125,
                            'registration': 'N2022D',
                            'serial': 'DENALI-005',
                            'location': 'Wichita, KS (KICT)',
                            'engines': 'GE Catalyst',
                            'engine_hours': '125',
                            'programs': 'ProAdvantage+',
                            'avionics': 'Garmin G3000',
                            'max_speed': 285,
                            'range': 1600,
                            'service_ceiling': 31000,
                            'seats': 11,
                            'images': ['cessna-denali.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': True},
                           {'id': str(uuid.uuid4()),
                            'title': '2021 Gulfstream G700',
                            'category': 'jet',
                            'manufacturer': 'Gulfstream',
                            'model': 'G700',
                            'year': 2021,
                            'description': 'The ultimate business jet with ultra-long-range capabilities. Features five living areas and the most spacious cabin in its class.',
                            'price': 78500000,
                            'total_time': 350,
                            'registration': 'N700GS',
                            'serial': 'G700-012',
                            'location': 'Savannah, GA (KSAV)',
                            'engines': 'Rolls-Royce Pearl 700',
                            'engine_hours': '350 / 350',
                            'programs': 'Gulfstream CMP Platinum',
                            'avionics': 'Symmetry Flight Deck',
                            'max_speed': 516,
                            'range': 7500,
                            'service_ceiling': 51000,
                            'seats': 19,
                            'images': ['g700.jpg'],
                            'seller_id': seller_id,
                            'seller_name': 'Jet Broker LLC',
                            'created_at': datetime.now().isoformat(),
                            'status': 'active',
                            'featured': True}]
        save_listings(sample_listings)


# Initialize the sample data when the module is imported
init_sample_data()

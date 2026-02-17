"""
Production Flask app for Jet Finder - Railway deployment.
Serves auth, listings, billing, frontend pages, and API routes used by the main site.
"""
import os
import json
import logging
from flask import Flask, render_template, request, jsonify, redirect

from models import init_db
from auth import auth_bp, get_current_user, set_limiter
from listings_api import listings_bp, get_my_listings, create_listing
from billing_api import billing_bp
from security import init_rate_limiter, add_security_headers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'change-me-in-production')

# CORS: same origin in production, or explicit origin from env
try:
    from flask_cors import CORS
    app_base = os.environ.get('APP_BASE_URL', '').rstrip('/')
    if app_base:
        CORS(app, origins=[app_base], supports_credentials=True)
    else:
        CORS(app, supports_credentials=True, origins='*')
except ImportError:
    pass

# Database init on startup
try:
    init_db()
except Exception as e:
    logger.exception("Database initialization failed")
    raise

# Rate limiter (auth module uses it)
limiter = init_rate_limiter(app)
set_limiter(limiter)

# Security headers
app.after_request(add_security_headers)

# Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(listings_bp)
app.register_blueprint(billing_bp)
logger.info("API blueprints registered")

# ----- Frontend routes -----
@app.route('/')
def index():
    return render_template('public/index.html')

@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template('auth/signup.html')

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('auth/login.html')

@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect('/login')
    return render_template('dashboard/index.html', user=user)

@app.route('/admin')
def admin():
    user = get_current_user()
    if not user or not getattr(user, 'is_admin', False):
        return jsonify({'error': 'Forbidden'}), 403
    return render_template('admin/index.html')

@app.route('/create-listing')
def create_listing_page():
    user = get_current_user()
    if not user:
        return redirect('/login')
    return render_template('create_listing.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

# ----- API routes (so they work when Railway runs this app) -----
_AIRPORTS_FALLBACK = [
    {'iata': 'LAX', 'icao': 'KLAX', 'name': 'Los Angeles International', 'city': 'Los Angeles', 'country': 'United States', 'lat': 33.9425, 'lon': -118.4081},
    {'iata': 'JFK', 'icao': 'KJFK', 'name': 'John F Kennedy International', 'city': 'New York', 'country': 'United States', 'lat': 40.6398, 'lon': -73.7789},
    {'iata': 'ORD', 'icao': 'KORD', 'name': 'Chicago O\'Hare International', 'city': 'Chicago', 'country': 'United States', 'lat': 41.9786, 'lon': -87.9047},
    {'iata': 'DFW', 'icao': 'KDFW', 'name': 'Dallas Fort Worth International', 'city': 'Dallas', 'country': 'United States', 'lat': 32.8968, 'lon': -97.0380},
    {'iata': 'ATL', 'icao': 'KATL', 'name': 'Hartsfield-Jackson Atlanta International', 'city': 'Atlanta', 'country': 'United States', 'lat': 33.6367, 'lon': -84.4281},
]

def _load_airports_data():
    _root = os.path.dirname(os.path.abspath(__file__))
    for _sub in ('static/data/airports.json', 'airports.json'):
        _path = os.path.join(_root, _sub)
        if os.path.isfile(_path):
            try:
                with open(_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not load %s: %s", _path, e)
    logger.warning("Airport data file not found; using fallback list")
    return _AIRPORTS_FALLBACK

@app.route('/api/debug')
def api_debug():
    return jsonify({
        'app': 'app_production',
        'routes': ['/api/airports', '/api/user-listings'],
        'airports_route_exists': True
    }), 200

@app.route('/api/airports')
def api_airports():
    try:
        query = (request.args.get('q') or '').strip().upper()
        if not query or len(query) < 2:
            return jsonify([])
        airports = _load_airports_data()
        matching = []
        for airport in airports:
            iata = (airport.get('iata') or '').upper()
            icao = (airport.get('icao') or '').upper()
            name = (airport.get('name') or '').upper()
            city = (airport.get('city') or '').upper()
            row = {
                'iata': airport.get('iata', ''),
                'icao': airport.get('icao', ''),
                'name': airport.get('name', ''),
                'city': airport.get('city', ''),
                'country': airport.get('country', ''),
                'lat': airport.get('lat', 0),
                'lon': airport.get('lon', 0),
            }
            if iata.startswith(query):
                row['match_type'] = 'iata'
                matching.append(row)
            elif icao.startswith(query):
                row['match_type'] = 'icao'
                matching.append(row)
            elif query in name or query in city:
                row['match_type'] = 'name_city'
                matching.append(row)
        matching.sort(key=lambda x: (0 if x['match_type'] == 'iata' else (1 if x['match_type'] == 'icao' else 2), x['name']))
        return jsonify(matching[:20])
    except Exception as e:
        logger.exception("Error in /api/airports")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user-listings', methods=['GET', 'POST'])
def user_listings_alias():
    if request.method == 'GET':
        return get_my_listings()
    return create_listing()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5015)), debug=False)

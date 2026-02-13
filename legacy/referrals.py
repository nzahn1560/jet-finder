from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import os
import json
from datetime import datetime
import uuid
import random  # Add import for random module

# Create blueprint
referrals = Blueprint('referrals', __name__, url_prefix='/referrals')

# File paths for data storage
PROVIDERS_DB_FILE = 'data/providers.json'
REFERRALS_DB_FILE = 'data/referrals.json'

# Helper function to load providers

def load_providers():
    if os.path.exists(PROVIDERS_DB_FILE):
        with open(PROVIDERS_DB_FILE, 'r') as f:
            return json.load(f)
    return []

# Helper function to save providers

def save_providers(providers):
    os.makedirs(os.path.dirname(PROVIDERS_DB_FILE), exist_ok=True)
    with open(PROVIDERS_DB_FILE, 'w') as f:
        json.dump(providers, f, indent=2)

# Helper function to load referrals

def load_referrals():
    if os.path.exists(REFERRALS_DB_FILE):
        with open(REFERRALS_DB_FILE, 'r') as f:
            return json.load(f)
    return []

# Helper function to save referrals

def save_referrals(referrals):
    os.makedirs(os.path.dirname(REFERRALS_DB_FILE), exist_ok=True)
    with open(REFERRALS_DB_FILE, 'w') as f:
        json.dump(referrals, f, indent=2)

# Helper to get a provider by ID

def get_provider(provider_id):
    providers = load_providers()
    for provider in providers:
        if provider['id'] == provider_id:
            return provider
    return None

# Helper to get a referral by ID

def get_referral(referral_id):
    referrals = load_referrals()
    for referral in referrals:
        if referral['id'] == referral_id:
            return referral
    return None

# Helper to create a new referral

def create_referral(user_id, provider_id, listing_id=None, notes=None):
    referrals = load_referrals()

    # Generate new referral ID
    referral_id = f"ref-{str(uuid.uuid4())[:8]}"

    # Create new referral record
    new_referral = {
        "id": referral_id,
        "user_id": user_id,
        "provider_id": provider_id,
        "listing_id": listing_id,
        "timestamp": datetime.now().isoformat(),
        "status": "contacted",
        "notes": notes,
        "conversion_status": "pending",
        "conversion_value": None,
        "conversion_date": None
    }

    referrals.append(new_referral)
    save_referrals(referrals)

    return new_referral

# Helper to update referral status

def update_referral_status(referral_id, status, conversion_value=None):
    referrals = load_referrals()
    for referral in referrals:
        if referral['id'] == referral_id:
            referral['status'] = status
            if status == 'converted':
                referral['conversion_status'] = 'converted'
                referral['conversion_date'] = datetime.now().isoformat()
                if conversion_value:
                    referral['conversion_value'] = conversion_value
            save_referrals(referrals)
            return referral
    return None

# Helper to get referrals by provider

def get_referrals_by_provider(provider_id):
    referrals = load_referrals()
    return [r for r in referrals if r['provider_id'] == provider_id]

# Helper to get referrals by user

def get_referrals_by_user(user_id):
    referrals = load_referrals()
    return [r for r in referrals if r['user_id'] == user_id]

# Helper to filter providers by service type

def filter_providers_by_service(service_type=None):
    providers = load_providers()
    if not service_type:
        return providers

    return [p for p in providers if service_type in p.get('services', [])]

# Routes

@referrals.route('/directory')
def directory():
    """Service Provider Directory page"""
    # Get filter parameters
    service_type = request.args.get('service', None)
    verified_only = request.args.get('verified', 'false') == 'true'

    # Load and filter providers
    providers = filter_providers_by_service(service_type)

    # Filter verified providers if needed
    if verified_only:
        providers = [p for p in providers if p.get('verified', False)]

    # Add random review counts for providers that don't have them
    for provider in providers:
        if 'review_count' not in provider:
            provider['review_count'] = random.randint(5, 25)

    # Sort providers - verified first, then alphabetically
    providers.sort(key=lambda x: (not x.get('verified', False), x.get('name', '')))

    return render_template('referrals/directory.html',
                           providers=providers,
                           service_type=service_type,
                           verified_only=verified_only)

@referrals.route('/provider/<string:provider_id>')
def provider_detail(provider_id):
    """Provider detail page"""
    provider = get_provider(provider_id)
    if not provider:
        flash('Provider not found', 'danger')
        return redirect(url_for('referrals.directory'))

    return render_template('referrals/provider_detail.html', provider=provider)

@referrals.route('/track', methods=['POST'])
def track_referral():
    """API endpoint to track a referral click"""
    data = request.get_json()

    user_id = data.get('user_id')
    provider_id = data.get('provider_id')
    listing_id = data.get('listing_id')
    notes = data.get('notes')

    # Validate input
    if not user_id or not provider_id:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    # Create the referral
    referral = create_referral(user_id, provider_id, listing_id, notes)

    return jsonify({'success': True, 'referral_id': referral['id']})

@referrals.route('/admin')
def admin_dashboard():
    """Admin dashboard for referral tracking"""
    # Check if user is admin (in a real app, this would be more robust)
    # current_user = None  # This should be populated from your auth system

    # Load all data
    providers = load_providers()
    referrals = load_referrals()

    # Calculate summary statistics
    total_referrals = len(referrals)
    converted_referrals = len([r for r in referrals if r['conversion_status'] == 'converted'])
    conversion_rate = (converted_referrals / total_referrals * 100) if total_referrals > 0 else 0

    # Get total revenue from conversions
    total_revenue = sum([r.get('conversion_value', 0) or 0 for r in referrals])

    # Prepare provider stats
    provider_stats = []
    for provider in providers:
        provider_referrals = get_referrals_by_provider(provider['id'])
        provider_stats.append({
            'id': provider['id'],
            'name': provider['name'],
            'total_referrals': len(provider_referrals),
            'converted': len([r for r in provider_referrals if r['conversion_status'] == 'converted']),
            'revenue': sum([r.get('conversion_value', 0) or 0 for r in provider_referrals])
        })

    return render_template('referrals/admin_dashboard.html',
                           total_referrals=total_referrals,
                           converted_referrals=converted_referrals,
                           conversion_rate=conversion_rate,
                           total_revenue=total_revenue,
                           provider_stats=provider_stats,
                           providers=providers,
                           referrals=referrals)

@referrals.route('/admin/provider/<string:provider_id>')
def admin_provider_details(provider_id):
    """Admin view for a specific provider's referrals"""
    provider = get_provider(provider_id)
    if not provider:
        flash('Provider not found', 'danger')
        return redirect(url_for('referrals.admin_dashboard'))

    # Get all referrals for this provider
    provider_referrals = get_referrals_by_provider(provider_id)

    # Calculate stats
    total_referrals = len(provider_referrals)
    converted_referrals = len([r for r in provider_referrals if r['conversion_status'] == 'converted'])
    conversion_rate = (converted_referrals / total_referrals * 100) if total_referrals > 0 else 0
    total_revenue = sum([r.get('conversion_value', 0) or 0 for r in provider_referrals])

    return render_template('referrals/admin_provider_details.html',
                           provider=provider,
                           referrals=provider_referrals,
                           total_referrals=total_referrals,
                           converted_referrals=converted_referrals,
                           conversion_rate=conversion_rate,
                           total_revenue=total_revenue)

@referrals.route('/admin/update-referral', methods=['POST'])
def update_referral():
    """API endpoint to update a referral's status"""
    data = request.get_json()

    referral_id = data.get('referral_id')
    status = data.get('status')
    conversion_value = data.get('conversion_value')

    # Validate input
    if not referral_id or not status:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    # Update the referral
    referral = update_referral_status(referral_id, status, conversion_value)
    if not referral:
        return jsonify({'success': False, 'message': 'Referral not found'}), 404

    return jsonify({'success': True, 'referral': referral})

# For provider management and verified status

@referrals.route('/admin/providers')
def admin_providers():
    """Admin page to manage providers"""
    providers = load_providers()
    return render_template('referrals/admin_providers.html', providers=providers)

@referrals.route('/admin/provider/edit/<string:provider_id>', methods=['GET', 'POST'])
def admin_edit_provider(provider_id):
    """Admin page to edit a provider"""
    providers = load_providers()

    # Find the provider
    provider = None
    for p in providers:
        if p['id'] == provider_id:
            provider = p
            break

    if not provider:
        flash('Provider not found', 'danger')
        return redirect(url_for('referrals.admin_providers'))

    # Handle form submission
    if request.method == 'POST':
        provider['name'] = request.form.get('name')
        provider['description'] = request.form.get('description')
        provider['services'] = request.form.getlist('services')
        provider['location'] = request.form.get('location')
        provider['contact_email'] = request.form.get('contact_email')
        provider['contact_phone'] = request.form.get('contact_phone')
        provider['website'] = request.form.get('website')
        provider['verified'] = 'verified' in request.form
        provider['featured'] = 'featured' in request.form

        save_providers(providers)
        flash('Provider updated successfully', 'success')
        return redirect(url_for('referrals.admin_providers'))

    return render_template('referrals/admin_edit_provider.html', provider=provider)

@referrals.route('/admin/provider/create', methods=['GET', 'POST'])
def admin_create_provider():
    """Admin page to create a new provider"""
    if request.method == 'POST':
        providers = load_providers()

        # Generate provider ID
        provider_id = f"prov-{str(uuid.uuid4())[:8]}"

        # Create new provider
        new_provider = {
            'id': provider_id,
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'services': request.form.getlist('services'),
            'location': request.form.get('location'),
            'contact_email': request.form.get('contact_email'),
            'contact_phone': request.form.get('contact_phone'),
            'website': request.form.get('website'),
            'verified': 'verified' in request.form,
            'subscription_status': 'inactive',
            'subscription_id': None,
            'join_date': datetime.now().isoformat(),
            'logo': request.form.get('logo'),
            'featured': 'featured' in request.form
        }

        providers.append(new_provider)
        save_providers(providers)

        flash('Provider created successfully', 'success')
        return redirect(url_for('referrals.admin_providers'))

    return render_template('referrals/admin_create_provider.html')

@referrals.route('/admin/provider/delete/<string:provider_id>', methods=['POST'])
def admin_delete_provider(provider_id):
    """Admin action to delete a provider"""
    providers = load_providers()

    # Filter out the provider to delete
    providers = [p for p in providers if p['id'] != provider_id]
    save_providers(providers)

    flash('Provider deleted successfully', 'success')
    return redirect(url_for('referrals.admin_providers'))

@referrals.route('/admin/provider/toggle-verify/<string:provider_id>', methods=['POST'])
def admin_toggle_verify(provider_id):
    """Admin action to toggle verified status"""
    providers = load_providers()

    for provider in providers:
        if provider['id'] == provider_id:
            provider['verified'] = not provider.get('verified', False)
            save_providers(providers)

            status = 'verified' if provider['verified'] else 'unverified'
            flash(f'Provider {status} successfully', 'success')
            break

    return redirect(url_for('referrals.admin_providers'))

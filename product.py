"""Marketplace, match, broker, and charter routes that sit on top of the Flask app."""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

import authz
import db as db_module
import matching
import pricing
import sections as sections_module

logger = logging.getLogger(__name__)

product = Blueprint('product', __name__)


def _current_user():
    from app import get_current_user_from_request
    return get_current_user_from_request()


def _require_user():
    user = _current_user()
    if not user:
        if request.path.startswith('/api/'):
            return None, (jsonify({'error': 'not_logged_in'}), 401)
        return None, redirect(url_for('login', next=request.path))
    return user, None


@product.route('/api/pricing/listing')
def api_listing_price():
    """Server price for one listing. The browser cannot choose the amount."""
    return jsonify(pricing.listing_price())


def _listing_cards():
    profiles = {row.get('id'): row for row in db_module.get_all_aircraft_profiles()}
    cards = []
    for row in db_module.get_active_user_listings():
        profile = profiles.get(row.get('profile_id')) or {}
        cards.append({
            'id': row.get('id'),
            'title': row.get('title'),
            'manufacturer': row.get('manufacturer') or profile.get('manufacturer'),
            'price': row.get('price'),
            'year': row.get('year'),
            'hours': row.get('hours'),
            'location': row.get('location'),
            'range': profile.get('range'),
            'passengers': profile.get('passengers'),
            'speed': profile.get('speed'),
            'category': profile.get('category'),
            'image': profile.get('image'),
            'engine_hours': row.get('engine_hours'),
            'avionics': row.get('avionics'),
            'paint_year': row.get('paint_year'),
            'interior_year': row.get('interior_year'),
            'description': row.get('description'),
        })
    return cards


@product.route('/match')
def match_page():
    return render_template('match.html')


@product.route('/api/match', methods=['POST'])
def api_match():
    data = request.get_json(silent=True) or {}
    ranked = matching.rank_listings(_listing_cards(), data)
    return jsonify(ranked)


@product.route('/marketplace')
def marketplace_browse():
    cards = _listing_cards()
    manufacturer = (request.args.get('manufacturer') or '').strip().lower()
    if manufacturer:
        cards = [card for card in cards if manufacturer in (card.get('manufacturer') or '').lower()]
    try:
        max_price = float(request.args.get('max_price')) if request.args.get('max_price') else None
    except ValueError:
        max_price = None
    if max_price is not None:
        cards = [card for card in cards if (card.get('price') or 0) <= max_price]
    cards.sort(key=lambda card: card.get('price') or 0)
    return render_template('marketplace_browse.html', listings=cards, manufacturer=request.args.get('manufacturer') or '', max_price=request.args.get('max_price') or '')


@product.route('/listing/<int:listing_id>')
def public_listing(listing_id):
    row = db_module.get_user_listing_by_id(listing_id, active_only=True)
    if not row or sections_module.normalize_market(row.get('market')) != 'public':
        return render_template('error.html', error_code=404, message='Listing not found'), 404
    profiles = {item.get('id'): item for item in db_module.get_all_aircraft_profiles()}
    profile = profiles.get(row.get('profile_id')) or {}
    media = db_module.list_listing_media(listing_id)
    if not any(item.get('media_type') == 'photo' for item in media):
        media = [
            {'media_type': 'photo', 'url': url.strip()}
            for url in (row.get('images') or '').split(',') if url.strip()
        ] + media
    owner = db_module.get_user_by_id(row.get('user_id')) if row.get('user_id') else None
    seller_name = ''
    if owner:
        seller_name = ' '.join(part for part in [owner.get('first_name'), owner.get('last_name')] if part)
    brokers = [broker for broker in db_module.list_approved_brokers() if broker.get('id') != row.get('user_id')]
    return render_template(
        'listing_public.html', listing=row, profile=profile, media=media,
        seller_name=seller_name or 'Seller', brokers=brokers,
    )


@product.route('/api/broker/profile', methods=['GET', 'PATCH'])
def api_broker_profile():
    user, err = _require_user()
    if err:
        return err
    if request.method == 'PATCH':
        data = request.get_json(silent=True) or {}
        from app import has_active_subscription
        on_team = bool(db_module.user_on_active_team(user['id']))
        paid = has_active_subscription(user['id'], 'broker') or has_active_subscription(user['id'], 'broker_team')
        if not user.get('is_admin') and not (authz.has_role(user, 'broker') and (on_team or paid)):
            return jsonify({
                'error': 'broker_subscription_required',
                'message': 'Broker access is required.',
            }), 402
        data['profile_role'] = 'broker'
        db_module.update_user_profile(user['id'], data)
        airport = sections_module.resolve_place(data.get('profile_location') or user.get('profile_location'), country='US')
        if airport and airport.get('lat') is not None:
            with db_module.get_session() as session:
                session.query(db_module.User).filter(db_module.User.id == user['id']).update({
                    'broker_lat': airport.get('lat'),
                    'broker_lon': airport.get('lon'),
                }, synchronize_session=False)
        user = db_module.get_user_by_id(user['id']) or user
    return jsonify({'user': _public_broker(user)})


def _public_broker(user: dict) -> dict:
    return {
        'id': user.get('id'),
        'first_name': user.get('first_name'),
        'last_name': user.get('last_name'),
        'company': user.get('company'),
        'phone': user.get('phone'),
        'email': user.get('email'),
        'profile_location': user.get('profile_location'),
        'profile_role': user.get('profile_role'),
        'roles': user.get('roles'),
        'broker_bio': user.get('broker_bio'),
        'broker_specialties': user.get('broker_specialties'),
        'broker_website': user.get('broker_website'),
        'broker_years': user.get('broker_years'),
        'broker_verified': bool(user.get('broker_verified')),
        'broker_state': user.get('broker_state'),
        'broker_country': user.get('broker_country'),
        'broker_lat': user.get('broker_lat'),
        'broker_lon': user.get('broker_lon'),
    }


@product.route('/api/charter/available')
def api_charter_available():
    """Real operator aircraft that are not blocked on the requested date."""
    on_date = (request.args.get('date') or '').strip()
    try:
        passengers = int(request.args.get('passengers') or 1)
    except ValueError:
        passengers = 1
    departure = sections_module.resolve_place(request.args.get('departure'))
    arrival = sections_module.resolve_place(request.args.get('arrival'))
    distance = None
    if departure and arrival:
        distance = sections_module.haversine_nm(departure['lat'], departure['lon'], arrival['lat'], arrival['lon']) * 1.08
    aircraft = []
    for row in db_module.list_charter_aircraft(active_only=True):
        if on_date and db_module.charter_aircraft_blocked(row['id'], on_date):
            continue
        seats = row.get('seats') or 0
        if seats and seats < passengers:
            continue
        if distance and row.get('range_nm') and row['range_nm'] < distance:
            continue
        base = sections_module.resolve_place(row.get('base_airport'))
        hours = None
        estimate = None
        speed = row.get('speed_kts') or 400
        if distance and speed:
            hours = round(distance / speed + 0.4, 1)
            if row.get('hourly_rate'):
                estimate = int(round(hours * float(row['hourly_rate'])))
        aircraft.append({
            'id': row['id'],
            'name': row['name'],
            'registration': row.get('registration'),
            'base_airport': row.get('base_airport'),
            'base': sections_module._airport_brief(base) if base else None,
            'seats': seats,
            'hourly_rate': row.get('hourly_rate'),
            'range_nm': row.get('range_nm'),
            'flight_hours': hours,
            'estimated_total': estimate,
            'notes': row.get('notes'),
            'bookable': True,
        })
    return jsonify({
        'aircraft': aircraft,
        'distance_nm': int(round(distance)) if distance else None,
        'departure': sections_module._airport_brief(departure) if departure else None,
        'arrival': sections_module._airport_brief(arrival) if arrival else None,
        'note': 'Only aircraft an operator has listed are bookable. Estimates are not a confirmed quote.',
    })


@product.route('/api/charter/book', methods=['POST'])
def api_charter_book():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    try:
        aircraft_id = int(data.get('aircraft_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Choose an aircraft from the available list.'}), 400
    aircraft = db_module.get_charter_aircraft(aircraft_id)
    if not aircraft or aircraft.get('status') != 'active':
        return jsonify({'error': 'That aircraft is not available.'}), 404
    departure = (data.get('departure_airport') or '').strip()
    arrival = (data.get('arrival_airport') or '').strip()
    if not name or '@' not in email or not departure or not arrival:
        return jsonify({'error': 'Name, email, and both airports are required.'}), 400
    on_date = (data.get('departure_date') or '').strip()
    if on_date and db_module.charter_aircraft_blocked(aircraft_id, on_date):
        return jsonify({'error': 'That aircraft is blocked on the requested date.'}), 409
    user = _current_user()
    booking_id = db_module.create_charter_booking({
        'aircraft_id': aircraft_id,
        'user_id': user['id'] if user else None,
        'contact_name': name,
        'contact_email': email,
        'contact_phone': data.get('phone'),
        'departure_airport': departure,
        'arrival_airport': arrival,
        'departure_date': on_date or None,
        'passengers': data.get('passengers') or 1,
        'estimated_price': data.get('estimated_price'),
        'notes': data.get('notes'),
    })
    _mail_charter_request(email, name, aircraft.get('name'), departure, arrival)
    return jsonify({
        'ok': True,
        'id': booking_id,
        'status': 'requested',
        'message': 'Request sent. The aircraft is not booked until the operator confirms it.',
    }), 201


@product.route('/charter/fleet', methods=['GET', 'POST'])
def charter_fleet_page():
    return render_template(
        'coming_soon.html',
        product='Charter',
        summary='Shop a route and see the aircraft that can fly it.',
    )
    user, err = _require_user()
    if err:
        return err
    if not authz.is_operator(user):
        return render_template('error.html', error_code=403, message='A charter operator account is required.'), 403
    operator_id = db_module.ensure_charter_operator(
        user['id'], user.get('company') or user.get('email'), user.get('phone'), user.get('email')
    )
    error = None
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if not name:
            error = 'Aircraft name is required.'
        else:
            def _int(key):
                raw = request.form.get(key)
                try:
                    return int(raw) if raw else None
                except ValueError:
                    return None
            def _float(key):
                raw = request.form.get(key)
                try:
                    return float(raw) if raw else None
                except ValueError:
                    return None
            db_module.create_charter_aircraft(operator_id, {
                'name': name,
                'registration': request.form.get('registration'),
                'base_airport': request.form.get('base_airport'),
                'seats': _int('seats'),
                'hourly_rate': _float('hourly_rate'),
                'range_nm': _int('range_nm'),
                'speed_kts': _int('speed_kts'),
                'notes': request.form.get('notes'),
            })
            return redirect(url_for('product.charter_fleet_page'))
    aircraft = db_module.list_charter_aircraft(operator_id=operator_id, active_only=False)
    bookings = db_module.list_charter_bookings(operator_id=operator_id)
    return render_template('charter_fleet.html', aircraft=aircraft, bookings=bookings, error=error)


@product.route('/api/charter/fleet/<int:aircraft_id>/block', methods=['POST'])
def api_charter_block(aircraft_id):
    user, err = _require_user()
    if err:
        return err
    if not authz.is_operator(user):
        return jsonify({'error': 'forbidden'}), 403
    operator = db_module.get_charter_operator_for_user(user['id'])
    aircraft = db_module.get_charter_aircraft(aircraft_id)
    if not aircraft or not operator or aircraft.get('operator_id') != operator.get('id'):
        if not user.get('is_admin'):
            return jsonify({'error': 'forbidden'}), 403
    data = request.get_json(silent=True) or request.form
    start = (data.get('start_date') or '').strip()
    end = (data.get('end_date') or start).strip()
    if not start:
        return jsonify({'error': 'start_date is required'}), 400
    block_id = db_module.add_charter_block(aircraft_id, start, end, data.get('reason'))
    return jsonify({'ok': True, 'id': block_id}), 201


@product.route('/api/charter/bookings/<int:booking_id>/status', methods=['POST'])
def api_charter_booking_status(booking_id):
    user, err = _require_user()
    if err:
        return err
    booking = db_module.get_charter_booking(booking_id)
    if not booking:
        return jsonify({'error': 'not_found'}), 404
    aircraft = db_module.get_charter_aircraft(booking['aircraft_id'])
    operator = db_module.get_charter_operator_for_user(user['id']) if not user.get('is_admin') else {'id': aircraft.get('operator_id') if aircraft else None}
    if not user.get('is_admin'):
        if not operator or not aircraft or aircraft.get('operator_id') != operator.get('id'):
            return jsonify({'error': 'forbidden'}), 403
    data = request.get_json(silent=True) or {}
    status = (data.get('status') or '').strip()
    if status not in ('pending_operator_confirmation', 'confirmed', 'cancelled', 'completed'):
        return jsonify({'error': 'unsupported status'}), 400
    if not db_module.set_charter_booking_status(booking_id, status):
        return jsonify({'error': 'could not update'}), 400
    _mail_charter_status(booking.get('contact_email'), status, aircraft.get('name') if aircraft else 'aircraft')
    return jsonify({'ok': True, 'status': status})


@product.route('/api/me/charter-bookings')
def api_my_charter_bookings():
    user, err = _require_user()
    if err:
        return err
    return jsonify({'bookings': db_module.list_charter_bookings(user_id=user['id'])})


def _mail_charter_request(email, name, aircraft, departure, arrival):
    try:
        import email_service
        if not email_service.is_configured():
            logger.info('Charter request saved for %s. Email is not configured.', email)
            return
        email_service.send_email(
            email,
            'JetSchool charter request received',
            f'<p>{name}, we received your request for {aircraft} from {departure} to {arrival}.</p>'
            '<p>This is a request. The trip is not confirmed until the operator accepts it.</p>',
            f'{name}, we received your request for {aircraft} from {departure} to {arrival}. It is not confirmed yet.',
        )
    except Exception:
        logger.exception('charter request email failed')


def _mail_charter_status(email, status, aircraft):
    if not email:
        return
    try:
        import email_service
        if not email_service.is_configured():
            return
        if status == 'confirmed':
            text = f'The operator confirmed {aircraft}. JetSchool will follow up on next steps.'
        elif status == 'cancelled':
            text = f'The request for {aircraft} was declined.'
        else:
            text = f'The request for {aircraft} is now {status.replace("_", " ")}.'
        email_service.send_email(email, 'JetSchool charter update', f'<p>{text}</p>', text)
    except Exception:
        logger.exception('charter status email failed')

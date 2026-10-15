"""Product checks for accounts, listings, price, brokers, scoring, and charter."""
import os
import tempfile
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

_DB = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
os.environ['DATABASE_URL'] = 'sqlite:///' + _DB.name
os.environ['FLASK_ENV'] = 'development'
os.environ['REQUIRE_PAYMENT_FOR_LISTINGS'] = 'false'
os.environ.pop('SECRET_KEY', None)

import pricing  # noqa: E402
from app import app  # noqa: E402
import db as db_module  # noqa: E402
import matching  # noqa: E402


class ProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        profiles = db_module.get_all_aircraft_profiles()
        cls.profile_id = profiles[0]['id']
        cls.seller = cls._signup('seller@example.com', 'seller-pass-1', 'seller')
        cls.buyer = cls._signup('buyer@example.com', 'buyer-pass-1', 'buyer')
        cls.broker = cls._signup('broker@example.com', 'broker-pass-1', 'broker')
        cls.operator = cls._signup('operator@example.com', 'operator-pass-1', 'charter_operator')
        cls.admin = cls._signup('admin@example.com', 'admin-pass-1', 'seller')
        db_module.set_user_admin(cls.admin['id'], True)

    @classmethod
    def _signup(cls, email, password, role):
        response = cls.client.post('/api/auth/signup', json={
            'email': email,
            'password': password,
            'first_name': role.title(),
            'profile_role': role,
            'profile_location': 'KTEB',
        })
        body = response.get_json()
        assert response.status_code == 201, body
        return body['user']

    def setUp(self):
        self.client = app.test_client()
        import app as app_module
        app_module._AUTH_RATE_LIMITS.clear()

    def _login(self, email, password):
        response = self.client.post('/api/auth/login', json={'email': email, 'password': password})
        self.assertEqual(response.status_code, 200, response.get_json())
        return response

    def test_login_endpoint_is_registered_and_home_renders(self):
        from flask import url_for
        with app.test_request_context():
            self.assertEqual(url_for('login'), '/login')
        home = self.client.get('/')
        self.assertEqual(home.status_code, 200)
        page = self.client.get('/login')
        self.assertEqual(page.status_code, 200)

    def test_price_switches_on_new_year_chicago(self):
        chicago = ZoneInfo('America/Chicago')
        promo = datetime(2026, 12, 31, 23, 59, tzinfo=chicago)
        after = datetime(2027, 1, 1, 0, 0, tzinfo=chicago)
        self.assertEqual(pricing.listing_price_cents(promo), 1499)
        self.assertEqual(pricing.listing_price_cents(after), 4999)
        self.assertTrue(pricing.listing_price(promo)['promotional'])
        self.assertFalse(pricing.listing_price(after)['promotional'])

    def test_login_logout_and_wrong_password(self):
        bad = self.client.post('/api/auth/login', json={'email': 'buyer@example.com', 'password': 'nope-nope'})
        self.assertEqual(bad.status_code, 401)
        good = self._login('buyer@example.com', 'buyer-pass-1')
        me = self.client.get('/api/auth/me')
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.get_json()['user']['email'], 'buyer@example.com')
        self.client.post('/api/auth/logout')
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)
        self.assertIn('jet_session', good.headers.get('Set-Cookie', ''))

    def test_public_listing_hides_broker_inventory(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Public Jet', 'public'))
        self.assertEqual(created.status_code, 201, created.get_json())
        public_id = created.get_json()['id']
        hidden = self.client.post('/api/listings', json=self._payload('Quiet Jet', 'broker_only'))
        hidden_id = hidden.get_json()['id']
        db_module.admin_approve_listing_any(public_id, self.admin['id'])
        db_module.admin_approve_listing_any(hidden_id, self.admin['id'])
        ids = {row.get('id') for row in self.client.get('/api/user-listings').get_json()}
        self.assertIn(public_id, ids)
        self.assertNotIn(hidden_id, ids)
        page = self.client.get(f'/listing/{hidden_id}')
        self.assertEqual(page.status_code, 404)
        self.assertEqual(self.client.get(f'/listing/{public_id}').status_code, 200)

    def test_buyer_cannot_open_off_market_and_broker_can(self):
        self._login('buyer@example.com', 'buyer-pass-1')
        blocked = self.client.get('/off-market')
        self.assertEqual(blocked.status_code, 403)
        self._login('broker@example.com', 'broker-pass-1')
        allowed = self.client.get('/off-market')
        self.assertEqual(allowed.status_code, 200)

    def test_owner_cannot_edit_someone_elses_listing(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Owned Jet', 'public'))
        listing_id = created.get_json()['id']
        self._login('buyer@example.com', 'buyer-pass-1')
        patched = self.client.patch(f'/api/listings/{listing_id}', json={'price': 1})
        self.assertEqual(patched.status_code, 403)

    def test_buyer_cannot_open_admin_and_admin_cannot_approve_own_listing(self):
        self._login('buyer@example.com', 'buyer-pass-1')
        self.assertEqual(self.client.get('/api/admin/listings').status_code, 403)
        self._login('admin@example.com', 'admin-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Admin Jet', 'public'))
        listing_id = created.get_json()['id']
        approved = self.client.post(f'/api/admin/listings/{listing_id}/approve')
        self.assertEqual(approved.status_code, 403)

    def test_reject_then_resubmit_does_not_require_a_second_payment(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Rejected Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.admin_reject_listing_any(listing_id, 'Need the serial number')
        with db_module.get_session() as session:
            session.query(db_module.UserListing).filter(db_module.UserListing.id == listing_id).update(
                {'payment_status': 'paid'}, synchronize_session=False
            )
        again = self.client.post(f'/api/listings/{listing_id}/resubmit')
        self.assertEqual(again.status_code, 200, again.get_json())
        self.assertFalse(again.get_json()['charged_again'])
        self.assertEqual(again.get_json()['status'], 'pending')

    def test_turning_paint_off_changes_the_rank(self):
        cards = [
            {'id': 1, 'title': 'Fresh', 'price': 100, 'year': 2018, 'hours': 500, 'range': 2000,
             'passengers': 6, 'speed': 400, 'paint_year': 2024, 'engine_hours': 400, 'avionics': 'G3000'},
            {'id': 2, 'title': 'Older paint', 'price': 100, 'year': 2018, 'hours': 500, 'range': 2000,
             'passengers': 6, 'speed': 400, 'paint_year': 1998, 'engine_hours': 400, 'avionics': 'G3000'},
        ]
        prefs = {'range_nm': 500, 'passengers': 2, 'weights': {key: True for key in matching.COMPONENTS}}
        with_paint = matching.rank_listings(cards, prefs)['results']
        prefs['weights']['paint'] = False
        without = matching.rank_listings(cards, prefs)['results']
        self.assertNotEqual(with_paint[0]['scores']['paint'], with_paint[1]['scores']['paint'])
        self.assertNotIn('paint', without[0]['used'])
        too_far = matching.rank_listings(cards, {'range_nm': 5000, 'weights': prefs['weights']})
        self.assertEqual(too_far['results'], [])
        self.assertEqual(len(too_far['excluded']), 2)

    def test_charter_request_is_not_confirmed_until_operator_accepts(self):
        self._login('operator@example.com', 'operator-pass-1')
        page = self.client.post('/charter/fleet', data={
            'name': 'Citation CJ3', 'registration': 'N100JS', 'base_airport': 'KTEB',
            'seats': 7, 'hourly_rate': 3200, 'range_nm': 1800, 'speed_kts': 400,
        }, follow_redirects=False)
        self.assertIn(page.status_code, (302, 303))
        available = self.client.get('/api/charter/available?departure=JFK&arrival=MIA&passengers=2&date=2026-11-01')
        aircraft = available.get_json()['aircraft']
        self.assertTrue(aircraft)
        booked = self.client.post('/api/charter/book', json={
            'aircraft_id': aircraft[0]['id'],
            'name': 'Pat Buyer',
            'email': 'pat@example.com',
            'departure_airport': 'JFK',
            'arrival_airport': 'MIA',
            'departure_date': '2026-11-01',
            'passengers': 2,
        })
        self.assertEqual(booked.status_code, 201)
        self.assertEqual(booked.get_json()['status'], 'requested')
        booking_id = booked.get_json()['id']
        accepted = self.client.post(f'/api/charter/bookings/{booking_id}/status', json={'status': 'confirmed'})
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(db_module.get_charter_booking(booking_id)['status'], 'confirmed')

    def test_duplicate_stripe_event_is_ignored(self):
        self.assertTrue(db_module.claim_stripe_event('evt_test_once'))
        self.assertFalse(db_module.claim_stripe_event('evt_test_once'))

    def test_listing_fee_ignores_a_client_supplied_amount(self):
        from app import _listing_fee_cents
        self.assertEqual(_listing_fee_cents(), pricing.listing_price_cents())
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Fee Jet', 'public'))
        listing_id = created.get_json()['id']
        checkout = self.client.post(f'/api/listings/{listing_id}/checkout', json={'amount': 1, 'amount_cents': 1})
        self.assertEqual(checkout.status_code, 200)
        self.assertTrue(checkout.get_json().get('skip'))

    def _payload(self, title, market):
        return {
            'profile_id': self.profile_id,
            'title': title,
            'price': 2500000,
            'location': 'KTEB',
            'email': 'seller@example.com',
            'year': 2018,
            'hours': 900,
            'description': 'Test aircraft',
            'market': market,
            'engine_hours': 700,
            'paint_year': 2020,
            'avionics': 'G1000',
        }


if __name__ == '__main__':
    unittest.main()
